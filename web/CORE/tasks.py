import datetime
import random

from django.db.models import Q

from CORE.models import BybitSettings, BybitAccount, RiskEmail, P2POrderBuyToken, P2PItem, P2POrderMessage
from CORE.service.bybit.parser import BybitSession
from CORE.service.bybit.code_2fa import get_codes, get_addressbook_codes

from CORE.service.CONFIG import P2P_BUY_TIMEOUTS, P2P_EMAIL_SEND_TIMEOUT, P2P_WITHDRAW_TIMEOUT, P2P_TOKENS

from celery import shared_task


@shared_task
def update_p2pitems_task():
    settings = BybitSettings.objects.first()
    for currency in settings.banks:
        #for method in currency['payment_methods']:
            accounts = BybitAccount.objects.filter(is_active=True)
            account = random.choice(accounts)
            s = BybitSession(account)

            items_sale= s.get_prices_list(token_id='USDT', currency_id=currency['id'],
                              payment_methods=[method['id'] for method in currency['payment_methods']], side="1") #лоты на продажу
            items_buy = s.get_prices_list(token_id='USDT', currency_id=currency['id'],
                              payment_methods=[method['id'] for method in currency['payment_methods']], side="0")  #лоты на покупку

            P2PItem.objects.filter(is_active=True).update(is_active=False)

            for item in (items_sale + items_buy):
                print(item)
                if P2PItem.objects.filter(item_id=item.item_id).exists():
                    item.id = P2PItem.objects.get(item_id=item.item_id).id
                    print(item.id)
                item.is_active = True
                item.save()

@shared_task
def update_latest_email_codes_task(user_id=None):
    if user_id:
        accounts = BybitAccount.objects.filter(user_id=user_id, is_active=True)
    else:
        accounts = BybitAccount.objects.filter(is_active=True)

    for account in accounts:
        emails = get_codes(IMAP_USERNAME=account.imap_username, IMAP_PASSWORD=account.imap_password, IMAP_SERVER=account.imap_server)
        for email in emails:
            risk = RiskEmail()
            risk.account = account
            risk.code = email['code']
            risk.amount = float(email['amount'])
            risk.address = email['address']
            risk.dt = email['dt']
            risk.save()

        addressbook_emails = get_addressbook_codes(IMAP_USERNAME=account.imap_username, IMAP_PASSWORD=account.imap_password, IMAP_SERVER=account.imap_server)
        print(addressbook_emails)
        for email in addressbook_emails:
            risk = RiskEmail()
            risk.account = account
            risk.code = email['code']
            risk.dt = email['dt']
            risk.save()

@shared_task
def process_orders_task():
    orders_buy_token = P2POrderBuyToken.objects.filter(~Q(state=P2POrderBuyToken.STATE_WITHDRAWN))
    for order in orders_buy_token:
        process_buy_order_task(order.id)

