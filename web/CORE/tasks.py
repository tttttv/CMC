import datetime
import random

from django.db import transaction
from django.db.models import Q
from CORE.models import BybitAccount, RiskEmail, OrderBuyToken, P2PItem, P2POrderMessage, BybitCurrency, BybitIncomingPayment, PaymentTerm

from CORE.service.bybit.api import BybitAPI
from CORE.service.bybit.parser import BybitSession, AuthenticationError
from CORE.service.bybit.code_2fa import get_codes, get_addressbook_codes
from CORE.service.CONFIG import P2P_BUY_TIMEOUTS, TOKENS_DIGITS
from celery import shared_task
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
        items_sale = bybit_session.get_prices_list(token_id='USDT', currency_id='RUB',
                                                   payment_methods=payment_methods, side="1", filter_online=True,
                                                   filter_ineligible=True)  # лоты на продажу
        items_buy = bybit_session.get_prices_list(token_id='USDT', currency_id='RUB',  # todo другие валюты
                                                  payment_methods=payment_methods, side="0", filter_online=True,
                                                  filter_ineligible=True)  # лоты на покупку
    except (ProxyError, RequestException) as e:
        account.set_proxy_dead()
        print(e)
        return
    except AuthenticationError:
        account.set_banned()
        return

    P2PItem.objects.filter(is_active=True).update(is_active=False)

    for item in (items_sale + items_buy):
        print(item)
        if P2PItem.objects.filter(item_id=item.item_id).exists():
            item.id = P2PItem.objects.get(item_id=item.item_id).id
            print(item.id)
        item.is_active = True
        item.save()
        print('SAVED ID', item.id)


@shared_task
def task_send_message(message_id: int):
    message = P2POrderMessage.objects.select_related('order').only('text', 'uuid', 'order__account').get(id=message_id)
    bybit_session = BybitSession(message.order.account)
    if bybit_session.send_message(message.order_id, message.text, message_uuid=message.uuid):
        message.status = message.STATUS_DELIVERED
    else:
        message.status = message.STATUS_ERROR
    message.save()


@shared_task()
def task_send_image(message_id: int, content_type: str):
    message = P2POrderMessage.objects.select_related('order').only('file', 'uuid', 'order__account').get(id=message_id)
    bybit_session = BybitSession(message.order.account)

    with message.file.open('rb') as f:
        content = f.read()

    if bybit_session.upload_file(message.order_id, message.file.name, content, content_type):
        message.status = message.STATUS_DELIVERED
    else:
        message.status = message.STATUS_ERROR
    message.save()


@shared_task
def process_orders_messages_task():
    orders_buy_token = OrderBuyToken.objects.filter(state__in=[
        OrderBuyToken.STATE_TRANSFERRED,
        OrderBuyToken.STATE_PAID,
        OrderBuyToken.STATE_WAITING_CONFIRMATION
    ])
    for order in orders_buy_token:
        process_receive_order_message_task.delay(order.id)


@shared_task
def process_receive_order_message_task(order_id):
    order = OrderBuyToken.objects.get(id=order_id)

    if order.order_sell_id:
        bybit_session = BybitSession(order.account)
        messages = bybit_session.get_order_messages(order.order_sell_id)  # Выгружаем сообщения
        for msg in messages:
            message = P2POrderMessage.from_json(order.id, msg)
            if message:
                message.save()

    if order.order_buy_id:
        bybit_session = BybitSession(order.account)
        messages = bybit_session.get_order_messages(order.order_buy_id)  # Выгружаем сообщения
        for msg in messages:
            message = P2POrderMessage.from_json(order.id, msg)
            if message:
                message.save()


@shared_task
def process_orders_task():
    orders_buy_token = OrderBuyToken.objects.filter(~Q(state=OrderBuyToken.STATE_WITHDRAWN) &
                                                    ~Q(state=OrderBuyToken.STATE_ERROR) &
                                                    ~Q(state=OrderBuyToken.STATE_CANCELLED) &
                                                    ~Q(state=OrderBuyToken.STATE_ERROR_TRADE_VOLATILE),
                                                    is_executing=False,
                                                    is_stopped=False)
    for order in orders_buy_token:
        process_buy_order_task.delay(order.id)


