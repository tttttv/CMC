import datetime
import random

from django.db import models
from django.db.models import Q

from CORE.service.bybit.api import BybitAPI
from CORE.service.bybit.code_2fa import get_ga_token
from CORE.service.bybit.models import OrderMessage
from CORE.service.CONFIG import  TOKENS_DIGITS
from CORE.service.tools.tools import calculate_withdraw_amount


class BybitSettings(models.Model):
    """Настройки одни на всю систему, ориентируемся на модель с номером 1"""
    #currencies = models.JSONField(default=dict) #Список валют доступных к обмену, {'CUR': [methods], ...}
    #payment_methods = models.JSONField(default=list) #Список методов оплаты, [{"payment_type": 377, "payment_name": "Sberbank", ...}]
    #tokens = models.JSONField(default=list) #Список токенов [{'id': 'USDT', 'name': 'USDT', 'chains': [{'name': 'MANTLE', 'id': 'MANTLE'},]},]
    #parsing_settings = models.JSONField(default=dict) #Список методов оплаты для парсинга [{'token': 'USDT', 'currency': 'RUB', 'payment_methods': [377, 379]}]
    #avalible_to_withdraw = models.JSONField(default=dict) #Список досупных для вывода монет/чейнов {'USDT': ['MANTLE'], 'BTC': ['']}
    #commissions = models.JSONField(default=dict) #Список комиссий вывода {'USDT': 0.01, 'BTC': 0.02}

    banks = models.JSONField(default=dict)
    """
    banks = [
        {
            'id': 'RUB',
            'name': 'Рубли',
            'payment_methods': [
                {
                    'bank_name': 'Альфа Банк',
                    'id': 377,
                }
            ],
        }
    ]
    """

    tokens = models.JSONField(default=dict)
    """
    tokens = [
        {
            'id': 'USDT',
            'name': 'USDT',
            'chains': [
                {
                    'name': 'MANTLE',
                    'id': 'MANTLE'
                }
            ],
            'payment_methods': [377, 379],
            'withdraw_commission': 0.01
        }
    ]
    """

    def __str__(self):
        return 'Настройки'

    @property
    def is_working(self):
        return True

    def get_payment_method(self, method):
        for cur in self.banks:
            for pm in cur['payment_methods']:
                if pm['id'] == method:
                    method = pm
                    method['currency'] = cur['id']
                    method['logo'] = '/static/CORE/banks/' + str(method['id']) + '.png'
                    return method
        else:
            raise ValueError("Payment method not found")

    def get_chain(self, token ,chain):
        tk = self.get_token(token)
        if tk:
            for c in tk['chains']:
                if c['id'] == chain:
                    return c
        return None

    def get_token(self, token):
        for t in self.tokens:
            if t['id'] == token:
                tk = t
                tk['logo'] = '/static/CORE/tokens/' + str(tk['id']) + '.png'
                return tk
        else:
            raise ValueError("Token not found")

    def get_avalible_topup_methods(self):
        banks = self.banks
        for i in range(0, len(banks)):
            for j in range(0, len(banks[i]['payment_methods'])):
                banks[i]['payment_methods'][j]['logo'] = '/static/CORE/banks/' + str(banks[i]['payment_methods'][j]['id']) + '.png'
        return banks

    def get_avalible_withdraw_methods(self):
        tokens = self.tokens
        for index in range(0, len(tokens)):
            tokens[index].pop('withdraw_commission')
            tokens[index]['crypto'] = True
            tokens[index]['logo'] = '/static/CORE/tokens/' + str(tokens[index]['id']) + '.png'
        return tokens

    def get_payment_method_name(self, type: int):
        for currency in self.banks:
            for payment_method in currency['payment_methods']:
                if payment_method['id'] == type:
                    return payment_method['bank_name']
        else:
            return "Не найден способ оплаты"


class BybitAccount(models.Model):
    is_active = models.BooleanField(default=True)
    user_id = models.IntegerField(unique=True) #Айди пользователя
    cookies = models.JSONField(default=list) #Куки пользователя
    cookies_updated = models.DateTimeField(default=datetime.datetime.now) #Время установки кук
    cookies_valid = models.BooleanField(default=True) #Не возникало ошибок с куками
    ga_secret = models.CharField(max_length=30, default='GHO5UKQ3IDTCRIXY') #Секрет гугл 2фа
    imap_username = models.CharField(max_length=50) #Почта привязанная к аккаунту
    imap_server = models.CharField(max_length=50) #Сервер почты
    imap_password = models.CharField(max_length=30) #Пароль от почты
    proxy_settings = models.JSONField(default=dict, blank=True, null=True) #Настройки прокси, привязанные к аккаунту

    api_key = models.CharField(max_length=50, blank=True, null=True)
    api_secret = models.CharField(max_length=50, blank=True, null=True)


    def risk_get_ga_code(self):
        return get_ga_token(self.ga_secret)

    def risk_get_email_code(self, address, amount):
        email = RiskEmail.objects.filter(address=address, amount=amount, used=False).order_by('-dt').first()
        email_rounded = RiskEmail.objects.filter(address=address, amount=round(amount, 4), used=False).order_by('-dt').first()
        if not email:
            email = email_rounded

        if email:
            email.used = True
            email.save()
            return email.code
        else:
            return None

    def __str__(self):
        return str(self.user_id)

    def get_api(self):
        return BybitAPI(api_key=self.api_key, api_secret=self.api_secret)

    @classmethod
    def get_free(cls):
        """ Возвращает аккаунт, на котором нет активных P2P сделок"""
        accounts = BybitAccount.objects.all()
        for account in accounts:
            if not P2POrderBuyToken.objects.filter(dt_received=None).exclude(state__in=[P2POrderBuyToken.STATE_WRONG_PRICE, P2POrderBuyToken.STATE_TIMEOUT]).exists():
                return account
        else:
            return None #Нет свободных аккаунтов

    @classmethod
    def get_random_account(cls):
        return random.choice(BybitAccount.objects.filter(is_active=True).all())

