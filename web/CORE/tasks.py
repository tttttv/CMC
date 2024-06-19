import datetime
import random
import time

from django.db import transaction
from django.db.models import Q

from CORE.exceptions import InsufficientBalance
from CORE.models import BybitAccount, RiskEmail, OrderBuyToken, P2PItem, P2POrderMessage, BybitCurrency, BybitIncomingPayment, PaymentTerm, AccountInsufficientItems, \
    BybitP2PBlackList

from CORE.service.bybit.api import BybitAPI
from CORE.service.bybit.parser import BybitSession, AuthenticationError
from CORE.service.bybit.code_2fa import get_codes, get_addressbook_codes
from CORE.service.CONFIG import P2P_BUY_TIMEOUTS, TOKENS_DIGITS, CREATED_TIMEOUT
from celery import shared_task

from CORE.service.tools.formats import format_float
from CORE.utils import order_task_lock, get_active_celery_tasks
from requests.exceptions import *


@shared_task
def update_p2pitems_task():
    accounts = BybitAccount.objects.filter(is_active=True)
    if not accounts:
        return
    account: BybitAccount = random.choice(accounts)
    bybit_session = BybitSession(account)

    payment_methods = [payment.payment_id for payment in BybitCurrency.all_payment_methods()]
    print('payment_methods', payment_methods)
    try:
        user_info = bybit_session.get_user_info()  # if filter_ineligible

        items_sale = bybit_session.get_prices_list(token_id='USDT', currency_id='RUB',
                                                   payment_methods=payment_methods, side="1", filter_online=True,
                                                   filter_ineligible=True, user_info=user_info)  # лоты на продажу
        items_buy = bybit_session.get_prices_list(token_id='USDT', currency_id='RUB',  # todo другие валюты
                                                  payment_methods=payment_methods, side="0", filter_online=True,
                                                  filter_ineligible=True, user_info=user_info)  # лоты на покупку
    except (ProxyError, RequestException) as e:
        account.set_proxy_dead()
        print(e)
        return
    except AuthenticationError:
        account.set_cookie_die()
        return

    P2PItem.objects.filter(is_active=True).update(is_active=False)

    exclude_sellers = BybitP2PBlackList.get_blacklist(side=BybitP2PBlackList.SIDE_SELL)
    exclude_buyers = BybitP2PBlackList.get_blacklist(side=BybitP2PBlackList.SIDE_BUY)

    for item in (items_sale + items_buy):
        if P2PItem.objects.filter(item_id=item.item_id).exists():
            item.id = P2PItem.objects.get(item_id=item.item_id).id

        item.is_active = True
        if item.side == P2PItem.SIDE_SELL:
            if item.user_id in exclude_sellers:
                item.is_active = False
        elif item.user_id in exclude_buyers:  # P2PItem.SIDE_BUY
            item.is_active = False
        item.save()


@shared_task
def task_remove_insufficient_items():
    now = datetime.datetime.now()
    expired_purchases = AccountInsufficientItems.objects.filter(expire_dt__lt=now)
    expired_purchases.delete()


@shared_task
def task_send_message(message_id: int):
    message = P2POrderMessage.objects.select_related('order').only('bybit_order_id', 'text', 'uuid', 'order__account').get(id=message_id)
    if message.bybit_order_id:
        bybit_session = BybitSession(message.order.account)
        if bybit_session.send_message(message.bybit_order_id, message.text, message_uuid=message.uuid):
            message.status = message.STATUS_DELIVERED
        else:
            message.status = message.STATUS_ERROR
        message.save()


@shared_task()
def task_send_image(message_id: int, content_type: str):
    message = P2POrderMessage.objects.select_related('order').only('bybit_order_id', 'file', 'uuid', 'order__account').get(id=message_id)
    if message.bybit_order_id:
        bybit_session = BybitSession(message.order.account)

        with message.file.open('rb') as f:
            content = f.read()

        if bybit_session.upload_file(message.bybit_order_id, message.file.name, content, content_type, message_uuid=message.uuid):
            message.status = message.STATUS_DELIVERED
        else:
            message.status = message.STATUS_ERROR
        message.save()