@shared_task
def healthcare_orders_task():  # Проверяем время выполнение таска
    orders_buy_token = OrderBuyToken.objects.filter(
        ~Q(state=OrderBuyToken.STATE_WITHDRAWN), is_stopped=False)

    dt_now = datetime.datetime.now() - datetime.timedelta(minutes=60)

    for order in orders_buy_token:
        if order.dt_created < dt_now:
            BybitAccount.release_order(order.account_id)

            order.is_stopped = True
            order.error_message = 'task timeout'
            order.save()
        elif order.is_executing:
            order_tasks = get_active_celery_tasks()
            for task in order_tasks:
                if task['name'] == 'CORE.tasks.process_buy_order_task' and task['args'][0] == order.order_id:
                    break
            else:
                print('Order task worker die!')  # FIXME нет атомарности / таска в запуске


def process_payment_fiat(order: OrderBuyToken):
    bybit_session = BybitSession(order.account)

    print('process_payment_fiat ORDER', order.id, order.state, order.account.imap_username)

    if order.state == OrderBuyToken.STATE_INITIATED:
        if not order.order_sell_id:  # Запрос к bybit еще не делали
            if not order.create_p2p_order(side=P2PItem.SIDE_SELL):
                return

        order.update_p2p_order_status(side=P2PItem.SIDE_SELL)
        return
    elif order.state == OrderBuyToken.STATE_CREATED:  # На этом этапе ждем подтверждения со стороны пользователя
        if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['CREATED'], side=P2PItem.SIDE_SELL):
            return

        print('WAITING FOR CUSTOMER TO PAY')
        messages = bybit_session.get_order_messages(order.order_sell_id)  # Выгружаем сообщения из базы
        for msg in messages:
            message = P2POrderMessage.from_json(order.id, msg)
            if message:
                message.save()
    elif order.state == OrderBuyToken.STATE_TRANSFERRED:  # Оплачен клиентом
        if bybit_session.mark_order_as_paid(order.order_sell_id, order.terms['payment_id'],
                                            order.payment_currency.payment_id):
            print('Order marked as paid')
            order.state = OrderBuyToken.STATE_PAID
            order.dt_paid = datetime.datetime.now()
            order.save()

    elif order.state == OrderBuyToken.STATE_PAID:  # Ждет подтверждения от продавца
        messages = bybit_session.get_order_messages(order.order_sell_id)  # Выгружаем сообщения из базы
        for msg in messages:
            message = P2POrderMessage.from_json(order.id, msg)
            if message:
                message.save()

        state, terms = bybit_session.get_order_info(order.order_sell_id, order.payment_currency.payment_id)

        if state == 50:
            print('Token received')
            order.state = OrderBuyToken.CHECK_BALANCE  # todo доп. проверять
            order.dt_received = datetime.datetime.now()
            order.save()
            process_buy_order_task(order.id)  # Вызывает себя со следующим статусом
        elif state == 20:
            print('Waiting for seller')
        elif state == 30:  # todo Выводить ошибку
            print('Appeal')
            order.state = OrderBuyToken.STATE_P2P_APPEAL
            order.save()
        else:
            raise ValueError("Unknown state", state)

        if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['CREATED'], side=P2PItem.SIDE_SELL):
            return
    elif order.state == OrderBuyToken.CHECK_BALANCE:
        # TODO ***
        order.state = OrderBuyToken.STATE_RECEIVED
        order.stage = order.STAGE_PROCESS_WITHDRAW
        order.save()