class RiskEmail(models.Model):
    """Парсинг верификационных писем с email"""
    account = models.ForeignKey(BybitAccount, on_delete=models.CASCADE) #ссылка на аккаунт с которого пришло письмо
    code = models.CharField(max_length=100) #Код подтверждения
    amount = models.FloatField(max_length=100, blank=True, null=True, default=None) #Сумма транзакции
    address = models.CharField(max_length=100, blank=True, null=True, default=None) #Адрес на который переводится крипта
    dt = models.DateTimeField() #Время получения письма
    used = models.BooleanField(default=False) #Использовали ли код

    def __str__(self):
        return '[' + self.dt.strftime('%d.%m.%Y %H:%M:%S') + '] => ' + str(self.amount)

class P2PItem(models.Model):
    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'
    ITEM_SIDE = (
        (SIDE_BUY, 'Покупка'),
        (SIDE_SELL, 'Продажа'),
    )

    item_id = models.CharField(max_length=50, unique=True) #Айди лота
    user_id = models.IntegerField() #Айди продавца
    price = models.FloatField() #Цена токена
    quantity = models.FloatField() #Доступно
    min_amount = models.FloatField() #Минимум фиата
    max_amount = models.FloatField() #Максимум фиата
    dt_updated = models.DateTimeField(default=datetime.datetime.now) #Время выгрузки данных
    side = models.CharField(max_length=10, choices=ITEM_SIDE)
    payment_methods = models.JSONField(default=list) #Список айди методов
    remark = models.TextField(blank=True, null=True) #Ремарка к лоту

    currency = models.CharField(max_length=50, default='RUB')
    token = models.CharField(max_length=50, default='USDT')
    is_active = models.BooleanField(default=True) #Активен ли сейчас продавец

    def __repr__(self):
        return '{P2P: ' + str(self.id) + ' ' + str(self.price) + '}'

    def __str__(self):
        return '[' + self.side + '] ' + str(self.item_id)

    def get_payment_methods(self):
        res = []
        settings = BybitSettings.objects.all().first()
        for method in self.payment_methods:
            res.append(settings.get_payment_method_name(method))
        return res

    @classmethod
    def from_json(cls, data):
        if P2PItem.objects.filter(item_id=data['id']).exists():
            item = P2PItem.objects.get(item_id=data['id'])
        else:
            item = P2PItem()

        item.item_id = data['id']
        item.user_id = int(data['userId'])
        item.token = data['tokenId']
        item.currency = data['currencyId']
        item.price = float(data['price'])
        item.quantity = float(data['quantity'])
        item.min_amount = float(data['minAmount'])
        item.max_amount = float(data['maxAmount'])
        item.payment_methods = [int(p) for p in data['payments']]
        item.remark = data.get('remark', None)
        item.side = P2PItem.SIDE_SELL if int(data['side']) == 1 else P2PItem.SIDE_BUY

        return item