@shared_task
def process_orders_messages_task(count=2):
    orders_buy_token = OrderBuyToken.objects.filter(state__in=[
        OrderBuyToken.STATE_CREATED,
        OrderBuyToken.STATE_TRANSFERRED,
        OrderBuyToken.STATE_PAID,
        OrderBuyToken.STATE_WAITING_CONFIRMATION
    ], is_stopped=False)

    for order in orders_buy_token:
        process_receive_order_message_task.delay(order.id)

    if count > 0:
        process_orders_messages_task.apply_async(args=(count - 1,), countdown=20)


@shared_task
def process_receive_order_message_task(order_id):
    order = OrderBuyToken.objects.get(id=order_id)

    if order.order_sell_id and order.stage == OrderBuyToken.STAGE_PROCESS_PAYMENT:
        order.update_p2p_order_messages(side=P2PItem.SIDE_SELL)

    if order.order_buy_id and order.stage == OrderBuyToken.STAGE_PROCESS_WITHDRAW:
        order.update_p2p_order_messages(side=P2PItem.SIDE_BUY)


@shared_task
def process_orders_task():
    orders_buy_token = OrderBuyToken.objects.filter(is_executing=False, is_stopped=False).exclude(
        state__in=BybitAccount.order_end_states())
    for order in orders_buy_token:
        process_buy_order_task.delay(order.id)


@shared_task
def healthcare_orders_task():  # Проверяем время выполнение таска
    orders_buy_token = OrderBuyToken.objects.filter(is_stopped=False).exclude(
        state__in=BybitAccount.order_end_states())

    dt_now = datetime.datetime.now() - datetime.timedelta(minutes=CREATED_TIMEOUT)

    for order in orders_buy_token:
        if order and order.dt_created_sell < dt_now:
            if order.account.active_order is not None:
                BybitAccount.release_order(order.account_id)

            order.is_stopped = True
            order.error_message = 'task timeout'
            order.state = OrderBuyToken.STATE_TIMEOUT

            order.save()

        elif order.is_executing:
            order_tasks = get_active_celery_tasks()
            for task in order_tasks:
                if task['name'] == 'CORE.tasks.process_buy_order_task' and task['args'][0] == order.order_id:
                    break
            else:
                print('Order task worker die!')  # FIXME нет атомарности / таска в запуске
                # TODO order.is_executing = False


def process_payment_fiat(order: OrderBuyToken):
    bybit_session = BybitSession(order.account)

    print('process_payment_fiat ORDER', order.id, order.state, order.account.imap_username)

    if order.state == OrderBuyToken.STATE_INITIATED:
        if not order.order_sell_id:  # Запрос к bybit еще не делали
            if not order.create_p2p_order(side=P2PItem.SIDE_SELL):  # Ad status changed
                return

        order.update_p2p_order_status(side=P2PItem.SIDE_SELL)
        return

    elif order.state == OrderBuyToken.STATE_CREATED:  # На этом этапе ждем подтверждения со стороны пользователя
        if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['CREATED'], side=P2PItem.SIDE_SELL):
            return

        print('WAITING FOR CUSTOMER TO PAY')

        order.update_p2p_order_messages(side=P2PItem.SIDE_SELL)

    elif order.state == OrderBuyToken.STATE_TRANSFERRED:  # Оплачен клиентом
        if bybit_session.mark_order_as_paid(order.order_sell_id, order.terms['payment_id'],
                                            order.payment_currency.payment_id):
            print('Order marked as paid')
            order.state = OrderBuyToken.STATE_PAID
            order.dt_paid_sell = datetime.datetime.now()
            order.save()
            process_buy_order_direct(order)
        else:
            order.update_p2p_order_messages(side=P2PItem.SIDE_SELL)

    elif order.state == OrderBuyToken.STATE_PAID:  # Ждет подтверждения от продавца

        order.update_p2p_order_messages(side=P2PItem.SIDE_SELL, bybit_session=bybit_session)

        state, terms, add_info = bybit_session.get_order_info(order.order_sell_id, order.payment_currency.payment_id)

        if state == 50:
            print('Token received')
            order.state = OrderBuyToken.STATE_CHECK_BALANCE  # todo доп. проверять
            order.dt_received_sell = datetime.datetime.now()
            order.save()
            process_buy_order_direct(order)  # Вызывает себя со следующим статусом
            order.add_message(message=f'P2P USDT received', **add_info)
            return

        elif state == 20:
            print('Waiting for seller')

        elif state == 30:  # todo Выводить ошибку
            print('Appeal')
            order.state = OrderBuyToken.STATE_P2P_APPEAL
            order.save()
            order.add_message(message='payment appeal')

            BybitP2PBlackList.add_seller(order.p2p_item_sell.item_id, order.p2p_item_sell.user_id, side=BybitP2PBlackList.SIDE_SELL)
            return
        else:
            raise ValueError("Unknown state", state)

        if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['CREATED'], side=P2PItem.SIDE_SELL):
            return

    elif order.state == OrderBuyToken.STATE_CHECK_BALANCE:
        # TODO ***
        order.state = OrderBuyToken.STATE_RECEIVED
        order.stage = order.STAGE_PROCESS_WITHDRAW
        order.save()
        process_buy_order_direct(order)
        return