def process_withdraw_crypto(order: OrderBuyToken):
    """Вывод крипты"""
    bybit_session = BybitSession(order.account)
    bybit_api = order.account.get_api()

    print('process_withdraw_crypto ORDER', order.id, order.state, order.account.imap_username)

    if order.state == OrderBuyToken.STATE_RECEIVED:  # Переводим на биржу
        usdt_amount_available = order.usdt_amount * (1 - order.partner_commission - order.platform_commission)
        print('usdt_amount_available', usdt_amount_available)

        digits = TOKENS_DIGITS['USDT']
        usdt_amount_available = float((('{:.' + str(digits) + 'f}').format(usdt_amount_available)))
        print('usdt_amount_available formated', usdt_amount_available)

        # BybitAccount.release_order(order.account_id) # FIXME

        if (order.payment_currency.is_fiat and order.p2p_item_sell.token == order.withdraw_currency.token or
                order.payment_currency.is_crypto and order.payment_currency.token == order.withdraw_currency.token):
            order.state = OrderBuyToken.STATE_WITHDRAWING  # Если не нужно менять валюту на бирже
            order.save()
            process_buy_order_task(order.id)
            return
        else:  # Нужно менять
            if order.payment_currency.is_fiat:
                bybit_api.transfer_to_trading(order.p2p_item_sell.token, usdt_amount_available)  # Переводим на биржу
            else:  # is crypto  Входящую крипту мы уже поменяли на USDT
                bybit_api.transfer_to_trading('USDT', usdt_amount_available)  # Переводим на биржу
            order.state = OrderBuyToken.STATE_TRADING
            order.dt_trading = datetime.datetime.now()
            order.save()

    elif order.state == OrderBuyToken.STATE_TRADING:

        withdraw_chain_commission = order.withdraw_currency.get_chain_commission()
        trading_quantity = (order.withdraw_amount + withdraw_chain_commission) / (1 - order.trading_commission)
        print('trading_quantity', trading_quantity)

        digits = TOKENS_DIGITS[order.withdraw_currency.token]
        trading_quantity = float((('{:.' + str(digits) + 'f}').format(trading_quantity)))
        print('trading_quantity', trading_quantity)

        usdt_price = bybit_api.get_price_for_amount(order.withdraw_currency.token, 'USDT', trading_quantity, side=BybitAPI.SIDE_BUY_CRYPTO)
        usdt_available = order.usdt_amount * (1 - order.partner_commission)

        trade_rate = usdt_price / trading_quantity
        print('usdt_price', usdt_price)
        print('usdt_amount', order.usdt_amount)
        print('trade_rate', trade_rate)

        if usdt_price > usdt_available * 1.03:  # FIXME CONFIG
            order.state = OrderBuyToken.STATE_ERROR_TRADE_VOLATILE  # FIXME change state
            order.save()

        print('trading_quantity', trading_quantity)
        market_order_id = bybit_api.place_order(order.withdraw_currency.token, 'USDT', trading_quantity,
                                                side=BybitAPI.SIDE_BUY_CRYPTO)  # FIXME *** Проверить
        order.order_buy_id = market_order_id
        order.state = OrderBuyToken.STATE_TRADED
        order.save()
    elif order.state == OrderBuyToken.STATE_TRADED:
        status = bybit_api.get_order_status(order.order_buy_id)
        print(status)
        if status == 'Filled' or status == 'PartiallyFilledCanceled':  # Успешно вывели
            bybit_api.transfer_to_funding(order.withdraw_currency.token,
                                          order.withdraw_from_trading_account)
            order.state = OrderBuyToken.STATE_WITHDRAWING
            order.save()
        elif status == 'PartiallyFilledCanceled':  # Todo проработать логику
            raise ValueError("Не до конца выполнено")
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
                        # order.payment_currency.address # TODO Проверять транзакцию/отправителя в RPC API NEAR / В bybit поискать
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

    elif order.state == OrderBuyToken.STATE_WAITING_TRANSACTION_PROCESSED:  # Ждем подтверждения перевода от bybit
        if not order.incoming_payment:
            order.state = OrderBuyToken.STATE_ERROR
            order.error_message = 'Входящий перевод отсутствует'
            order.save()

        deposit_data = bybit_session.get_deposit_status(token_name=order.payment_currency.token)

        for incoming_payment in deposit_data:
            incoming_id = int(incoming_payment['id'])
            if order.incoming_payment.item_id == incoming_id:
                updated_data = {'confirmations': int(incoming_payment['confirmations']),
                                'safeConfirmNumber': int(incoming_payment['safeConfirmNumber']),
                                'blockConfirmNumber': int(incoming_payment['blockConfirmNumber']),
                                'status': incoming_payment['status']
                                }

                # BybitIncomingPayment.objects.filter(id=incoming_id).update(**updated_data)
                # order.incoming_payment.refresh_from_db()

                for field, value in updated_data.items():
                    setattr(order.incoming_payment, field, value)
                order.incoming_payment.save()
                print('confirmations', order.incoming_payment.confirmations)
                print('safeConfirmNumber', order.incoming_payment.safeConfirmNumber)
                print('confirmed', order.incoming_payment.confirmed)
                if order.incoming_payment.confirmed:
                    order.state = OrderBuyToken.STATE_RECEIVING_CRYPTO
                    order.save()
                    process_buy_order_task(order.id)
                return

    elif order.state == OrderBuyToken.STATE_RECEIVING_CRYPTO:  # Переводим на биржу
        account_balance = bybit_session.get_available_balance(token_name=order.payment_currency.token)
        if account_balance < order.payment_amount:
            order.state = OrderBuyToken.STATE_ERROR
            order.error_message = 'Токен не поступил на баланс после входящего перевода'
            order.save()

        if order.payment_currency.token == BybitCurrency.CURRENCY_USDT:  # Если не нужно менять валюту на бирже
            order.state = OrderBuyToken.CHECK_BALANCE
            order.save()
            process_buy_order_task(order.id)
            return
        else:  # Нужно менять
            print('NEED TRADE')
            bybit_api.transfer_to_trading(order.payment_currency.token, order.payment_amount)  # Переводим на биржу
            order.state = OrderBuyToken.STATE_TRADING_CRYPTO
            order.dt_trading = datetime.datetime.now()
            order.save()

    elif order.state == OrderBuyToken.STATE_TRADING_CRYPTO:
        # FIXME chain комиссия на ввод ???
        digits = TOKENS_DIGITS[order.payment_currency.token]
        trading_quantity = float((('{:.' + str(digits) + 'f}').format(order.payment_amount)))

        usdt_price = bybit_api.get_price_for_amount(order.payment_currency.token, BybitCurrency.CURRENCY_USDT,
                                                    trading_quantity, side=BybitAPI.SIDE_BUY_FIAT)
        trade_rate = usdt_price / order.payment_amount
        print('usdt_price', usdt_price)
        print('usdt_amount', order.usdt_amount)
        print('trade_rate', trade_rate)

        usdt_available = order.usdt_amount * (1 - order.partner_commission)
        print('usdt_available', usdt_available, 'usdt_price', usdt_price, usdt_price > usdt_available * 1.03)
        if usdt_price > usdt_available * 1.03:  # FIXME CONFIG
            order.state = OrderBuyToken.STATE_ERROR_TRADE_VOLATILE  # FIXME change state
            order.error_message = f'trade: usdt_price {usdt_price}, usdt_available {usdt_available}, rate {trade_rate}, k {usdt_price/usdt_available}'
            order.save()

        market_order_id = bybit_api.place_order(order.payment_currency.token, 'USDT', trading_quantity,  # Меняем всю крипту что нам дали
                                                side=BybitAPI.SIDE_BUY_FIAT)
        order.order_sell_id = market_order_id
        order.state = OrderBuyToken.STATE_TRADED_CRYPTO
        order.save()

    elif order.state == OrderBuyToken.STATE_TRADED_CRYPTO:
        status = bybit_api.get_order_status(order.order_sell_id)
        print(status)
        if status == 'Filled' or status == 'PartiallyFilledCanceled':  # Успешно вывели
            digits = TOKENS_DIGITS['USDT']
            usdt_amount = float((('{:.' + str(digits) + 'f}').format(order.usdt_amount)))

            bybit_api.transfer_to_funding('USDT', usdt_amount)
            order.state = OrderBuyToken.CHECK_BALANCE
            order.save()
        elif status == 'PartiallyFilledCanceled':  # TODO проработать логику ***
            raise ValueError("Не до конца выполнено")
        else:
            print(status)
            raise ValueError("Unknown status")

    elif order.state == OrderBuyToken.CHECK_BALANCE:
        # TODO ***
        order.state = OrderBuyToken.STATE_RECEIVED
        order.stage = order.STAGE_PROCESS_WITHDRAW
        order.save()


