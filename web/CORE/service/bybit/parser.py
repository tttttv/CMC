import datetime
import json
import time
import requests
from requests import Session
import uuid
from typing import Optional, List
from urllib.parse import urlparse

from websocket import create_connection

from CORE.service.bybit.models import BybitPaymentTerm
# from CORE.models import P2PItem
from CORE.service.tools.formats import format_float

from CORE.service.CONFIG import P2P_BUY_TIMEOUTS, P2P_EMAIL_SEND_TIMEOUT


# def get_cookies():
#     with open('www.bybit.com.cookies.json', 'r') as f:
#         cookies = json.load(f)
#     return cookies


class TimeoutRequestsSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault('timeout', P2P_EMAIL_SEND_TIMEOUT)
        return super(TimeoutRequestsSession, self).request(*args, **kwargs)


class AuthenticationError(Exception):
    def __init__(self, message="Authentication failed"):
        self.message = message


class InsufficientError(Exception):
    def __init__(self, message="Insufficient ad inventory"):
        self.message = message


class InsufficientErrorSell(InsufficientError):
    pass


class AdStatusChanged(Exception):
    def __init__(self, message="The ad status of your P2P order has been changed"):
        self.message = message


class BybitSession:
    def __init__(self, user):
        self.user_id = user.user_id
        self.session = TimeoutRequestsSession()
        self.user: BybitAccount = user

        if user.use_proxy:
            print('BybitSession proxy settings:', user.proxy_settings)
            self.session.proxies.update(user.proxy_settings)

        for c in user.cookies:
            my_cookie = requests.cookies.create_cookie(name=c['name'], domain=c['domain'], value=c['value'])
            self.session.cookies.set_cookie(my_cookie)

        self.headers = {
            'authority': 'api2.bybit.com',
            'accept': 'application/json',
            'accept-language': 'en-GB,en-US;q=0.9,en;q=0.8',
            'guid': self.session.cookies.get_dict()['_by_l_g_d'],
            'origin': 'https://www.bybit.com',
            'platform': 'pc',
            'referer': 'https://www.bybit.com/',
        }
        self.session.headers.update(self.headers)
        print('COOKIES SUCCESSFULLY SET')

    def get_prices_list(self, token_id='USDT', currency_id='RUB', payment_methods=("379",),
                        items: Optional[list] = None, amount="", side="1", filter_online: bool = True,
                        filter_ineligible: bool = True, user_info: Optional[dict] = None):

        from CORE.models import P2PItem  # FIXME ** Разбить на файлы модель
        """Выгружает список цен на п2п"""
        data = {
            "userId": self.user_id,
            "tokenId": token_id,  # Покупка USDT за RUB
            "currencyId": currency_id,
            "payment": [str(p) for p in payment_methods],  # 379 - Альфа банк
            "side": side,  # 1 - лоты на продажу токенов, 0 - лоты на покупку токенов
            "size": "10000",
            "page": "1",
            "amount": amount,
            # "authMaker": True, - подтвержденный
            "canTrade": True
        }

        r = self.session.post('https://api2.bybit.com/fiat/otc/item/online', json=data)
        resp = r.json()

        if resp['ret_code'] == 0:
            p2p = []
            for item in resp['result']['items']:
                # print(f"Seller id {item['accountId']} online: {item['isOnline']}")
                if filter_online and not item['isOnline']:
                    continue

                if filter_ineligible and user_info:
                    prefs = item['tradingPreferenceSet']

                    # TODO add isKyc / isEmail / isMobile
                    # if prefs['isMobile'] and not user_info:
                    #     continue

                    if (prefs['hasOrderFinishNumberDay30'] and
                            prefs['orderFinishNumberDay30'] >= user_info['recentFinishCount']):
                        continue

                    if prefs['hasUnPostAd'] and not user_info['hasUnPostAd']:
                        continue

                    if prefs['hasRegisterTime'] and prefs['registerTimeThreshold'] >= user_info['accountCreateDays']:
                        continue

                    if prefs['hasNationalLimit'] and user_info['kycCountryCode'] in prefs['nationalLimit']:
                        continue

                    if prefs['hasCompleteRateDay30']:
                        completeRateDay30 = int(prefs['completeRateDay30'])
                        if 0 < completeRateDay30 and completeRateDay30 >= int(user_info['recentRate']):
                            continue

                if not items or item['id'] in items:  # Фильтруем только тех кого запросили
                    p2p.append(P2PItem.from_json(item))
            return p2p
        elif resp['ret_code'] == 10007:
            raise AuthenticationError()
        else:
            print(resp)
            raise ValueError

    def get_item_price(self, item_id):
        """Уточняет цену по айтему перед сделкой"""
        data = {
            "item_id": item_id,
        }
        # {'ret_code': 912300001, 'ret_msg': 'Insufficient ad inventory, please try other ads', 'result': None, 'ext_code': '', 'ext_info': None, 'time_now': '1713650165.224304'}
        print('data:', data)
        r = self.session.post('https://api2.bybit.com/fiat/otc/item/simple', json=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            result = resp['result']
            return {
                'price': float(result['price']),  # цена к покупке
                'lastQuantity': float(result['lastQuantity']),  # остаток селлера
                'curPrice': result['curPrice'],
                'minAmount': float(result['minAmount']),  # минимум валюты
                'maxAmount': float(result['maxAmount']),  # максимум валюты
                'payments': result['payments']
            }
        elif resp['ret_code'] == 912300001:
            raise InsufficientError()
        elif resp['ret_code'] == 10007:  # FIXME TEST
            raise AuthenticationError()
        else:
            print(resp)
            raise ValueError

    def create_order_buy(self, item_id, quantity, amount, cur_price, token_id="USDT", currency_id="RUB"):
        """Создает ордер на обмен валюты"""
        data = {
            "itemId": item_id,
            "flag": "amount",
            "version": "1.0",
            "tokenId": token_id,
            "currencyId": currency_id,
            "securityRiskToken": "",
            "side": "0",
            "quantity": str(format_float(float(quantity), token=token_id)),
            # сумма в крипте, точность зависит от токена
            "amount": str(amount),  # сумма в фиате
            "curPrice": cur_price,
        }
        print(data)

        r = self.session.post("https://api2.bybit.com/fiat/otc/order/create", json=data)
        resp = r.json()
        if resp['ret_code'] == 0:
            return resp['result']['orderId']
        else:
            print(resp)
            if resp['ret_code'] == 912120110:
                return None

            elif resp['ret_code'] == 912100027:
                raise AdStatusChanged('Ad status changed')

            elif resp['ret_code'] == 912100052:  # Не попали в range по amount
                raise AdStatusChanged("LIMIT")

            elif resp['ret_code'] == 41100:
                raise AdStatusChanged('Ad removed')

            elif resp['ret_code'] == 40001:  # FIXME Request parameter verification error В основном наша цена устарела
                raise ValueError('Ad price changed')
                # raise AdStatusChanged('Ad price changed')
            else:
                raise ValueError

    def create_order_sell(self, item_id, quantity, amount, cur_price, payment_type, payment_id, token_id="USDT",
                          currency_id="RUB", risk_token=''):
        """Создает ордер на обмен валюты"""
        data = {
            "itemId": str(item_id),
            "tokenId": token_id,
            "currencyId": currency_id,
            "side": "1",  # 1 - продажа крипты,  0 - покупка
            "quantity": str(format_float(float(quantity), token=token_id)),
            "amount": str(amount),  # сумма в фиате
            "curPrice": cur_price,
            "flag": "amount",
            # "flag": "quantity",  # ORIG
            "version": "1.0",
            "securityRiskToken": risk_token,
            "paymentType": str(payment_type),
            "paymentId": str(payment_id),
            "online": "0"
        }

        print('create_order_sell', data)

        r = self.session.post("https://api2.bybit.com/fiat/otc/order/create", json=data)
        resp = r.json()
        if resp['ret_code'] == 0:
            result = resp['result']
            return result['orderId'], result['securityRiskToken']  # order, risk_token
        else:
            print(resp)
            if resp['ret_code'] == 912120030:
                # raise TypeError('The price has been changed')
                raise AdStatusChanged('The price has been changed')

            elif resp['ret_code'] == 912100027:
                raise AdStatusChanged('Ad status changed')

            elif resp['ret_code'] == 912100052:  # Не попали в range по amount
                raise AdStatusChanged("LIMIT")

            elif resp['ret_code'] == 41100:
                raise AdStatusChanged('Ad removed')
            else:
                print(resp)
                raise ValueError

    def get_order_info(self, order_id, payment_type: Optional[int] = None):
        data = {
            "orderId": order_id
        }
        print('get_order_info', data)
        r = self.session.post("https://api2.bybit.com/fiat/otc/order/info", json=data)
        resp = r.json()
        if resp['ret_code'] == 0:
            result = resp['result']
            for term in result['paymentTermList']:
                term = BybitPaymentTerm(term)
                if not payment_type or str(term.paymentType) == str(payment_type):
                    # 10 - в процессе, 50 - совершено, 20 - при продаже отправили монеты
                    additional_info = {'amount': result['amount'], 'quantity': result['quantity'], 'price': result['price']}
                    return result['status'], term, additional_info
            else:
                print(resp)
                raise NotImplementedError
        else:
            print(resp)
            raise ValueError

    def mark_order_as_paid(self, order_id, payment_id: int, payment_type="379"):
        data = {
            "orderId": order_id,
            "paymentId": payment_id,
            "paymentType": str(payment_type),
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/fiat/otc/order/pay", json=data)
        resp = r.json()

        if resp['ret_code'] == 0:
            return True
        else:
            print(resp)
            raise ValueError

    def get_order_messages(self, order_id):
        data = {
            'orderId': order_id,
            'currentPage': 1,
            'size': 1000
        }
        print('data', data)
        r = self.session.post("https://api2.bybit.com/fiat/otc/order/message/listpage", data=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            messages = []
            for item in resp['result']['result']:
                # messages.append(OrderMessage(item))
                messages.append(item)
            return messages
        else:
            print(resp)
            raise ValueError

    def send_message(self, order_id, message, message_uuid: Optional[str] = None, contentType='str',
                     extra_data: dict = None):
        """Отправляет сообщение в переписку"""
        r = self.session.post('https://api2.bybit.com/user/private/ott')
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            result = resp['result']
            deviceId = self.session.cookies.get_dict()['deviceId']
            url = "wss://ws2.bybit.com/private?appid=bybit&os=web&deviceid=" + deviceId

            # Установка соединения с веб сокетом
            if self.user.use_proxy:
                ws = create_connection(url, http_proxy_host=self.user.proxy_host, http_proxy_port=self.user.proxy_port, proxy_type=self.user.proxy_type,
                                       http_proxy_auth=self.user.proxy_auth)
            else:
                ws = create_connection(url)

            req_id = self.session.cookies.get_dict()['_by_l_g_d']
            data = {"req_id": req_id, "op": "login", "args": [result]}
            ws.send(json.dumps(data))  # Запрос на авторизацию
            result = json.loads(ws.recv())

            if result['success']:  # success auth
                if message_uuid is None:
                    message_uuid = str(uuid.uuid4())  # генерация uuid для сообщения
                BODY = {
                    'topic': 'OTC_USER_CHAT_MSG_V2',
                    'type': 'SEND',
                    'data': {
                        'userId': str(self.user_id),
                        'orderId': str(order_id),
                        'message': str(message),
                        'contentType': str(contentType),  # contentType: str, pdf
                        'msgUuid': message_uuid,
                        'roleType': 'user',
                    },
                    'msgId': f'OTC_USER_CHAT_MSG_V2-SEND-{int(time.time())}-{str(order_id)}',
                    'reqId': str(req_id)
                }

                if extra_data:
                    BODY['data'].update(extra_data)
                print('BODY', BODY)
                data = {
                    "op": "input",
                    "args": [
                        "FIAT_OTC_TOPIC",
                        json.dumps(BODY)
                    ]
                }
                print('data', data)
                ws.send(json.dumps(data))
                result = json.loads(ws.recv())

                if result['success']:
                    return True
                else:
                    ws.close()
                    raise ConnectionRefusedError()
            else:
                ws.close()
                raise ConnectionRefusedError()
        else:
            print(resp)
            raise ValueError()

    def upload_file(self, order_id, file_name, content, content_type, message_uuid: Optional[str] = None):
        files = {'upload_file': (file_name, content, content_type)}  # (file_name, content, 'application/pdf')
        r = self.session.post('https://api2.bybit.com/fiat/p2p/oss/upload_file', files=files)
        resp = r.json()
        print(f'upload_file resp: {resp}')
        if resp['ret_code'] == 0:
            file_url = resp['result']['url']
            parsed_url = urlparse(file_url)
            dist_file_name = parsed_url.path.split('/')[-1]
            print('dist_file_name', dist_file_name, type(dist_file_name))

            if isinstance(dist_file_name, bytes):
                dist_file_name = dist_file_name.decode('utf8')

            file_ext = dist_file_name.split(".")[-1]
            print('new file_ext', file_ext)
            mime_types = {
                'png': 'image/pic',  # TEST
                'jpg': 'image/pic',  # +
                'jpeg': 'image/pic',  # TEST
                'mp4': 'video/video',  # +
                'pdf': 'application/pdf'  # +
            }
            content_type = mime_types[file_ext]
            print('content_type', content_type)
            mtype, subtype = content_type.split('/')  # application/pdf
            extra_data = {
                'type': mtype,
                'tmpName': str(file_name),
                'onlyForCustomer': '0'
            }
            print('extra_data', extra_data)
            result = self.send_message(order_id, file_url, message_uuid=message_uuid, contentType=subtype, extra_data=extra_data)
            print('result', result)
            return result
        return False

    def get_withdraw_risk_token(self, address, amount: float, token='USDT', chain='MANTLE'):
        r = self.session.get(
            "https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/risk-token?" +
            "coin=" + token +
            "&chain=" + chain +
            "&address=" + address +
            "&tag=" +
            "&amount=" + str(format_float(float(amount), token=token)) +
            "&withdrawType=0", headers=self.headers)
        resp = r.json()
        if resp['ret_code'] == 0:
            return resp['result']['riskToken']
        else:
            print(resp)
            raise ValueError
        """
        {
        "ret_code": 0,
        "ret_msg": "success",
        "result": {
            "riskToken": "724714962710916596307030010#1620cca4-f",
            "riskTokenType": "challenge"
        },
        "ext_code": "",
        "ext_info": null,
        "time_now": "1709080747.342739"
        }
        """

    def verify_risk_send_email(self, risk_token):
        data = {
            "risk_token": risk_token,
            "component_id": "email_verify"
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/user/public/risk/send/code", json=data, headers=self.headers)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            if resp['result']['cool_down'] == "0":
                return True
            else:
                raise ConnectionRefusedError
        else:
            print(resp)
            raise ValueError
        {
            "ret_code": 0,
            "ret_msg": "success",
            "result": {
                "cool_down": "0"
            },
            "ext_code": "",
            "ext_info": None,
            "time_now": "1709080799.318239"
        }

    def verify_risk_is_address_verified(self, address, amount, token, chain):
        data = {
            "coin": token,
            "chain": chain,
            "address": address,
            "tag": "",
            "amount": amount,
            "address_type": 0
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/address/address-is-verified",
                              json=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return True
        else:
            print(resp)
            raise ValueError

    def verify_risk_address_check(self, address, token, chain):
        data = {
            "coin": token,
            "chain": chain,
            "address": address,
            "address_type": 0
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/address/address-check", json=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return resp['result']['isCorrect']
        else:
            print(resp)
            raise ValueError

    def verify_risk_withdraw_fee(self, amount, token, chain):
        r = self.session.get(
            'https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/withdraw-fee?coin=' + token + '&amount=' + str(
                amount) + '&withdraw_type=0&is_all=0&chain=' + chain)
        resp = r.json()
        if resp['ret_code'] == 0:
            return resp['result']['fee']
        else:
            print(resp)
            raise ValueError

    def verify_risk_pre_check(self, address, amount, token, chain):
        r = self.session.get('https://api2.bybit.com/v3/private/cht/asset-withdraw/address/pre-check-withdraw-address' +
                             '?coin=' + token + '&chain=' + chain + '&amount=' + str(
            amount) + '&address=' + address + '&tag=')
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return True
        else:
            print(resp)
            raise ValueError

    def verify_risk_is_travel_rule(self, address, amount, token, chain):
        r = self.session.get('https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/is-travel-rule' +
                             '?coin=' + token + '&chain=' + chain + '&amount=' + str(
            amount) + '&address=' + address + '&tag=')
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return True
        else:
            print(resp)
            raise ValueError

    def verify_risk_token(self, risk_token, google_code, email_code=None):
        data = {
            "risk_token": risk_token,
            "component_list": {
                "google2fa": google_code
            }
        }
        if email_code:  # если заодно требуется email верификация
            data['component_list']['email_verify'] = email_code
        print(data)

        r = self.session.post("https://api2.bybit.com/user/public/risk/verify", json=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            for component in resp['result']['component_list']:
                if component['component_code'] != 0:
                    print(resp)
                    raise ConnectionRefusedError
            else:
                return resp['result']['risk_token']
        else:
            print(resp)
            raise ValueError

    {
        "ret_code": 0,
        "ret_msg": "success",
        "result": {
            "risk_token": "724714962710916596307030010#1620cca4-f",
            "ret_code": 0,
            "component_list": [
                {
                    "component_id": "google2fa",
                    "component_code": 0,
                    "ext_info": {}
                },
                {
                    "component_id": "email_verify",
                    "component_code": 0,
                    "ext_info": {}
                }
            ]
        },
        "ext_code": "",
        "ext_info": None,
        "time_now": "1709080987.246192"
    }

    def onchain_withdraw(self, address, amount, risk_token, token='USDT', chain='MANTLE'):
        data = {
            "coin": token,
            "chain": chain,
            "address": address,
            "tag": "",
            "amount": str(format_float(amount, token=token)),
            "is_verified": True,
            "risk_verified_result_token": risk_token,
            "account_type": 6
        }

        print(data)
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/onChain-withdraw",
                              json=data)
        resp = r.json()
        if resp['ret_code'] == 0:
            return True
        else:
            print(resp)
            raise ValueError
        {
            "ret_code": 0,
            "ret_msg": "success",
            "result": {},
            "ext_code": "",
            "ext_info": None,
            "time_now": "1709080989.726645"
        }

    def check_payment_method(self, paymentID):
        print('delete_payment_method')
        data = {'id': paymentID}
        r = self.session.post('https://api2.bybit.com/fiat/otc/item/payment', data=data)

        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return True
        return False

    def add_payment_method(self, realName, accountNo, payment_type='377', risk_token=None):
        print('add_payment_method')
        data = {
            'paymentType': payment_type,
            'realName': realName,
            'accountNo': accountNo,
        }
        if risk_token:
            data['securityRiskToken'] = risk_token

        r = self.session.post('https://api2.bybit.com/fiat/otc/user/payment/new_create', data=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return resp['result']['securityRiskToken']
        else:
            print(resp)
            raise ValueError

    def delete_payment_method(self, paymentId, risk_token=None):
        print('delete_payment_method')
        data = {'id': paymentId}

        if risk_token:
            data['securityRiskToken'] = risk_token

        r = self.session.post('https://api2.bybit.com/fiat/otc/user/payment/new_delete', data=data)

        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return resp['result']['securityRiskToken']
        else:
            print(resp)
            raise ValueError

    def get_payments_list(self) -> List[BybitPaymentTerm]:
        r = self.session.post('https://api2.bybit.com/fiat/otc/user/payment/list')
        resp = r.json()

        if resp['ret_code'] == 0:
            payments = []
            for payment in resp['result']:
                payments.append(BybitPaymentTerm(payment))
            return payments
        else:
            print(resp)
            raise ValueError
        {
            "ret_code": 0,
            "ret_msg": "SUCCESS",
            "result": [
                {
                    "id": "-1",
                    "realName": "",
                    "paymentType": 416,
                    "bankName": "",
                    "branchName": "",
                    "accountNo": "",
                    "qrcode": "",
                    "visible": 0,
                    "payMessage": "",
                    "firstName": "",
                    "lastName": "",
                    "secondLastName": "",
                    "clabe": "",
                    "debitCardNumber": "",
                    "mobile": "",
                    "businessName": "",
                    "concept": "",
                    "online": "1",
                    "countNo": "",
                    "paymentExt1": "",
                    "paymentExt2": "",
                    "paymentExt3": "",
                    "paymentExt4": "",
                    "paymentExt5": "",
                    "paymentExt6": "",
                    "paymentTemplateVersion": 0,
                    "hasPaymentTemplateChanged": False,
                    "paymentConfigVo": {
                        "paymentType": "416",
                        "checkType": 5,
                        "sort": 0,
                        "paymentName": "Balance",
                        "addTips": "This payment method enables transfers of assets in the Funding Account between Bybit users. Please make sure you have sufficient funds before initiating a purchase.",
                        "itemTips": "This payment method enables transfers of assets in the Funding Account between Bybit users. Please make sure you have sufficient funds before initiating a purchase.",
                        "online": 1,
                        "items": []
                    },
                    "realNameVerified": False,
                    "channel": "bybit"
                },
                {
                    "id": "3379619",
                    "realName": "Куртынов Владимир",
                    "paymentType": 377,
                    "bankName": "",
                    "branchName": "",
                    "accountNo": "4276420030240021",
                    "qrcode": "",
                    "visible": 0,
                    "payMessage": "",
                    "firstName": "",
                    "lastName": "",
                    "secondLastName": "",
                    "clabe": "",
                    "debitCardNumber": "",
                    "mobile": "",
                    "businessName": "",
                    "concept": "",
                    "online": "0",
                    "countNo": "",
                    "paymentExt1": "",
                    "paymentExt2": "",
                    "paymentExt3": "",
                    "paymentExt4": "",
                    "paymentExt5": "",
                    "paymentExt6": "",
                    "paymentTemplateVersion": 1,
                    "hasPaymentTemplateChanged": False,
                    "paymentConfigVo": {
                        "paymentType": "377",
                        "checkType": 0,
                        "sort": 0,
                        "paymentName": "Sberbank",
                        "addTips": "",
                        "itemTips": "",
                        "online": 0,
                        "items": [
                            {
                                "view": True,
                                "name": "realName",
                                "label": "Name",
                                "placeholder": "Please Enter Name",
                                "type": "text",
                                "maxLength": "50",
                                "required": True
                            },
                            {
                                "view": True,
                                "name": "accountNo",
                                "label": "Bank Account Number",
                                "placeholder": "Please Enter Account Number",
                                "type": "text",
                                "maxLength": "100",
                                "required": True
                            },
                            {
                                "view": True,
                                "name": "branchName",
                                "label": "Bank Branch",
                                "placeholder": "Please Enter Bank Branch",
                                "type": "text",
                                "maxLength": "100",
                                "required": False
                            },
                            {
                                "view": True,
                                "name": "bankName",
                                "label": "Bank Name",
                                "placeholder": "Please Enter Bank Name",
                                "type": "text",
                                "maxLength": "100",
                                "required": False
                            }
                        ]
                    },
                    "realNameVerified": False,
                    "channel": "bybit"
                }
            ],
            "ext_code": "",
            "ext_info": None,
            "time_now": "1709081810.937200"
        }

    """
    Логика:
    Simple -> Create (risk token) -> components -> verify -> create -> info
    
    """

    def get_risk_components(self, risk_token):  # обязательно
        data = {
            "risk_token": risk_token
        }
        r = self.session.post('https://api2.bybit.com/user/public/risk/components', json=data, headers=self.headers)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            components = []
            for component in resp['result']['component_list']:
                components.append(component['component_id'])
            return components
        else:
            print(resp)
            raise ValueError()
        {
            "ret_code": 0,
            "ret_msg": "success",
            "result": {
                "risk_token": "282814933279113642847030036#5f380ea3-d",
                "component_type": 2,
                "component_list": [
                    {
                        "component_id": "google2fa",
                        "component_extension": "",
                        "disposal": "",
                        "disposal_extension": ""
                    }
                ],
                "logc_ext": {
                    "required": [
                        "google2fa"
                    ],
                    "option": []
                }
            },
            "ext_code": "",
            "ext_info": None,
            "time_now": "1709081944.604493"
        }

    """
    Логика:
    Finish (risk token) -> components -> verify -> finish -> info

    """

    def finish_p2p_sell(self, order_id, payment_type='377', country_code='RU', risk_token=''):
        data = {
            "orderId": order_id,
            "paymentType": int(payment_type),
            "countryCode": country_code,
            "securityRiskToken": risk_token
        }

        headers = {  # без этого не работает
            'guid': self.session.cookies.get_dict()['_by_l_g_d'],
        }

        r = self.session.post('https://api2.bybit.com/fiat/otc/order/finish', headers=headers, json=data)
        resp = r.json()

        if resp['ret_code'] == 0:
            return resp['result']['securityRiskToken']
        else:
            print(resp)
            raise ValueError()
        {
            "ret_code": 0,
            "ret_msg": "SUCCESS",
            "result": {
                "success": False,
                "securityRiskToken": "999314964113616480597030039#2733b34a-5",
                "riskTokenType": "challenge",
                "riskVersion": "1",
                "needSecurityRisk": True
            },
            "ext_code": "",
            "ext_info": None,
            "time_now": "1709082450.108636"
        }

    def get_payment_methods(self):
        """Список доступных способов оплаты"""
        r = self.session.post('https://api2.bybit.com/fiat/otc/configuration/queryAllPaymentList')
        resp = r.json()
        if resp['ret_code'] == 0:
            with open('payment_methods.json', 'w') as f:
                f.write(json.dumps(resp['result'], indent=4))
            return True
        else:
            return False

    def addressbook_check(self, address, token='USDT', chain='MANTLE'):
        data = {
            "coin": token,
            "address": address,
            "chain": chain,
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/address/address-check", json=data)
        resp = r.json()

        if resp['ret_code'] == 0:
            return resp['result']['isExisted']
        else:
            print(resp)
            raise ValueError()

    def addressbook_get_risk_token(self, address, token='USDT', chain='MANTLE'):
        info = {
            "addresses":
                [
                    {
                        "coin": token,
                        "address": address,
                        "chain_type": chain,
                        "is_verified": False,
                        "address_type": 0
                    }
                ]
        }
        data = {
            'sence': '30062',
            'ext_info_str': json.dumps(info)
        }

        r = self.session.post("https://api2.bybit.com/user/public/risk/default-intercept", data=data,
                              headers=self.headers)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return resp['result']['risk_token']
        else:
            print(resp)
            raise ValueError

    def addressbook_create_address(self, address, risk_token, token='USDT', chain='MANTLE'):
        data = {
            "coin": token,
            "address": address,
            "chain_type": chain,
            "is_verified": False,  # Вывод без 2фа
            "address_type": 0,
            "risk_verified_result_token": risk_token
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/address/address-create", json=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return True
            # return resp['result']['riskToken']
        else:
            print(resp)
            raise ValueError

    @classmethod
    def download_p2p_file_attachment(cls, file_path):  # Можно без сессии получать
        r = requests.get(f'https://api2.bybit.com/{file_path}')
        if r.status_code == 200:
            parsed_url = urlparse(file_path)
            filename = parsed_url.path.split('/')[-1]
            return filename, r.content
        return None, None

    def get_user_info(self) -> Optional[dict]:
        timestamp = int(time.time() * 1000)

        r = self.session.post("https://api2.bybit.com/fiat/otc/user/personal/info", params={'t': timestamp})
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return resp['result']
        elif resp['ret_code'] == 10007:
            print('AuthenticationError')
            raise AuthenticationError()
        else:
            print('exc:', resp)
            raise ValueError

    def get_deposit_address(self, token: str = 'USDT', chain: str = 'MANTLE'):
        params = {
            'coin': token,
            'chain': chain
        }

        r = self.session.get(f"https://api2.bybit.com/v3/private/cht/asset-deposit/deposit/address-chain", params=params)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            if resp['result']['chain'] == chain:
                return resp['result']
            else:
                raise ValueError
        else:
            print(resp)
            raise ValueError

    def get_deposit_status(self, token_name: Optional[str] = None):
        params = {
            'status': 0,
            'pageSize': 20,
            'type': 0
        }
        if token_name:
            params['coin'] = token_name  # 'USDT, 'NEAR', 'BTC' ...

        r = self.session.get(f"https://api2.bybit.com/v3/private/cht/asset-deposit/deposit/aggregate-records", params=params)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return resp['result']['list']
        else:
            print(resp)
            raise ValueError

    def get_withdraw_status(self, token_name: Optional[str] = None):
        params = {
            'page': 1,
            'withdraw_type': 2,
            'page_size': 20
        }
        if token_name:
            params['coin'] = token_name  # 'USDT, 'NEAR', 'BTC' ...

        r = self.session.get(f"https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/aggregated-list", params=params)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return resp['result']['list']
        else:
            print(resp)
            raise ValueError

    def get_available_balance(self, token_name: str = 'USDT') -> float:
        data = {
            'tokenId': token_name
        }
        r = self.session.post(f"https://api2.bybit.com/fiat/otc/user/availableBalance", data=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            for token_balance in resp['result']:
                if token_balance['tokenId'] == token_name:
                    return float(token_balance['available'])
        else:
            print(resp)
            raise ValueError
        return 0.0

    def get_unified_balance(self, token_name: str = 'USDT') -> float:
        r = self.session.post(f"https://api2.bybit.com/siteapi/unified/private/account-walletbalance")
        resp = r.json()

        if resp['retCode'] == 0:
            for token_balance in resp['result']['coinList']:
                print('token_balance', token_balance)
                if token_balance['coin'] == token_name:
                    balance = token_balance['wb']
                    return float(balance) if balance else 0.0
        else:
            print(resp)
            raise ValueError
        return 0.0

    def get_funding_balance(self, token_name: str = 'USDT') -> float:

        r = self.session.get('https://api2.bybit.com/fiat/private/fund-account/balance-list?account_category=crypto')
        resp = r.json()

        if resp['ret_code'] == 0:
            for token_balance in resp['result']:
                print('token_balance', token_balance)
                if token_balance['currency'] == token_name:
                    balance = token_balance['balance']
                    return float(balance) if balance else 0.0
        else:
            print(resp)
            raise ValueError
        return 0.0

    def get_p2p_orders(self) -> Optional[dict]:
        data = {'page': 1, 'size': 10}
        r = self.session.post(f"https://api2.bybit.com/fiat/otc/order/simplifyList", data=data)
        resp = r.json()

        if resp['ret_code'] == 0:
            items = resp['result']['items']
            for item in items:
                print('item', item['id'], item['side'], item['amount'], item['currencyId'], item['price'], item['notifyTokenId'],
                    item['notifyTokenQuantity'], item['status'])
            return items
        else:
            print(resp)
            raise ValueError
        return None


if __name__ == '__main__':
    from CORE.models import BybitAccount

    account = BybitAccount.objects.get(id=2)
    bybit_session = BybitSession(account)
    # result = bybit_session.get_deposit_address('USDT', 'MANTLE')
    # print(result)

    # result = bybit_session.get_deposit_status()

    # payments = bybit_session.get_payments_list()
    # print(payments)
    from CORE.service.tools.formats import format_float_up

    item_id = "1797264716497227776"
    data = bybit_session.get_item_price(item_id)
    amount = 520.45
    quantity = amount / data['price']
    print('quantity', quantity)
    quantity = str(format_float_up(float(quantity), token='USDT'))
    print('quantity', quantity)

    # quantity = self.usdt_amount
    # amount = self.withdraw_amount,

    bybit_session.create_order_sell(item_id=item_id, amount=500, quantity=quantity, cur_price=data['curPrice'],
                                    payment_id=6235204, payment_type=377, token_id='USDT', currency_id='RUB')
    # REQ
    {"itemId": "1797207041813614592", "tokenId": "USDT", "currencyId": "RUB", "side": "1", "quantity": "5.5948", "amount": "500",
     "curPrice": "674722da90574ca1afcd974b691829ef",
     "flag": "amount", "version": "1.0", "securityRiskToken": "", "paymentType": "377", "paymentId": "6235204", "online": "0"}
    # YA
    {'itemId': '1797207041813614592', 'flag': 'quantity', 'version': '1.0', 'tokenId': 'USDT', 'currencyId': 'RUB', 'securityRiskToken': '', 'side': '1',
     'quantity': '5.5948',
     'amount': '500', 'curPrice': '5e25bdce173947b19aec95b874cb5c75', 'paymentType': '377', 'paymentId': 6235204, 'online': '0'}

    # create_order_sell
    {'itemId': '1797243172272623616', 'tokenId': 'USDT', 'currencyId': 'RUB', 'side': '1', 'quantity': '5.5056', 'amount': '500.0',
     'curPrice': 'e59d5461de2e492abb4cb5c71b3b6076',
     'flag': 'amount', 'version': '1.0', 'securityRiskToken': '', 'paymentType': '377', 'paymentId': '6235204', 'online': '0'}