def process_withdraw_crypto(order: OrderBuyToken):
    """Вывод крипты"""
    bybit_session = BybitSession(order.account)
    bybit_api = order.account.get_api()

    print('process_withdraw_crypto ORDER', order.id, order.state, order.account.imap_username)

    if order.state == OrderBuyToken.STATE_RECEIVED:  # Переводим на биржу
        if (order.payment_currency.is_fiat and order.p2p_item_sell.token == order.withdraw_currency.token or
                order.payment_currency.is_crypto and order.payment_currency.token == order.withdraw_currency.token):
            order.state = OrderBuyToken.STATE_WITHDRAWING  # Если не нужно менять валюту на бирже
            order.save()
        else:  # Нужно менять
            usdt_amount_available = order.usdt_amount / (1 - order.platform_commission)

            print('usdt_amount_available formated', usdt_amount_available)
            usdt_amount_available = format_float(usdt_amount_available, token='USDT')

            if order.payment_currency.is_fiat:
                token = order.p2p_item_sell.token
            else:  # is crypto  Входящую крипту мы уже поменяли на USDT
                token = 'USDT'

            balance = bybit_session.get_funding_balance(token)
            print('funding balance', balance, 'need', usdt_amount_available, usdt_amount_available > balance)

            try:
                bybit_api.transfer_to_trading(token, usdt_amount_available)  # Переводим на биржу
                order.state = OrderBuyToken.STATE_TRADING
                order.dt_trading_buy = datetime.datetime.now()
                order.add_message(message=f'transfer {token} from funding to unified', funding_balance=balance, transfer=usdt_amount_available)
            except InsufficientBalance:
                order.state = OrderBuyToken.STATE_ERROR
                order.add_message(message=f'not enough {token} on funding', funding_balance=balance, transfer=usdt_amount_available)

            order.save()

        process_buy_order_direct(order)
        return

    elif order.state == OrderBuyToken.STATE_TRADING:

        withdraw_chain_commission = order.withdraw_currency.get_chain_commission()
        trading_quantity = (order.withdraw_amount + withdraw_chain_commission) / (1 - order.trading_commission)
        print('trading_quantity', trading_quantity)

        trading_quantity = format_float(trading_quantity, token=order.withdraw_currency.token)
        print('trading_quantity', trading_quantity)

        usdt_price = bybit_api.get_price_for_amount(order.withdraw_currency.token, 'USDT', trading_quantity, side=BybitAPI.SIDE_BUY_CRYPTO)

        trade_rate = usdt_price / trading_quantity
        print('usdt_price', usdt_price)
        print('usdt_amount', order.usdt_amount)
        print('trade_rate', trade_rate)

        trade_rate = bybit_api.get_trading_rate(order.withdraw_currency.token, 'USDT')
        print('orig trade_rate', trade_rate, 'from order', order.price_buy)

        if trade_rate > order.price_buy * 1.01:
            order.state = OrderBuyToken.STATE_ERROR_TRADE_VOLATILE  # FIXME change state
            order.save()
            order.error_message = "Цена на бирже изменилась > 3%"
            order.add_message('trade price changed', prev=order.price_buy, new=trade_rate)
            return

        print('trading_quantity', trading_quantity)

        try:
            market_order_id = bybit_api.place_order(order.withdraw_currency.token, 'USDT',
                                                    trading_quantity, side=BybitAPI.SIDE_BUY_CRYPTO)

        except InsufficientBalance:
            order.state = OrderBuyToken.STATE_ERROR
            unified_balance = bybit_session.get_unified_balance('USDT')

            order.add_message(message=f'not enough USDT on unified for trade', unified_balance=unified_balance,
                              buy=trading_quantity, token='USDT', price=trade_rate)
            order.save()
            return

        order.order_buy_id = market_order_id
        order.state = OrderBuyToken.STATE_TRADED
        order.save()

        time.sleep(2)  # FIXME !!!
        process_buy_order_direct(order)
        return

    elif order.state == OrderBuyToken.STATE_TRADED:
        status = bybit_api.get_order_status(order.order_buy_id)
        print(status)

        if status == 'Filled':  # Успешно вывели
            try:
                bybit_api.transfer_to_funding(order.withdraw_currency.token,
                                              order.withdraw_from_trading_account)
                order.state = OrderBuyToken.STATE_WITHDRAWING

            except InsufficientBalance:
                order.state = OrderBuyToken.STATE_ERROR
                unified_balance = bybit_session.get_unified_balance('USDT')
                order.add_message(message=f'not enough {order.withdraw_currency.token} after trade', unified_balance=unified_balance,
                                  need=order.withdraw_from_trading_account, token=order.withdraw_currency.token)

            order.save()

        elif status == 'PartiallyFilledCanceled':  # Todo проработать логику
            order.add_message(message=f'PartiallyFilledCanceled')
            order.state = OrderBuyToken.STATE_ERROR
            order.save()
        else:
            print(status)
            raise ValueError("Unknown status")

    elif order.state == OrderBuyToken.STATE_WITHDRAWING:  # Инициализируем вывод крипты
        BybitAccount.release_order(order.account_id)
        print('withdraw crypto STATE_WITHDRAWING')

        existed = bybit_session.addressbook_check(order.withdraw_currency.address, order.withdraw_currency.token,
                                                  order.withdraw_currency.chain)
        print('withdraw address existed', existed)
        if not existed:  # Если в адресной книге нет адреса
            risk_token = bybit_session.addressbook_get_risk_token(order.withdraw_currency.address, order.withdraw_currency.token,
                                                                  order.withdraw_currency.chain)
            if not order.verify_risk_token(risk_token, bybit_session):
                return

            bybit_session.addressbook_create_address(order.withdraw_currency.address, risk_token, order.withdraw_currency.token,
                                                     order.withdraw_currency.chain)

        order.state = OrderBuyToken.STATE_WAITING_VERIFICATION
        order.dt_verification = datetime.datetime.now()
        order.save()

    elif order.state == OrderBuyToken.STATE_WAITING_VERIFICATION:  # Ждем код на почту
        BybitAccount.release_order(order.account_id)

        print('withdraw_amount', order.withdraw_amount)
        if bybit_api.withdraw(order.withdraw_currency.token, order.withdraw_currency.chain, order.withdraw_currency.address,
                              order.withdraw_amount):  # FIXME снимут комиссию chain с баланса или с транзакции
            print('Withdrawn successfully')
            order.state = OrderBuyToken.STATE_WITHDRAWN
            order.dt_withdrawn = datetime.datetime.now()
            order.save()