@shared_task
def process_buy_order_task(order_id):
    order = P2POrderBuyToken.objects.get(id=order_id)
    accounts = BybitAccount.objects.filter(is_active=True)
    account = random.choice(accounts)
    s = BybitSession(account)

    print(order.id, order.state)
    if order.state == P2POrderBuyToken.STATE_INITIATED:

        if order.withdraw_token not in P2P_TOKENS:  # Если нужно трейдить токен, покупаем в USDT
            order.withdraw_price = order.account.get_api().get_price(order.withdraw_token, 'USDT')
            order.p2p_token = 'USDT'
        else: #Если нет - покупаем ту же валюту
            order.withdraw_price = 1
            order.p2p_token = order.withdraw_token
        order.save()

        price = s.get_item_price(order.item.item_id) #Хэш от стоимости
        print('Got price')

        if price['price'] != order.p2p_price: #Не совпала цена
            order.state = P2POrderBuyToken.STATE_WRONG_PRICE
            order.save()
            return order

        order_id = s.create_order_buy(order.item.item_id, order.p2p_quantity, order.amount, price['curPrice'], token_id=order.p2p_token, currency_id=order.currency)
        order.dt_created = datetime.datetime.now()
        order.order_id = order_id
        order.state = P2POrderBuyToken.STATE_CREATED
        order.save()

        state, terms = s.get_order_info(order_id, order.payment_method)
        print('Got state', state)
        order.order_status = int(state)
        order.terms = terms.to_json()
        order.save() #Нужно отдать клиенту реквизиты и ждать оплаты
    elif order.state == P2POrderBuyToken.STATE_CREATED: #На этом этапе ждем подтверждения со стороны пользователя
        if order.dt_created.replace(tzinfo=None) < (datetime.datetime.now() - datetime.timedelta(minutes=P2P_BUY_TIMEOUTS['CREATED'])):
            print('Order timeout')
            order.state = P2POrderBuyToken.STATE_TIMEOUT
            order.save()
        else:
            print('WAITING FOR CUSTOMER TO PAY')
            messages = s.get_order_messages(order.order_id) #Выгружаем сообщения из базы
            for m in messages:
                P2POrderMessage.create_from_parser(order.order_id, m)
    elif order.state == P2POrderBuyToken.STATE_TRANSFERRED: #Оплачен клиентом
        if s.mark_order_as_paid(order.order_id, order.terms['payment_id'], order.payment_method):
            print('Order marked as paid')
            order.state = P2POrderBuyToken.STATE_PAID
            order.dt_paid = datetime.datetime.now()
            order.save()
    elif order.state == P2POrderBuyToken.STATE_PAID: #Ждет подтверждения от продавца
        #Todo сколько времени на подтверждение продавцом? - 10 мин, но дальше аппеляция
        state, terms = s.get_order_info(order.order_id, order.payment_method)

        messages = s.get_order_messages(order.order_id)  # Выгружаем сообщения из базы
        for m in messages:
            P2POrderMessage.create_from_parser(order.order_id, m)

        if state == 50:
            print('Token received')
            order.state = P2POrderBuyToken.STATE_RECEIVED
            order.dt_received = datetime.datetime.now()
            order.save()
            process_buy_order_task(order.id) #Вызывает себя со следующим статусом
        elif state == 20:
            print('Waiting for seller')
        elif state == 30:
            print('Appeal')
        else:
            raise ValueError("Unknown state", state)
    elif order.state == P2POrderBuyToken.STATE_RECEIVED: #Переводим на биржу
        if order.p2p_token == order.withdraw_token: #Если не нужно менять валюту на бирже
            order.state = P2POrderBuyToken.STATE_WITHDRAWING
            order.save()
            process_buy_order_task(order.id)
            return order
        else: #Нужно менять
            api = order.account.get_api()
            api.transfer_to_trading(order.p2p_token, order.p2p_quantity) #Переводим на биржу
            order.state = P2POrderBuyToken.STATE_TRADING
            order.dt_trading = datetime.datetime.now()
            order.save()
    elif order.state == P2POrderBuyToken.STATE_TRADING: #Todo добавить проверку на волатильность
        api = order.account.get_api()
        market_order_id = api.place_order(order.withdraw_token, order.p2p_token, order.withdraw_quantity)
        order.market_order_id = market_order_id
        order.state = P2POrderBuyToken.STATE_TRADED
        order.save()
    elif order.state == P2POrderBuyToken.STATE_TRADED:
        api = order.account.get_api()
        status = api.get_order_status(order.market_order_id)
        print(status)
        if status == 'Filled' or status == 'PartiallyFilledCanceled': #Успешно вывели
            api.transfer_to_funding(order.withdraw_token, order.withdraw_quantity)
            order.state = P2POrderBuyToken.STATE_WITHDRAWING
            order.save()
        elif status == 'PartiallyFilledCanceled': #Todo ghjhf,jnfnm kjubre
            raise ValueError("Не до конца выполнено")
        else:
            print(status)
            raise ValueError("Unknown status")
    elif order.state == P2POrderBuyToken.STATE_WITHDRAWING:  # Инициализируем вывод крипты
        existed = s.addressbook_check(order.withdraw_address, order.withdraw_token, order.withdraw_chain)
        if not existed: #Если в адресной книге нет адреса
            risk_token = s.addressbook_get_risk_token(order.withdraw_address, order.withdraw_token, order.withdraw_chain)
            components = s.get_risk_components(risk_token)
            print(components)
            if len(components) == 2: #Если email верификация - плохо
                s.verify_risk_send_email(risk_token)
                code = input('please enter your code')
                s.verify_risk_token(risk_token, account.risk_get_ga_code(), email_code=code)
            else:
                s.verify_risk_token(risk_token, account.risk_get_ga_code())
            s.addressbook_create_address(order.withdraw_address, risk_token, order.withdraw_token, order.withdraw_chain)

        order.state = P2POrderBuyToken.STATE_WAITING_VERIFICATION
        order.dt_verification = datetime.datetime.now()
        order.save()
    elif order.state == P2POrderBuyToken.STATE_WAITING_VERIFICATION:  # Ждем код на почту
        api = account.get_api()
        print(order.withdraw_quantity)
        if api.withdraw(order.withdraw_token, order.withdraw_chain, order.withdraw_address, order.withdraw_quantity):
            print('Witdrawn successfully')
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
    return order


