import datetime
import logging
import random
from django.db.models import Q
from CORE.models import BybitAccount, RiskEmail, P2POrderBuyToken, P2PItem, P2POrderMessage, BybitCurrency
from CORE.service.bybit.parser import BybitSession, AuthenticationError
from CORE.service.bybit.code_2fa import get_codes, get_addressbook_codes
from CORE.service.CONFIG import P2P_BUY_TIMEOUTS, P2P_EMAIL_SEND_TIMEOUT, P2P_WITHDRAW_TIMEOUT, P2P_TOKENS
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
    message = P2POrderMessage.objects.select_related('order__account', 'order__order_id').get(id=message_id)
    bybit_session = BybitSession(message.order.account)
    if bybit_session.send_message(message.order.order_id, message.text, message_uuid=message.uuid):
        message.status = message.STATUS_DELIVERED
    else:
        message.status = message.STATUS_ERROR
    message.save()

@shared_task()
def task_send_image(message_id: int, content_type: str):
    message = P2POrderMessage.objects.select_related('order__account', 'order__order_id').get(id=message_id)
    bybit_session = BybitSession(message.order.account)

    with message.file.open('r') as f:
        content = f.read()

    if bybit_session.upload_file(message.order.order_id, message.file.name, content, content_type):
        message.status = message.STATUS_DELIVERED
    else:
        message.status = message.STATUS_ERROR
    message.save()

@shared_task
def update_latest_email_codes_task(user_id=None):
    if user_id:
        accounts = BybitAccount.objects.filter(user_id=user_id, is_active=True)
    else:
        accounts = BybitAccount.objects.filter(is_active=True)

    for account in accounts:
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
                                                   IMAP_PASSWORD=account.imap_password, IMAP_SERVER=account.imap_server)
        print(addressbook_emails)
        for email in addressbook_emails:
            risk = RiskEmail()
            risk.account = account
            risk.code = email['code']
            risk.dt = email['dt']
            risk.save()


@shared_task
def process_orders_messages_task():  # Ошибочные статусы доп проверки
    orders_buy_token = P2POrderBuyToken.objects.filter(state__in=[P2POrderBuyToken.STATE_WITHDRAWN,
                                                                  P2POrderBuyToken.STATE_TRANSFERRED,
                                                                  P2POrderBuyToken.STATE_PAID])
    for order in orders_buy_token:
        process_receive_order_message_task.delay(order.id)


@shared_task
def process_receive_order_message_task(order_id):
    order = P2POrderBuyToken.objects.get(id=order_id)

    if order.state in [P2POrderBuyToken.STATE_WITHDRAWN,
                       P2POrderBuyToken.STATE_TRANSFERRED,
                       P2POrderBuyToken.STATE_PAID]:

        bybit_session = BybitSession(order.account)
        messages = bybit_session.get_order_messages(order.order_id)  # Выгружаем сообщения
        for msg in messages:
            message = P2POrderMessage.from_json(order.id, msg)
            if message:
                message.save()


@shared_task
def process_receive_order_message_task_direct(order_id):
    order = P2POrderBuyToken.objects.get(id=order_id)
    bybit_session = BybitSession(order.account)
    messages = bybit_session.get_order_messages(order.order_id)
    for msg in messages:
        message = P2POrderMessage.from_json(order.id, msg)
        if message:
            message.save()


@shared_task
def process_orders_task():
    orders_buy_token = P2POrderBuyToken.objects.filter(~Q(state=P2POrderBuyToken.STATE_WITHDRAWN),
                                                       # Ошибочные статусы доп проверки
                                                       is_executing=False,
                                                       is_stopped=False)
    for order in orders_buy_token:
        process_buy_order_task.delay(order.id)