def process_payment_crypto(order: OrderBuyToken):
    bybit_session = BybitSession(order.account)
    bybit_api = order.account.get_api()

    print('process_payment_crypto ORDER', order.id, order.state, order.account.imap_username)  # email

    if order.state == OrderBuyToken.STATE_INITIATED:
        if order.internal_address is None:
            if not order.create_trade_deposit():
                return

        order.state = OrderBuyToken.STATE_CREATED
        order.dt_created_sell = datetime.datetime.now()
        order.save()

    elif order.state == OrderBuyToken.STATE_CREATED:  # Ждем подтверждения
        print('WAITING CONFIRM FROM USER')
        return

    elif order.state == OrderBuyToken.STATE_TRANSFERRED:  # Ждем перевода

        deposit_data = bybit_session.get_deposit_status(token_name=order.payment_currency.token)

        for incoming_payment in deposit_data:  # TODO дополнительно выгружать таской для админки
            incoming_id = int(incoming_payment['id'])
            if not BybitIncomingPayment.objects.filter(item_id=incoming_id).exists():
                incoming_payment = BybitIncomingPayment.from_json(incoming_payment, order.account)
                print('incoming_payment', incoming_payment.to_json())
                print('trx dt', incoming_payment.created_time.strftime('%Y-%m-%d %H:%M:%S'))
                print('sell dt', order.dt_created_sell.strftime('%Y-%m-%d %H:%M:%S'))
                print('dt', incoming_payment.created_time > order.dt_initiated, incoming_payment.created_time > order.dt_created_sell)
                print(incoming_payment.address, order.payment_currency.address, order.internal_address.address)
                print(incoming_payment.chain, order.payment_currency.chain)
                if (incoming_payment.created_time > order.dt_created_sell and
                        # order.payment_currency.address # TODO Проверять транзакцию/отправителя в RPC API NEAR
                        incoming_payment.address == order.internal_address.address and
                        incoming_payment.chain == order.payment_currency.chain):
                    with transaction.atomic():
                        if incoming_payment.amount < order.payment_amount:
                            order.state = OrderBuyToken.STATE_PAYMENT_AMOUNT_NOT_ENOUGH  # ***
                        else:
                            order.state = OrderBuyToken.STATE_WAITING_TRANSACTION_PROCESSED

                        order.incoming_payment = incoming_payment
                        order.incoming_payment.save()
                        order.save()

                        process_buy_order_direct(order)

    elif order.state == OrderBuyToken.STATE_WAITING_TRANSACTION_PROCESSED:  # Ждем подтверждения перевода от bybit
        if not order.incoming_payment:
            order.state = OrderBuyToken.STATE_ERROR
            order.error_message = 'Входящий перевод отсутствует'
            order.save()

        deposit_data = bybit_session.get_deposit_status(token_name=order.payment_currency.token)

        for incoming_payment in deposit_data:
            incoming_id = int(incoming_payment['id'])
            if order.incoming_payment.item_id == incoming_id:
                updated_data = {
                    'confirmations': int(incoming_payment['confirmations']),
                    'safeConfirmNumber': int(incoming_payment['safeConfirmNumber']),
                    'blockConfirmNumber': int(incoming_payment['blockConfirmNumber']),
                    'status': incoming_payment['status']
                }

                for field, value in updated_data.items():
                    setattr(order.incoming_payment, field, value)
                order.incoming_payment.save()

                if order.incoming_payment.confirmed:
                    order.state = OrderBuyToken.STATE_RECEIVING_CRYPTO
                    order.save()
                    process_buy_order_direct(order)
                return
        return

    elif order.state == OrderBuyToken.STATE_RECEIVING_CRYPTO:  # Переводим на биржу
        account_balance = bybit_session.get_available_balance(token_name=order.payment_currency.token)
        if account_balance < order.payment_amount:
            order.state = OrderBuyToken.STATE_ERROR
            order.error_message = 'Токен не поступил на баланс после входящего перевода'
            order.save()
            return

        if order.payment_currency.token == BybitCurrency.CURRENCY_USDT:  # Если не нужно менять валюту на бирже
            order.state = OrderBuyToken.STATE_CHECK_BALANCE
            order.save()

        else:  # Нужно менять
            print('NEED TRADE')
            bybit_api.transfer_to_trading(order.payment_currency.token, order.payment_amount)  # Переводим на биржу
            order.state = OrderBuyToken.STATE_TRADING_CRYPTO
            order.dt_trading = datetime.datetime.now()
            order.save()

        process_buy_order_direct(order)
        return

    elif order.state == OrderBuyToken.STATE_TRADING_CRYPTO:
        # usdt_price = bybit_api.get_price_for_amount(order.payment_currency.token, BybitCurrency.CURRENCY_USDT,
        #                                             trading_quantity, side=BybitAPI.SIDE_BUY_FIAT)
        # trade_rate = usdt_price / order.payment_amount
        # print('usdt_price', usdt_price)
        # print('usdt_amount', order.usdt_amount)
        # print('trade_rate', trade_rate)

        # usdt_available = order.usdt_amount * (1 - order.platform_commission)
        # print('usdt_available', usdt_available, 'usdt_price', usdt_price, usdt_price > usdt_available * 1.03)

        trade_rate = bybit_api.get_trading_rate(order.payment_currency.token, 'USDT')
        print('orig trade_rate', trade_rate, 'from order', order.price_sell)

        if 1 / trade_rate > order.price_sell * 1.01:
            order.state = OrderBuyToken.STATE_ERROR_TRADE_VOLATILE  # TODO WRONG_PRICE
            order.error_message = "Цена на бирже изменилась > 3%"
            order.save()
            return

        trading_quantity = format_float(order.payment_amount, token=order.payment_currency.token)
        market_order_id = bybit_api.place_order(order.payment_currency.token, 'USDT', trading_quantity,  # Меняем всю крипту что нам дали
                                                side=BybitAPI.SIDE_BUY_FIAT)
        order.order_sell_id = market_order_id
        order.state = OrderBuyToken.STATE_TRADED_CRYPTO
        order.save()

        time.sleep(5)  # FIXME !!!
        process_buy_order_direct(order)
        return

    elif order.state == OrderBuyToken.STATE_TRADED_CRYPTO:
        status = bybit_api.get_order_status(order.order_sell_id)
        print(status)
        if status == 'Filled' or status == 'PartiallyFilledCanceled':  # Успешно вывели
            # digits = TOKENS_DIGITS['USDT']
            # usdt_amount = float((('{:.' + str(digits) + 'f}').format(order.usdt_amount)))
            print('STATE_TRADED_CRYPTO order.usdt_amount', order.usdt_amount)
            bybit_api.transfer_to_funding('USDT', order.usdt_amount)
            order.state = OrderBuyToken.STATE_CHECK_BALANCE
            order.save()
            process_buy_order_direct(order)
        elif status == 'PartiallyFilledCanceled':  # TODO проработать логику ***
            order.state = OrderBuyToken.STATE_ERROR
            order.error_message = 'partiallyFilledCac'
            order.save()
            raise ValueError("Не до конца выполнено")
        else:
            print(status)
            raise ValueError("Unknown status")

    elif order.state == OrderBuyToken.STATE_CHECK_BALANCE:
        # TODO ***
        order.state = OrderBuyToken.STATE_RECEIVED
        order.stage = order.STAGE_PROCESS_WITHDRAW
        order.save()
        process_buy_order_direct(order)