def process_withdraw_fiat(order: OrderBuyToken):
    bybit_session = BybitSession(order.account)

    print('process_withdraw_fiat ORDER', order.id, order.state, order.account.imap_username)  # email

    if order.state == OrderBuyToken.STATE_RECEIVED:  # Проводим P2P Сделку

        for payment_method in bybit_session.get_payments_list():
            if (payment_method.paymentType == order.withdraw_currency.payment_id and
                    payment_method.accountNo == order.withdraw_currency.address and
                    payment_method.realName == order.withdraw_name):
                print('WITHDRAW CARD EXIST')
                order.payment_term = PaymentTerm.from_bybit_term(payment_method)
                order.payment_term.save()
                break

        else:  # Добавляем новую карту
            risk_token = bybit_session.add_payment_method(realName=order.withdraw_name, accountNo=order.withdraw_currency.address)
            print('ADD NEW WITHDRAW CARD')
            if not order.verify_risk_token(risk_token, bybit_session):
                return

            bybit_session.add_payment_method(realName=order.withdraw_name, accountNo=order.withdraw_currency.address,
                                             risk_token=risk_token)
            return

        if not order.order_buy_id:  # Запрос к bybit еще не делали
            try:
                if not order.create_p2p_order(side=P2PItem.SIDE_BUY):  # Создаем заказ
                    return  # state -> ERROR
            except TypeError:  # Цена изменилась
                order.verify_order()
                return
                # order.state = OrderBuyToken.STATE_WRONG_PRICE
                # order.error_message = "Цена у p2p вывода изменилась"
                # order.save()
        print('created')
        order.update_p2p_order_status(side=P2PItem.SIDE_BUY)  # state -> STATE_TRANSFERRED
        return

    elif order.state == OrderBuyToken.STATE_TRANSFERRED:  # Ждет подтверждения от продавца
        order.update_p2p_order_messages(side=P2PItem.SIDE_BUY)  # Выгружаем сообщения в базу

        state, terms = bybit_session.get_order_info(order.order_buy_id, order.withdraw_currency.payment_id)
        print('STATE_TRANSFERRED get_order_info', state, terms)
        # if state == 50:
        #     print('Token received')
        #     order.state = OrderBuyToken.STATE_WAITING_CONFIRMATION  # todo доп. проверять
        #     order.dt_received = datetime.datetime.now()
        #     order.save()
        #     process_buy_order_task(order.id)  # Вызывает себя со следующим статусом
        # elif state == 20:
        if state == 20:
            print('Token received')
            order.state = OrderBuyToken.STATE_WAITING_CONFIRMATION  # todo доп. проверять
            order.dt_received = datetime.datetime.now()
            order.save()
            process_buy_order_task(order.id)  # Вызывает себя со следующим статусом

            # print('Waiting for seller')
        elif state == 30:  # todo Выводить ошибку
            print('Appeal')
            order.state = OrderBuyToken.STATE_P2P_APPEAL
            order.save()
        elif state == 10:
            print('order created')
        else:
            raise ValueError("Unknown state", state)

        if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['SELLER'], side=P2PItem.SIDE_BUY):
            return

    elif order.state == OrderBuyToken.STATE_WAITING_CONFIRMATION:
        if order.check_p2p_timeout(minutes=P2P_BUY_TIMEOUTS['CREATED'], side=P2PItem.SIDE_BUY):
            return
        print("Wait withdraw confirmation")
        order.update_p2p_order_messages(side=P2PItem.SIDE_BUY)

    elif order.state == OrderBuyToken.STATE_BUY_CONFIRMED:
        print('Withdraw confirmed')

        state, terms = bybit_session.get_order_info(order.order_buy_id, order.withdraw_currency.payment_id)
        print('STATE_BUY_CONFIRMED state', state, terms)
        if state != 50:  # Если не подтвердили получение средств
            order.finish_buy_order()

        BybitAccount.release_order(order.account_id)

        order.state = OrderBuyToken.STATE_WITHDRAWN
        order.dt_withdrawn = datetime.datetime.now()
        order.save()

      
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
        except TimeoutError as e:
            continue