@shared_task
def healthcare_orders_task():  # Проверяем время выполнение таска
    orders_buy_token = P2POrderBuyToken.objects.filter(
        ~Q(state=P2POrderBuyToken.STATE_WITHDRAWN), is_stopped=False)

    dt_now = datetime.datetime.now() - datetime.timedelta(minutes=60)

    for order in orders_buy_token:
        if order.dt_created < dt_now:
            order.is_stopped = True
            order.error_status = 'task timeout'
            order.save()
        elif order.is_executing:
            order_tasks = get_active_celery_tasks()
            for task in order_tasks:
                if task['name'] == 'CORE.tasks.process_buy_order_task' and task['args'][0] == order.order_id:
                    break
            else:
                print('Order task worker die!')  # FIXME нет атомарности / таска в запуске


@shared_task
def process_buy_order_task(order_id):
    order: P2POrderBuyToken = P2POrderBuyToken.objects.get(id=order_id)

    with order_task_lock(order.id):
        bybit_session = BybitSession(order.account)
        bybit_api = order.account.get_api()

        print('ORDER', order.id, order.state, order.account.imap_username)  # email
        if order.state == P2POrderBuyToken.STATE_INITIATED:
            if not order.order_id:  # Бывает такое что заказ не создавался / Запрос к bybit еще не делали
                order.create_order()

            state, terms = bybit_session.get_order_info(order.order_id, order.payment_method.payment_id)
            print('Got state', state)
            order.order_status = int(state)
            order.terms = terms.to_json()
            if order.terms:  # Может не выгрузиться из-за ошибок
                order.state = P2POrderBuyToken.STATE_CREATED
                order.save()  # Нужно отдать клиенту реквизиты и ждать оплаты
        elif order.state == P2POrderBuyToken.STATE_CREATED:  # На этом этапе ждем подтверждения со стороны пользователя
            if order.dt_created.replace(tzinfo=None) < (
                    datetime.datetime.now() - datetime.timedelta(minutes=P2P_BUY_TIMEOUTS['CREATED'])):
                print('Order timeout')
                order.state = P2POrderBuyToken.STATE_TIMEOUT
                order.save()
            else:
                print('WAITING FOR CUSTOMER TO PAY')
                messages = bybit_session.get_order_messages(order.order_id)  # Выгружаем сообщения из базы
                for msg in messages:
                    message = P2POrderMessage.from_json(order.id, msg)
                    if message:
                        message.save()
        elif order.state == P2POrderBuyToken.STATE_TRANSFERRED:  # Оплачен клиентом
            if bybit_session.mark_order_as_paid(order.order_id, order.terms['payment_id'],
                                                order.payment_method.payment_id):
                print('Order marked as paid')
                order.state = P2POrderBuyToken.STATE_PAID
                order.dt_paid = datetime.datetime.now()
                order.save()
        elif order.state == P2POrderBuyToken.STATE_PAID:  # Ждет подтверждения от продавца
            messages = bybit_session.get_order_messages(order.order_id)  # Выгружаем сообщения из базы
            for msg in messages:
                message = P2POrderMessage.from_json(order.id, msg)
                if message:
                    message.save()

            state, terms = bybit_session.get_order_info(order.order_id, order.payment_method.payment_id)

            if state == 50:
                print('Token received')
                order.state = P2POrderBuyToken.STATE_RECEIVED  # todo доп. проверять
                order.dt_received = datetime.datetime.now()
                order.save()
                process_buy_order_task(order.id)  # Вызывает себя со следующим статусом
            elif state == 20:
                print('Waiting for seller')
            elif state == 30:  # todo Выводить ошибку
                print('Appeal')
                # order.is_stopped = True
                order.state = P2POrderBuyToken.STATE_P2P_APPEAL
                order.save()
            else:
                raise ValueError("Unknown state", state)

            if order.dt_paid.replace(tzinfo=None) < (
                    datetime.datetime.now() - datetime.timedelta(minutes=P2P_BUY_TIMEOUTS['CREATED'])):
                print('SELLER timeout')
                # order.is_stopped = True
                order.state = P2POrderBuyToken.STATE_ERROR
                order.save()
        elif order.state == P2POrderBuyToken.STATE_RECEIVED:  # Переводим на биржу
            if order.p2p_token == order.withdraw_token:  # Если не нужно менять валюту на бирже
                order.state = P2POrderBuyToken.STATE_WITHDRAWING
                order.save()
                process_buy_order_task(order.id)
                return
            else:  # Нужно менять
                bybit_api.transfer_to_trading(order.p2p_token, order.p2p_available_balance)  # Переводим на биржу
                order.state = P2POrderBuyToken.STATE_TRADING
                order.dt_trading = datetime.datetime.now()
                order.save()
        elif order.state == P2POrderBuyToken.STATE_TRADING:  # Todo добавить проверку на волатильность TEST
            # trading_quantity = order.withdraw_from_trading_account / (1 - order.trading_commission)
            # buy_p2p = order.amount / order.p2p_price

            total_price = bybit_api.get_price_for_amount(order.withdraw_token, order.p2p_token, order.trading_quantity)
            trade_rate = total_price / order.trading_quantity
            print('total_price', total_price)
            print('trade_rate', trade_rate)
            # trade_rate = bybit_api.get_trading_rate(order.withdraw_token, order.p2p_token)

            # buy_p2p * (1 - platform_commission) / withdraw_token_rate > buy_p2p / trade_rate * 1.03

            if trade_rate > ((1 - order.platform_commission) * order.withdraw_token_rate * 1.03):
                print('diff', trade_rate, order.withdraw_token_rate * 1.03,
                      ((1 - order.platform_commission) * order.withdraw_token_rate * 1.03))
                order.state = P2POrderBuyToken.STATE_ERROR
                order.save()

            market_order_id = bybit_api.place_order(order.withdraw_token, order.p2p_token, order.trading_quantity)
            order.market_order_id = market_order_id
            order.state = P2POrderBuyToken.STATE_TRADED
            order.save()
        elif order.state == P2POrderBuyToken.STATE_TRADED:
            status = bybit_api.get_order_status(order.market_order_id)
            print(status)
            if status == 'Filled' or status == 'PartiallyFilledCanceled':  # Успешно вывели
                bybit_api.transfer_to_funding(order.withdraw_token,
                                              order.withdraw_from_trading_account)  # todo выводить минус комиссия 0.1% near
                order.state = P2POrderBuyToken.STATE_WITHDRAWING
                order.save()
            elif status == 'PartiallyFilledCanceled':  # Todo проработать логику
                raise ValueError("Не до конца выполнено")
            else:
                print(status)
                raise ValueError("Unknown status")
        elif order.state == P2POrderBuyToken.STATE_WITHDRAWING:  # Инициализируем вывод крипты
            existed = bybit_session.addressbook_check(order.withdraw_address, order.withdraw_token,
                                                      order.withdraw_chain)
            if not existed:  # Если в адресной книге нет адреса
                risk_token = bybit_session.addressbook_get_risk_token(order.withdraw_address, order.withdraw_token,
                                                                      order.withdraw_chain)
                components = bybit_session.get_risk_components(risk_token)
                print(components)
                if len(components) == 2:  # Если email верификация - плохо
                    bybit_session.verify_risk_send_email(risk_token)
                    code = input('please enter your code')
                    bybit_session.verify_risk_token(risk_token, order.account.risk_get_ga_code(), email_code=code)
                else:
                    bybit_session.verify_risk_token(risk_token, order.account.risk_get_ga_code())

                bybit_session.addressbook_create_address(order.withdraw_address, risk_token, order.withdraw_token,
                                                         order.withdraw_chain)

            order.state = P2POrderBuyToken.STATE_WAITING_VERIFICATION
            order.dt_verification = datetime.datetime.now()
            order.save()
        elif order.state == P2POrderBuyToken.STATE_WAITING_VERIFICATION:  # Ждем код на почту
            print(order.withdraw_quantity)
            if bybit_api.withdraw(order.withdraw_token, order.withdraw_chain, order.withdraw_address,
                                  order.withdraw_quantity):  # todo выводить минус комиссия вывода 0.01 near
                print('Withdrawn successfully')
                order.state = P2POrderBuyToken.STATE_WITHDRAWN
                order.dt_withdrawn = datetime.datetime.now()
                order.save()

        """Заменено на вывод через API 
        elif order.state == P2POrderBuyToken.STATE_WITHDRAWING: #Инициализируем вывод крипты
            if order.dt_received.replace(tzinfo=None) < datetime.datetime.now() - datetime.timedelta(seconds=P2P_WITHDRAW_TIMEOUT): #Если больше 30 минут пытаемся вывести крипту
                order.state = P2POrderBuyToken.STATE_ERROR
                order.save()
                return order

            if not order.risk_token: #Получаем риск-токен
                risk_token = s.get_withdraw_risk_token(order.withdraw_address, order.withdraw_quantity, order.withdraw_token, order.withdraw_chain)
                print('Got risk token', risk_token)
            else:
                risk_token = order.risk_token

            print(s.session.cookies.keys())
            COOKIES_TO_DELETE = ['low_broswer', 'g_state', 'cookies_uuid_report', 'first_collect', 'tx_token_current', 'tx_token_time', 'trace_id_time', 'by_token_print', 'deviceCodeExpire', 'wcs_bt']
            for c in COOKIES_TO_DELETE:
                try: #может не быть
                    s.session.cookies.pop(c)
                except:
                    pass
            print('-'*10)
            print(s.session.cookies.keys())


            code = ''
            try:
                code = s.verify_risk_send_email(risk_token)
                print(code)
            except:
                try: #Чтобы код отправился, почему-то достаточно получить ошибку верификации
                    print('risk token')
                    s.verify_risk_token(risk_token, order.risk_get_ga_code(), email_code='123456')
                except:
                    code = s.verify_risk_send_email(risk_token)
                    print(code)

            if code: #Возможно зависает из-за cookie deviceCodeExpire или by_token_prin
                print('Email sent')
                order.state = P2POrderBuyToken.STATE_WAITING_VERIFICATION
                order.dt_verification = datetime.datetime.now()
                order.risk_token = risk_token
                order.save()
                update_latest_email_codes_task(order.account.user_id)
        elif order.state == P2POrderBuyToken.STATE_WAITING_VERIFICATION: #Ждем код на почту
            email_code = order.risk_get_email_code()
            print('Email code:', email_code)
            if email_code: #Todo учесть комиссию блокчейна
                try:
                    risk_token = s.verify_risk_token(order.risk_token, order.risk_get_ga_code(), email_code=email_code)
                except ConnectionRefusedError:
                    order.state = P2POrderBuyToken.STATE_WITHDRAWING
                    order.risk_token = None
                    print('returned to recevived')
                    order.save()
                    process_buy_order_task(order.id)
                    return order

                print('Risk token', risk_token)
                if s.onchain_withdraw(order.withdraw_address, order.withdraw_quantity, risk_token, token=order.withdraw_token, chain=order.withdraw_chain):
                    print('Witdrawn successfully')
                    order.state = P2POrderBuyToken.STATE_WITHDRAWN
                    order.dt_withdrawn = datetime.datetime.now()
                    order.save()
            else:
                if order.dt_verification.replace(tzinfo=None) < datetime.datetime.now() - datetime.timedelta(seconds=P2P_BUY_TIMEOUTS['EMAIL_CODE']): #Ждем письмо не больше 3 минут
                    print('Email waiting timeout')
                    order.risk_token = None
                    order.state = P2POrderBuyToken.STATE_RECEIVED
                    order.save()
                    process_buy_order_task(order.id)
        """
    return