def process_withdraw_fiat(order: OrderBuyToken):
    bybit_session = BybitSession(order.account)

    print('process_withdraw_fiat ORDER', order.id, order.state, order.account.imap_username)  # email

    if order.state == OrderBuyToken.STATE_RECEIVED:  # Проводим P2P Сделку

        for payment_method in bybit_session.get_payments_list():
            print('payment_method', payment_method.paymentType, payment_method.accountNo, payment_method.realName)
            if (payment_method.paymentType == order.withdraw_currency.payment_id and
                    payment_method.accountNo == order.withdraw_currency.address and
                    payment_method.realName == order.withdraw_name):
                print('WITHDRAW CARD EXIST')
                order.payment_term = PaymentTerm.from_bybit_term(payment_method)
                order.payment_term.save()
                break

        else:  # Добавляем новую карту
            risk_token = bybit_session.add_payment_method(payment_type=order.withdraw_currency.payment_id,
                                                          realName=order.withdraw_name,
                                                          accountNo=order.withdraw_currency.address)
            print('ADD NEW WITHDRAW CARD')
            if not order.verify_risk_token(risk_token, bybit_session):
                return

            bybit_session.add_payment_method(payment_type=order.withdraw_currency.payment_id,
                                             realName=order.withdraw_name,
                                             accountNo=order.withdraw_currency.address,
                                             risk_token=risk_token)

            time.sleep(3)

            for payment_method in bybit_session.get_payments_list():
                if (payment_method.paymentType == order.withdraw_currency.payment_id and
                        payment_method.accountNo == order.withdraw_currency.address and
                        payment_method.realName == order.withdraw_name):
                    order.payment_term = PaymentTerm.from_bybit_term(payment_method)
                    order.payment_term.save()
                    break
            else:
                return

        if not order.order_buy_id:  # Запрос к bybit еще не делали
            if not order.create_p2p_order(side=P2PItem.SIDE_BUY,
                                          find_new_items=False if order.p2p_item_buy is not None else True):  # Создаем заказ
                return  # state -> ERROR

        print('created')
        order.update_p2p_order_status(side=P2PItem.SIDE_BUY)  # state -> STATE_TRANSFERRED
        return

    elif order.state == OrderBuyToken.STATE_TRANSFERRED:  # Ждет подтверждения от продавца
        order.update_p2p_order_messages(side=P2PItem.SIDE_BUY)  # Выгружаем сообщения в базу

        state, terms, add_info = bybit_session.get_order_info(order.order_buy_id, order.withdraw_currency.payment_id)
        print('STATE_TRANSFERRED get_order_info', state, terms)
        if state == 50:
            order.state = OrderBuyToken.STATE_BUY_CONFIRMED
            order.error_message = 'заказ подтвердили с аккаунта bybit'
            order.save()
            order.add_message(message=f'P2P Заказ подтвердили с аккаунта bybit', **add_info)

        elif state == 40:
            order.error_message = 'продавец не подтвердил заказ'
            BybitP2PBlackList.add_seller(order.p2p_item_buy.item_id, order.p2p_item_buy.user_id, side=BybitP2PBlackList.SIDE_BUY)
            order.add_message(message=f'P2P Заказ отменен продавцом', item_id=order.p2p_item_buy.item_id, **add_info,
                              price=order.price_buy, order_id=order.order_buy_id)

            order.state = OrderBuyToken.STATE_RECEIVED
            order.order_buy_id = None
            order.p2p_item_buy = None

            order.save()
            return

        elif state == 20:
            order.state = OrderBuyToken.STATE_WAITING_CONFIRMATION
            order.dt_received_buy = datetime.datetime.now()
            order.save()
            process_buy_order_direct(order)  # Вызывает себя со следующим статусом

        elif state == 30:
            print('Appeal')
            BybitP2PBlackList.add_seller(order.p2p_item_buy.item_id, order.p2p_item_buy.user_id, side=BybitP2PBlackList.SIDE_BUY)

            order.add_message(message=f'P2P Апелляция', item_id=order.p2p_item_buy.item_id, **add_info)
            order.state = OrderBuyToken.STATE_P2P_APPEAL
            order.save()
            return
        elif state == 10:
            print('order created')
        else:
            raise ValueError("Unknown state", state)

        if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['SELLER'], side=P2PItem.SIDE_BUY):
            order.error_message = 'Продавец не перевел деньги'
            order.state = OrderBuyToken.STATE_ERROR
            return

    elif order.state == OrderBuyToken.STATE_WAITING_CONFIRMATION:
        # if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['CREATED'], side=P2PItem.SIDE_BUY):
        if order.dt_received_buy <= datetime.datetime.now() - datetime.timedelta(minutes=P2P_BUY_TIMEOUTS['CREATED']):
            # order.state = OrderBuyToken.STATE_BUY_NOT_CONFIRMED # FIXME
            order.error_message = 'Получение средств не подтвердили/оспорили за 30 минут'
            order.save()
            process_buy_order_direct(order)
            return
        print("Wait withdraw confirmation")
        order.update_p2p_order_messages(side=P2PItem.SIDE_BUY)

    elif order.state == OrderBuyToken.STATE_BUY_CONFIRMED or order.state == OrderBuyToken.STATE_BUY_NOT_CONFIRMED:
        print('Withdraw confirmed')

        state, terms, add_info = bybit_session.get_order_info(order.order_buy_id, order.withdraw_currency.payment_id)
        print('STATE_BUY_CONFIRMED state', state, terms)
        if state != 50:  # Если не подтвердили получение средств
            order.finish_buy_order()

        order.add_message(message=f'P2P Продали USDT', item_id=order.p2p_item_buy.item_id, **add_info)

        if order.state == OrderBuyToken.STATE_BUY_CONFIRMED:
            order.state = OrderBuyToken.STATE_WITHDRAWN

        elif order.state == OrderBuyToken.STATE_BUY_NOT_CONFIRMED:
            order.state = OrderBuyToken.STATE_TIMEOUT

        order.dt_withdrawn = datetime.datetime.now()
        order.save()

        BybitAccount.release_order(order.account_id)

        order.update_p2p_order_messages(side=P2PItem.SIDE_BUY)


