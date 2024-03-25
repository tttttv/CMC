import json
import time
import requests
from requests import Session
import uuid

from websocket import create_connection

from CORE.service.bybit.models import PaymentTerm, OrderMessage
from CORE.models import P2PItem
from CORE.service.tools.formats import format_float

from CORE.service.CONFIG import P2P_BUY_TIMEOUTS, P2P_EMAIL_SEND_TIMEOUT


def get_cookies():
    with open('www.bybit.com.cookies.json', 'r') as f:
        cookies = json.load(f)
    return cookies

class TimeoutRequestsSession(requests.Session):
    def request(self, *args, **kwargs):
        kwargs.setdefault('timeout', P2P_EMAIL_SEND_TIMEOUT)
        return super(TimeoutRequestsSession, self).request(*args, **kwargs)

class BybitSession(Session):
    def __init__(self, user):
        self.user_id = user.user_id
        self.session = TimeoutRequestsSession()
        self.user = user

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

    def get_prices_list(self, token_id='USDT', currency_id='RUB', payment_methods=["379"], items=[], amount="", side="1"):
        """Выгружает список цен на п2п"""
        data = {
            "userId": self.user_id,
            "tokenId": token_id,  # Покупка USDT за RUB
            "currencyId": currency_id,
            "payment": [str(p) for p in payment_methods], #379 - Альфа банк
            "side": side, #1 - лоты на продажу токенов, 0 - лоты на покупку токенов
            "size": "10000",
            "page": "1",
            "amount": amount,
            "authMaker": True,
            "canTrade": True
        }

        print(data)
        r = self.session.post('https://api2.bybit.com/fiat/otc/item/online', json=data)
        resp = r.json()

        print(resp)
        if resp['ret_code'] == 0:
            p2p = []
            for item in resp['result']['items']:
                if (not items) or (item['id'] in items): #Фильтруем только тех кого запросили
                    p2p.append(P2PItem.from_json(item))
            return p2p
        else:
            print(resp)
            raise ValueError

    def get_item_price(self, item_id):
        """Уточняет сцену по айтему перед сделкой"""
        data = {
            "item_id": item_id,
        }

        r = self.session.post('https://api2.bybit.com/fiat/otc/item/simple', json=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return {
                'price': float(resp['result']['price']),  # цена к покупке
                'lastQuantity': float(resp['result']['lastQuantity']),  # остаток селлера
                'curPrice': resp['result']['curPrice'],
                'minAmount': float(resp['result']['minAmount']),  # минимум валюты
                'maxAmount': float(resp['result']['maxAmount']),  # максимум валюты
            }
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
            "quantity": str(format_float(float(quantity), token=token_id)), #сумма в крипте, точность зависит от токена
            "amount": str(amount), #сумма в фиате
            "curPrice": cur_price,
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/fiat/otc/order/create", json=data)
        resp = r.json()
        if resp['ret_code'] == 0:
            return resp['result']['orderId']
        else:
            print(resp)
            raise ValueError


    def create_order_sell(self, item_id, quantity, amount, cur_price, payment_type, payment_id, token_id="USDT", currency_id="RUB", risk_token=''):
        """Создает ордер на обмен валюты"""
        data = {
            "itemId": item_id,
            "flag": "quantity",
            "version": "1.0",
            "tokenId": token_id,
            "currencyId": currency_id,
            "securityRiskToken": risk_token,
            "side": "1", #1 - продажа крипты,  0 - покупка
            "quantity": str(format_float(float(quantity), token=token_id)), #сумма в крипте, тут не совсем понятно как округлять и сколько знаков
            "amount": str(amount), #сумма в фиате
            "curPrice": cur_price,
            "paymentType": payment_type,
            "paymentId": payment_id,
            "online": "0"
        }

        print(data)
        r = self.session.post("https://api2.bybit.com/fiat/otc/order/create", json=data)
        resp = r.json()
        if resp['ret_code'] == 0:
            return resp['result']['orderId'], resp['result']['securityRiskToken'] #order, risk_token
        elif resp['ret_code'] == 912120030:
            raise ValueError('The price has been changed')
        else:
            print(resp)
            raise ValueError

    def get_order_info(self, order_id, payment_type=None):
        data = {
            "orderId": order_id
        }
        r = self.session.post("https://api2.bybit.com/fiat/otc/order/info", json=data)
        resp = r.json()
        if resp['ret_code'] == 0:
            terms = []
            for term in resp['result']['paymentTermList']:
                term = PaymentTerm(term)
                if (not payment_type) or (str(term.paymentType) == str(payment_type)):
                    return resp['result']['status'], term #10 - в процессе, 50 - совершено, 20 - при продаже отправили монеты
            else:
                print(resp)
                raise NotImplementedError
        else:
            print(resp)
            raise ValueError

    def mark_order_as_paid(self, order_id, payment_id, payment_type="379"):
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
        r = self.session.post("https://api2.bybit.com/fiat/otc/order/message/listpage", data=data)
        resp = r.json()

        if resp['ret_code'] == 0:
            messages = []
            for item in resp['result']['result']:
                messages.append(OrderMessage(item))
            return messages
        else:
            print(resp)
            raise ValueError

    def send_message(self, order_id, message):
        """Отправляет сообщение в переписку"""
        r = self.session.post('https://api2.bybit.com/user/private/ott')
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            result = resp['result']
            deviceId = self.session.cookies.get_dict()['deviceId']
            url = "wss://ws2.bybit.com/private?appid=bybit&os=web&deviceid=" + deviceId
            ws = create_connection(url) #Установка соединения с веб сокетом

            req_id = self.session.cookies.get_dict()['_by_l_g_d']
            data = {"req_id": req_id, "op": "login", "args": [result]}
            ws.send(json.dumps(data)) #Запрос на авторизацию
            result = json.loads(ws.recv())

            if result['success'] == True:  # success auth
                myuuid = str(uuid.uuid4()) #генерация uuid для сообщения
                data = {
                    "op": "input",
                    "args": [
                        "FIAT_OTC_TOPIC",
                        "{\"topic\":\"OTC_USER_CHAT_MSG_V2\",\"type\":\"SEND\",\"data\":{\"userId\":" + str(self.user_id) + ",\"orderId\":\"" + str(order_id) + "\",\"message\":\"" + message + "\",\"contentType\":\"str\",\"msgUuid\":\"" + myuuid + "\",\"roleType\":\"user\"},\"msgId\":\"OTC_USER_CHAT_MSG_V2-SEND-" + str(
                            int(time.time())) + "-" + str(order_id) + "\",\"reqId\":\"" + req_id + "\"}"
                    ]
                }
                ws.send(json.dumps(data))
                result = json.loads(ws.recv())
                if result['success'] == True:
                    return True
                else:
                    ws.close()
                    raise ConnectionRefusedError()
            else:
                ws.close()
                raise ConnectionRefusedError()
            ws.close()
        else:
            print(resp)
            raise ValueError()

    def upload_file(self, file):
        files = {'upload_file': file}
        r = s.post('https://api2.bybit.com/fiat/p2p/oss/upload_file', data=files)
        resp = r.json()

        if resp['ret_code'] == 0:
            return True

    def get_withdraw_risk_token(self, address, amount:float, token='USDT', chain='MANTLE'):
        r = self.session.get(
            "https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/risk-token?" + \
            "coin=" + token + \
            "&chain=" + chain + \
            "&address=" + address + \
            "&tag=" + \
            "&amount=" + str(format_float(float(amount), token=token)) + \
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
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/address/address-is-verified", json=data)
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
        r = self.session.get('https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/withdraw-fee?coin=' + token + '&amount=' + str(amount) + '&withdraw_type=0&is_all=0&chain=' + chain)
        resp = r.json()
        if resp['ret_code'] == 0:
            return resp['result']['fee']
        else:
            print(resp)
            raise ValueError

    def verify_risk_pre_check(self, address, amount, token, chain):
        r = self.session.get('https://api2.bybit.com/v3/private/cht/asset-withdraw/address/pre-check-withdraw-address' + \
                '?coin=' + token + '&chain=' + chain + '&amount=' + str(amount) + '&address=' + address + '&tag=')
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return True
        else:
            print(resp)
            raise ValueError

    def verify_risk_is_travel_rule(self, address, amount, token, chain):
        r = self.session.get('https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/is-travel-rule' + \
                '?coin=' + token + '&chain=' + chain + '&amount=' + str(amount) + '&address=' + address + '&tag=')
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
        if email_code: #если заодно требуется email верификация
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
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/withdraw/onChain-withdraw", json=data)
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

    def add_payment_method(self, real_name, account_number, payment_type='377', risk_token=None):
        data = {
            'paymentType': payment_type,
            'realName': real_name,
            'accountNo': account_number,
        }
        if risk_token:
            data['securityRiskToken'] = risk_token

        r = self.session.post('https://api2.bybit.com/fiat/otc/user/payment/new_create', data=data)
        resp = r.json()

        if resp['ret_code'] == 0:
            return resp['result']['securityRiskToken']
        else:
            print(resp)
            raise ValueError
        {
            "ret_code": 0,
            "ret_msg": "SUCCESS",
            "result": {
                "securityRiskToken": "740314913866111711827030041#4446dc59-9",
                "riskTokenType": "challenge",
                "riskVersion": "1",
                "needSecurityRisk": true
            },
            "ext_code": "",
            "ext_info": null,
            "time_now": "1709081427.406440"
        }

    def get_payments_list(self):
        r = self.session.post('https://api2.bybit.com/fiat/otc/user/payment/list')
        resp = r.json()

        if resp['ret_code'] == 0:
            payments = []
            for payment in resp['result']:
                payments.append(PaymentTerm(payment))
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
    def get_risk_components(self, risk_token): #обязательно
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

        headers = { #без этого не работает
            'guid': self.session.cookies.get_dict()['_by_l_g_d'],
        }

        r = self.session.post('https://api2.bybit.com/fiat/otc/order/finish',  headers=headers, json=data)
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
        "Список доступных способов оплаты"
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
                            "is_verified":False,
                            "address_type":0
                        }
                    ]
            }
        data = {
            'sence': '30062',
            'ext_info_str': json.dumps(info)
        }


        r = self.session.post("https://api2.bybit.com/user/public/risk/default-intercept", data=data, headers=self.headers)
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
            "is_verified": False, #Вывод без 2фа
            "address_type": 0,
            "risk_verified_result_token": risk_token
        }
        print(data)
        r = self.session.post("https://api2.bybit.com/v3/private/cht/asset-withdraw/address/address-create", json=data)
        resp = r.json()
        print(resp)
        if resp['ret_code'] == 0:
            return True
            return resp['result']['riskToken']
        else:
            print(resp)
            raise ValueError

if __name__ == '__main__':
    s = BybitSession('147000319')
    payments = s.get_payments_list()
    print(payments)