class P2POrderBuyToken(models.Model):
    STATE_INITIATED = 'INITIATED'
    STATE_WRONG_PRICE = 'WRONG'
    STATE_CREATED = 'CREATED'
    STATE_TRANSFERRED = 'TRANSFERRED' #Переведено клиентом
    STATE_PAID = 'PAID' #Ждет подтверждения продавца
    STATE_RECEIVED = 'RECEIVED'  # Токен получен
    STATE_TRADING ='TRADING'
    STATE_TRADED = 'TRADED'
    STATE_WITHDRAWING = 'WITHDRAWING' #Токен получен
    STATE_WAITING_VERIFICATION = 'VERIFICATION' #Ожидание верификации по почте
    STATE_WITHDRAWN = 'WITHDRAWN' #Токен выведен на кошелек
    STATE_TIMEOUT = 'TIMEOUT' #Отменен по времени
    STATE_ERROR = 'ERROR' #Ошибка вывода после получения средств клиента
    STATE_CANCELLED = 'CANC' #Отменен пользователем

    STATES = (
        (STATE_INITIATED, 'Инициализирован'),
        (STATE_WRONG_PRICE, 'Не совпадает цена'),
        (STATE_CREATED, 'Сделка создана'),
        (STATE_TRANSFERRED, 'Средства переведены клиентом'),
        (STATE_PAID, 'Ждет продавца'),
        (STATE_RECEIVED, 'Продавец подтвердил'),
        (STATE_TRADING, 'Обмен на бирже'),
        (STATE_TRADED, 'Обменено на бирже'),
        (STATE_WITHDRAWING, 'Вывод монет'),
        (STATE_WAITING_VERIFICATION, '2-ФА'),
        (STATE_WITHDRAWN, 'Средства выведены'),
        (STATE_TIMEOUT, 'Просрочен'),
        (STATE_ERROR, 'Ошибка вывода валюты'),
        (STATE_CANCELLED, 'Отменен пользователем')
    )

    account = models.ForeignKey(BybitAccount, on_delete=models.CASCADE)

    name = models.CharField(max_length=100, default='')
    card_number = models.CharField(max_length=100, default='')
    email = models.CharField(max_length=100, default='')

    item = models.ForeignKey(P2PItem, on_delete=models.CASCADE)
    payment_method = models.IntegerField()
    amount = models.FloatField()
    currency = models.CharField(max_length=10)
    p2p_token = models.CharField(max_length=30, default='USDT')
    p2p_price = models.FloatField()

    #Информация для вывода средств
    withdraw_price = models.FloatField(default=1, null=True)
    withdraw_token = models.CharField(max_length=30, default='USDT')
    withdraw_chain = models.CharField(max_length=30, default='MANTLE')
    withdraw_address = models.CharField(max_length=100)

    #INITIATED
    dt_initiated = models.DateTimeField(default=datetime.datetime.now)

    #CREATED
    dt_created = models.DateTimeField(default=None, blank=True, null=True)
    order_id = models.CharField(max_length=30, blank=True, null=True)
    order_status = models.IntegerField(default=10, blank=True, null=True)
    terms = models.JSONField(default=dict, blank=True, null=True)
    payment_id = models.CharField(max_length=50, blank=True, null=True)

    #TRANSFERRED
    dt_transferred = models.DateTimeField(default=None, blank=True, null=True)

    #PAID
    dt_paid = models.DateTimeField(default=None, blank=True, null=True)

    #RECEIVED
    dt_received = models.DateTimeField(default=None, blank=True, null=True)
    risk_token = models.CharField(max_length=50, blank=True, null=True)

    #TRADING
    dt_trading = models.DateTimeField(default=None, blank=True, null=True)
    market_order_id = models.CharField(max_length=50, blank=True, null=True)

    #VERIFICATION
    dt_verification= models.DateTimeField(default=None, blank=True, null=True)

    #WITHDRAWN
    dt_withdrawn = models.DateTimeField(default=None, blank=True, null=True)

    state = models.CharField(max_length=20, choices=STATES, default=STATE_INITIATED)

    HASH_CONSTANT = 35742549198872617291353508656626642567
    @classmethod
    def get_order_by_hash(cls, hash):
        id = hash ^ P2POrderBuyToken.HASH_CONSTANT
        return P2POrderBuyToken.objects.filter(id=id).first()

    def get_hash(self):
        return self.id ^ P2POrderBuyToken.HASH_CONSTANT

    @property
    def p2p_quantity(self):
        digits = TOKENS_DIGITS[self.p2p_token]
        return float((('{:.' + str(digits) + 'f}').format(self.amount / self.p2p_price)))

    @property
    def withdraw_quantity(self):
        return calculate_withdraw_amount(self.withdraw_token, self.withdraw_chain, self.amount, self.p2p_price, self.withdraw_price)

    def risk_get_ga_code(self):
        return self.account.risk_get_ga_code()

    def risk_get_email_code(self):
        return self.account.risk_get_email_code(self.withdraw_address, self.withdraw_quantity)


class P2POrderMessage(models.Model):
    order_id = models.CharField(max_length=50)

    message_id = models.CharField(max_length=50)
    account_id = models.CharField(max_length=50, blank=True, null=True)
    text = models.TextField()
    dt = models.DateTimeField(blank=True, null=True)
    uuid = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    nick_name = models.CharField(max_length=50, blank=True, null=True)
    type = models.CharField(max_length=50)  # 1 - переписка, иначе служебное

    @classmethod
    def create_from_parser(cls, order_id, data: OrderMessage):
        if not P2POrderMessage.objects.filter(message_id=data.id).exists():
            message = P2POrderMessage(order_id=order_id)
            message.message_id = data.id
            message.account_id = data.accountId
            message.text = data.text
            message.dt = datetime.datetime.utcfromtimestamp(data.createdDate / 1000)
            message.uuid = data.msgUuid
            message.user_id = data.userId
            message.nick_name = data.nickName
            message.type = data.msgType
            message.save()

    def to_json(self):
        return {
            'nick_name': self.nick_name,
            'text': self.text,
            'dt': self.dt.strftime('%d.%m.%Y %H:%M:%S'),
            'uuid': self.uuid,
            'image_url': None
        }