def process_buy_order_direct(order: OrderBuyToken):
    print(f'PROCESS Order {order} DIRECT, {order.state}, stage {order.stage}')
    if order.stage == order.STAGE_PROCESS_PAYMENT:
        if order.payment_currency.is_crypto:
            process_payment_crypto(order)
        elif order.payment_currency.is_fiat:
            process_payment_fiat(order)
    elif order.stage == order.STAGE_PROCESS_WITHDRAW:
        if order.withdraw_currency.is_crypto:
            process_withdraw_crypto(order)
        elif order.withdraw_currency.is_fiat:
            process_withdraw_fiat(order)


@shared_task
def process_buy_order_task(order_id):
    order: OrderBuyToken = OrderBuyToken.objects.get(id=order_id)
    with order_task_lock(order.id):
        print(f'PROCESS Order {order}, {order.state}, stage {order.stage}')
        if order.stage == order.STAGE_PROCESS_PAYMENT:
            if order.payment_currency.is_crypto:
                process_payment_crypto(order)
            elif order.payment_currency.is_fiat:
                process_payment_fiat(order)
        elif order.stage == order.STAGE_PROCESS_WITHDRAW:
            if order.withdraw_currency.is_crypto:
                process_withdraw_crypto(order)
            elif order.withdraw_currency.is_fiat:
                process_withdraw_fiat(order)
    return


@shared_task
def update_latest_email_codes_task(user_id=None):
    if user_id:
        accounts = BybitAccount.objects.filter(user_id=user_id, is_active=True, imap_username__isnull=False,
                                               imap_password__isnull=False, imap_server__isnull=False)
    else:
        accounts = BybitAccount.objects.filter(is_active=True, imap_username__isnull=False,
                                               imap_password__isnull=False, imap_server__isnull=False)

    for account in accounts:
        if not account.imap_username or not account.imap_password or not account.imap_server:
            continue
        try:
            emails = get_codes(IMAP_USERNAME=account.imap_username, IMAP_PASSWORD=account.imap_password,
                               IMAP_SERVER=account.imap_server)
            for email in emails:
                risk = RiskEmail()
                risk.account = account
                risk.code = email['code']
                risk.amount = float(email['amount'])
                risk.address = email['address']
                risk.dt = email['dt']
                risk.save()

            addressbook_emails = get_addressbook_codes(IMAP_USERNAME=account.imap_username,
                                                       IMAP_PASSWORD=account.imap_password,
                                                       IMAP_SERVER=account.imap_server)
            print(addressbook_emails)
            for email in addressbook_emails:
                risk = RiskEmail()
                risk.account = account
                risk.code = email['code']
                risk.dt = email['dt']
                risk.save()
        except (OSError, TimeoutError) as e:  # socket.gaierror
            continue
