import datetime
import hashlib
import random
import time
import secrets
import base64
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.db import models, transaction
from django.db.models import Q

from CORE.service.bybit.api import BybitAPI
from CORE.service.bybit.code_2fa import get_ga_token
# from CORE.service.bybit.models import OrderMessage
from CORE.service.CONFIG import TOKENS_DIGITS

from CORE.service.tools.formats import file_as_base64
from CORE.service.CONFIG import P2P_TOKENS

class BybitSeller(models.Model):
    item_id = models.IntegerField()
    account_id = models.IntegerField()
    userId = models.IntegerField()
    # whitelist
    is_available = models.BooleanField()

class BybitCurrency(models.Model):
    TYPE_FIAT = 'fiat'
    TYPE_CRYPTO = 'crypto'
    TYPES = (
        (TYPE_FIAT, 'Фиат'),
        (TYPE_CRYPTO, 'Криптовалюта'),
    )

    CURRENCY_RUB = 'RUB'
    CURRENCY_USDT = 'USDT'
    CURRENCY_NEAR = 'NEAR'
    CURRENCY = (
        (CURRENCY_RUB, 'Рубль'),
        (CURRENCY_USDT, 'USDT'),
        (CURRENCY_NEAR, 'NEAR'),  # TODO перечислить все варианты
    )

    type = models.CharField(max_length=10, choices=TYPES)
    name = models.CharField(max_length=20)  # АльфаБанк Сбербанк USDT NEAR
    chains = models.JSONField(default=list, blank=True, null=True)
    # TODO chains -> chain м можно все withdraw_token(fiat) сделать ForeignKey -> withdraw_currency

    payment_id = models.IntegerField(default=None, blank=True, null=True, verbose_name="ID Банка")  # 337 339
    token = models.CharField(max_length=10, choices=CURRENCY, verbose_name='Токен валюты')  # RUB / USDT / NEAR

    # Список валют за которые можно покупать
    exchange_from = models.ManyToManyField("self", blank=True, symmetrical=False, related_name='exchange_to')

    def __str__(self):
        return self.name

    def logo(self):
        if self.type == self.TYPE_FIAT:
            return f'/static/CORE/banks/{self.id}.png'
        else:
            return f'/static/CORE/tokens/{self.token}.png'

    def to_json(self) -> dict:  # TODO Serialize
        return {'id': self.id, 'type': self.type,
                'name': self.get_token_display(), 'chains': self.chains,
                'logo': self.logo()}

    @staticmethod
    def cache_exchange_from(available_payment_methods: list = None):  # ЛЕВАЯ ЧАСТЬ
        fiats = {}
        tokens = []
        currencies = BybitCurrency.objects.filter(exchange_to__isnull=False).all().distinct()
        for currency in currencies:
            if available_payment_methods and currency.id not in available_payment_methods:
                continue

            exchange_to = list(currency.exchange_to.values_list('id', flat=True))
            if currency.type == BybitCurrency.TYPE_FIAT:
                payment_method = {'id': currency.id, 'name': currency.name, 'logo': currency.logo(),
                                  'exchange_to': exchange_to}
                if currency.token not in fiats:
                    fiats[currency.token] = {'id': currency.token,  # 'type': currency.type,
                                             'name': currency.get_token_display(),
                                             'payment_methods': [payment_method]}
                else:
                    fiats[currency.token]['payment_methods'].append(payment_method)

            elif currency.type == BybitCurrency.TYPE_CRYPTO:
                token_data = {'id': currency.id,  # 'id': currency.token,  'type': currency.type,
                              'name': currency.get_token_display(), 'chains': currency.chains,
                              'logo': currency.logo(),
                              'exchange_to': exchange_to}
                tokens.append(token_data)

        return {'fiat': list(fiats.values()), 'crypto': tokens}

    @staticmethod
    def cache_exchange_to(withdrawing_token=None, withdrawing_chain=None):  # ПРАВАЯ ЧАСТЬ
        fiats = {}
        tokens = []  # Валюты которые мы можем обменять
        currencies = BybitCurrency.objects.filter(exchange_from__isnull=False).all().distinct()
        for currency in currencies:
            if withdrawing_token and withdrawing_token != currency.token:
                continue

            exchange_from = list(currency.exchange_from.values_list('id', flat=True))
            if currency.type == BybitCurrency.TYPE_FIAT:
                payment_method = {'id': currency.id, 'name': currency.name, 'logo': currency.logo(),
                                  'exchange_from': exchange_from}
                if currency.token not in fiats:
                    fiats[currency.type] = {'id': currency.token,  # 'type': currency.type,
                                            'name': currency.get_token_display(),
                                            'payment_methods': [payment_method],
                                            'exchange_from': exchange_from}
                else:
                    fiats[currency.type]['payment_methods'].append(payment_method)
            elif currency.type == BybitCurrency.TYPE_CRYPTO:
                token_data = {'id': currency.id,  # id': currency.token, 'type': currency.type,
                              'name': currency.get_token_display(), 'chains': currency.chains,
                              'logo': currency.logo(),
                              'exchange_from': exchange_from}
                tokens.append(token_data)
        return {'fiat': list(fiats.values()), 'crypto': tokens}

    @staticmethod
    def get_currency(method_id: int):
        print('method_id:', method_id)
        return BybitCurrency.objects.get(id=method_id)

    @staticmethod
    def get_token(token):
        return BybitCurrency.objects.get(token=token)

    def get_chain(self, chain):
        for c in self.chains:
            if c['id'] == chain:
                return c
        return None

    def validate_exchange(self, other):
        return self.exchange_from.filter(id=other.id).exists()

    def payment_methods(self):
        return list(self.exchange_from.values_list('payment_id', flat=True))

    @staticmethod
    def all_payment_methods():
        return BybitCurrency.objects.filter(exchange_to__isnull=False).distinct()

    def validate_chain(self, chain_id: str) -> bool:
        for chain in self.chains:
            if chain['id'] == chain_id:
                return True
        return False

class BybitAccount(models.Model):
    is_active = models.BooleanField(default=True)
    user_id = models.IntegerField(unique=True)  # Айди пользователя
    # nick_name = models.CharField(default='')  # Ник пользователя
    cookies = models.JSONField(default=list)  # Куки пользователя
    cookies_updated = models.DateTimeField(default=datetime.datetime.now)  # Время установки кук
    cookies_valid = models.BooleanField(default=True)  # Не возникало ошибок с куками
    ga_secret = models.CharField(max_length=30, default='GHO5UKQ3IDTCRIXY')  # Секрет гугл 2фа
    imap_username = models.CharField(max_length=50)  # Почта привязанная к аккаунту
    imap_server = models.CharField(max_length=50)  # Сервер почты
    imap_password = models.CharField(max_length=30)  # Пароль от почты
    proxy_settings = models.JSONField(default=dict, blank=True, null=True)  # Настройки прокси, привязанные к аккаунту

    api_key = models.CharField(max_length=50, blank=True, null=True)
    api_secret = models.CharField(max_length=50, blank=True, null=True)

    is_active_commentary = models.CharField(max_length=200, default='')

    active_order = models.OneToOneField('P2POrderBuyToken', on_delete=models.SET_NULL, null=True, blank=True)
    # Можно просто флаг

    def risk_get_ga_code(self):
        return get_ga_token(self.ga_secret)

    def risk_get_email_code(self, address, amount):
        email = RiskEmail.objects.filter(address=address, amount=amount, used=False).order_by('-dt').first()
        email_rounded = RiskEmail.objects.filter(address=address, amount=round(amount, 4), used=False).order_by(
            '-dt').first()
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
    def assign_order(cls, order_id):  # FIXME
        with transaction.atomic:
            query = BybitAccount.objects.filter(order__isnull=True)
            count = query.count()
            if count == 0:
                return None

            random_index = random.randint(0, count - 1)
            account = query.all()[random_index:random_index + 1].select_for_update().first()

            if account:
                account.order = P2POrderBuyToken.objects.get(id=order_id)
                account.save(update_fields=['order_id'])
                return account

    # @classmethod
    # def get_free(cls):
    #     """ Возвращает аккаунт, на котором нет активных P2P сделок"""
    #     accounts = BybitAccount.objects.all()
    #     for account in accounts:
    #         if not P2POrderBuyToken.objects.filter(dt_received=None).exclude(
    #                 state__in=[P2POrderBuyToken.STATE_WRONG_PRICE, P2POrderBuyToken.STATE_TIMEOUT]).exists():
    #             return account
    #     else:
    #         return None  # Нет свободных аккаунтов

    @classmethod
    def get_random_account(cls):
        return random.choice(BybitAccount.objects.filter(is_active=True).all())

    def set_banned(self):
        self.is_active = False
        self.is_active_commentary = 'Banned for frod at ' + datetime.datetime.now().strftime(
            '%d.%m.%Y %H:%M')
        self.save()


class RiskEmail(models.Model):
    """Парсинг верификационных писем с email"""
    account = models.ForeignKey(BybitAccount, on_delete=models.CASCADE)  # ссылка на аккаунт с которого пришло письмо
    code = models.CharField(max_length=100)  # Код подтверждения
    amount = models.FloatField(max_length=100, blank=True, null=True, default=None)  # Сумма транзакции
    address = models.CharField(max_length=100, blank=True, null=True,
                               default=None)  # Адрес на который переводится крипта
    dt = models.DateTimeField()  # Время получения письма
    used = models.BooleanField(default=False)  # Использовали ли код

    def __str__(self):
        return '[' + self.dt.strftime('%d.%m.%Y %H:%M:%S') + '] => ' + str(self.amount)


class P2PItem(models.Model):
    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'
    ITEM_SIDE = (
        (SIDE_BUY, 'Покупка'),
        (SIDE_SELL, 'Продажа'),
    )

    item_id = models.CharField(max_length=50, unique=True)  # Айди лота
    user_id = models.IntegerField()  # Айди продавца
    price = models.FloatField()  # Цена токена
    quantity = models.FloatField()  # Доступно
    min_amount = models.FloatField()  # Минимум фиата
    max_amount = models.FloatField()  # Максимум фиата
    dt_updated = models.DateTimeField(default=datetime.datetime.now)  # Время выгрузки данных
    side = models.CharField(max_length=10, choices=ITEM_SIDE)
    payment_methods = models.JSONField(default=list)  # Список айди методов  FIXME
    remark = models.TextField(blank=True, null=True)  # Ремарка к лоту

    currency = models.CharField(max_length=50, default='RUB')
    token = models.CharField(max_length=50, default='USDT')
    is_active = models.BooleanField(default=True)  # Активен ли сейчас продавец

    def __repr__(self):
        return '{P2P: ' + str(self.id) + ' ' + str(self.price) + '}'

    def __str__(self):
        return '[' + self.side + '] ' + str(self.item_id)

    def get_payment_methods(self):
        return list(BybitCurrency.objects.filter(payment_id__isnull=False).values_list('payment_id', flat=True))

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


def default_session_token():
    return secrets.token_urlsafe(64)[:64]


class Partner(models.Model):
    name = models.CharField(max_length=50, default='Имя')  # Название выпустившего виджет
    balance = models.FloatField(default=0)  # Баланс комиссии
    platform_commission = models.FloatField(default=0.02)  # Комиссия платформы
    code = models.CharField(max_length=64, default=default_session_token)


def default_widget_hash():
    return secrets.token_urlsafe(64)[:64]


class Widget(models.Model):
    DEFAULT_PALETTE = {'accentColor': None, 'secondaryAccentColor': None, 'textColor': None,
                       'secondaryTextColor': None, 'bodyColor': None, 'blockColor': None, 'contrastColor': None,
                       'buttonHoverColor': None, 'buttonDisabledColor': None, 'uiKitBackgroundColor': None,
                       'uiKitBorderColor': None}

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    hash = models.CharField(max_length=64, default=default_widget_hash, unique=True)

    withdrawing_token = models.CharField(max_length=50, default=None, blank=True, null=True)
    withdrawing_chain = models.CharField(max_length=50, default=None, blank=True, null=True)
    withdrawing_address = models.CharField(max_length=500, default=None, blank=True,
                                           null=True)  # TODO в currency добавить

    partner_commission = models.FloatField(default=0.01)  # Комиссия партнера
    platform_commission = models.FloatField(default=0.02)  # Комиссия платформы

    email = models.CharField(max_length=50, default=None, blank=True, null=True)
    full_name = models.CharField(max_length=50, default=None, blank=True, null=True)
    color_palette = models.JSONField(default=DEFAULT_PALETTE, blank=True, null=True)
    payment_methods = models.ManyToManyField(BybitCurrency, default=None, verbose_name='Способы оплаты',
                                             related_name="widget_payment")
    # private
    redirect_url = models.TextField(validators=[URLValidator()], default=None, blank=True, null=True)


def default_order_hash():
    return secrets.token_urlsafe(128)[:128]


class P2POrderBuyToken(models.Model):
    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'
    ITEM_SIDE = (
        (SIDE_BUY, 'Покупка'),  # Покупаем крипту за фиат
        (SIDE_SELL, 'Продажа'),  # Покупаем фиат за крипту
    )

    STATE_INITIATED = 'INITIATED'
    STATE_WRONG_PRICE = 'WRONG'
    STATE_CREATED = 'CREATED'
    STATE_TRANSFERRED = 'TRANSFERRED'  # Переведено клиентом
    STATE_PAID = 'PAID'  # Ждет подтверждения продавца
    STATE_RECEIVED = 'RECEIVED'  # Токен получен
    STATE_TRADING = 'TRADING'
    STATE_TRADED = 'TRADED'
    STATE_WITHDRAWING = 'WITHDRAWING'  # Токен получен
    STATE_WAITING_VERIFICATION = 'VERIFICATION'  # Ожидание верификации по почте
    STATE_WITHDRAWN = 'WITHDRAWN'  # Токен выведен на кошелек

    STATE_TIMEOUT = 'TIMEOUT'  # Отменен по времени
    STATE_ERROR = 'ERROR'  # Ошибка вывода после получения средств клиента
    STATE_TRADE_WRONG_PRICE = 'ERROR'  # На бирже значимо изменилась цена обмена
    STATE_CANCELLED = 'CANC'  # Отменен пользователем
    STATE_ACCOUNT_BANNED = 'ACC_BANNED'
    STATE_P2P_APPEAL = 'P2P_APPEAL'

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
        (STATE_CANCELLED, 'Отменен пользователем'),

        (STATE_ACCOUNT_BANNED, 'Заблокирован аккаунт'),  # state только системный
        (STATE_P2P_APPEAL, 'Создана апелляция')
    )

    ANCHOR_CURRENCY = 'currency'
    ANCHOR_TOKEN = 'token'
    # TODO весь нейминг к одному виду: fiat currency crypro token
    # TODO anchor - Поменять на side 1 / 0 Первая валюта или вторая

    ANCHORS = (
        (ANCHOR_CURRENCY, 'Фиат'),
        (ANCHOR_TOKEN, 'Крипта')
    )

    hash = models.CharField(max_length=128, default=default_order_hash, unique=True)  # TODO NEW

    account = models.ForeignKey(BybitAccount, on_delete=models.CASCADE, related_name='order')
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE, blank=True, null=True)

    name = models.CharField(max_length=100, default='')
    card_number = models.CharField(max_length=100, default='')
    email = models.CharField(max_length=100, default='')

    item = models.ForeignKey(P2PItem, on_delete=models.CASCADE)
    payment_method = models.ForeignKey(BybitCurrency, on_delete=models.CASCADE, blank=True, null=True)

    # currency = models.CharField(max_length=10) FIXME
    p2p_token = models.CharField(max_length=30, default='USDT')
    p2p_price = models.FloatField()

    # Информация для вывода средств
    withdraw_token_rate = models.FloatField(default=1, null=True)
    withdraw_token = models.CharField(max_length=30, default='USDT')
    withdraw_chain = models.CharField(max_length=30, default='MANTLE')
    withdraw_address = models.CharField(max_length=100)

    amount = models.FloatField()  # Сколько валюты человек отправляет
    withdraw_quantity = models.FloatField(null=True)  # Сколько крипты выводим, null когда создается
    partner_commission = models.FloatField()  # Комиссия создателя трейда
    platform_commission = models.FloatField()  # Комиссия платформы
    chain_commission = models.FloatField()  # Комиссия блокчейна за перевод
    trading_commission = models.FloatField()  # Комиссия биржи за покупку

    # INITIATED
    dt_initiated = models.DateTimeField(default=datetime.datetime.now)

    # CREATED
    dt_created = models.DateTimeField(default=None, blank=True, null=True)
    order_id = models.CharField(max_length=30, blank=True, null=True)
    order_status = models.IntegerField(default=10, blank=True, null=True)
    terms = models.JSONField(default=dict, blank=True, null=True)
    # payment_id = models.CharField(max_length=50, blank=True, null=True) # FIXME

    # TRANSFERRED
    dt_transferred = models.DateTimeField(default=None, blank=True, null=True)

    # PAID
    dt_paid = models.DateTimeField(default=None, blank=True, null=True)

    # RECEIVED
    dt_received = models.DateTimeField(default=None, blank=True, null=True)
    risk_token = models.CharField(max_length=50, blank=True, null=True)

    # TRADING
    dt_trading = models.DateTimeField(default=None, blank=True, null=True)
    market_order_id = models.CharField(max_length=50, blank=True, null=True)

    # VERIFICATION
    dt_verification = models.DateTimeField(default=None, blank=True, null=True)

    # WITHDRAWN
    dt_withdrawn = models.DateTimeField(default=None, blank=True, null=True)

    state = models.CharField(max_length=20, choices=STATES, default=STATE_INITIATED)

    # CHECK NEW
    is_executing = models.BooleanField(default=False)
    anchor = models.CharField(max_length=20, default=ANCHOR_CURRENCY, choices=ANCHORS)
    is_stopped = models.BooleanField(default=False)  # Долгое выполнение / Возникла ошибка
    error_status = models.TextField(blank=True, null=True)

    @property
    def p2p_quantity(self):  # Сколько нужно купить на п2п
        digits = TOKENS_DIGITS[self.p2p_token]
        return float((('{:.' + str(digits) + 'f}').format(self.amount / self.p2p_price)))

    @property
    def p2p_available_balance(self):  # Сколько остается после комиссий - переводим на биржу
        digits = TOKENS_DIGITS[self.p2p_token]  # Todo тут нужно поработать с точностью после запятой
        return float(('{:.' + str(digits) + 'f}').format(
            self.p2p_quantity * (1 - self.platform_commission - self.partner_commission)))

    @property
    def trading_quantity(self):  # Нужно купить на бирже
        digits = TOKENS_DIGITS[self.withdraw_token]
        return float(
            (('{:.' + str(digits) + 'f}').format(self.withdraw_from_trading_account / (1 - self.trading_commission))))

    @property
    def withdraw_from_trading_account(self):  # Сколько нужно перевести на Funding аккаунт
        digits = TOKENS_DIGITS[self.withdraw_token]
        return float((('{:.' + str(digits) + 'f}').format((self.withdraw_quantity + self.chain_commission))))

    """
    @property
    def withdraw_quantity(self):
        return calculate_withdraw_amount(self.withdraw_token, self.withdraw_chain, self.amount, self.p2p_price, self.withdraw_price)
    """

    def risk_get_ga_code(self):
        return self.account.risk_get_ga_code()

    def risk_get_email_code(self):
        return self.account.risk_get_email_code(self.withdraw_address, self.withdraw_quantity)

    def create_order(self):
        from CORE.service.bybit.parser import BybitSession  # FIXME
        from CORE.service.tools.tools import calculate_withdraw_quantity

        if self.account is None:  # FIXME Можно убрать
            with transaction.atomic():
                query = BybitAccount.objects.only('id').filter(is_active=True, active_order__isnull=True)
                count = query.count()
                if count == 0:
                    raise Exception("No available account")
                random_index = random.randint(0, count - 1)

                account_query = query.select_for_update(of=("self",))[random_index:random_index + 1].all()

                if not account_query:
                    raise Exception("No available account")

                account = account_query[0]

                account.active_order = self
                self.account = account
                self.save()
                account.save()

        bybit_session = BybitSession(self.account)
        bybit_api = self.account.get_api()

        if self.withdraw_token not in P2P_TOKENS:  # Если нужно трейдить токен, покупаем в USDT
            self.withdraw_token_rate = bybit_api.get_trading_rate(self.withdraw_token, 'USDT')
            self.p2p_token = 'USDT'
        else:  # Если нет - покупаем ту же валюту
            self.withdraw_token_rate = 1
            self.p2p_token = self.withdraw_token

        price = bybit_session.get_item_price(self.item.item_id)  # Хэш от стоимости

        self.withdraw_quantity = calculate_withdraw_quantity(self.withdraw_token, self.withdraw_chain,
                                                             self.amount, price['price'],
                                                             self.withdraw_token_rate,
                                                             self.platform_commission,
                                                             self.partner_commission,
                                                             self.trading_commission,
                                                             self.chain_commission)

        if price['price'] != self.p2p_price:  # Не совпала цена
            self.state = P2POrderBuyToken.STATE_WRONG_PRICE
            self.save()  # withdraw_quantity сохраняется для передачи нового количества. Пользователь может согласиться или нет
            return

        self.withdraw_quantity = calculate_withdraw_quantity(self.withdraw_token, self.withdraw_chain,
                                                             self.amount, self.p2p_price,
                                                             self.withdraw_token_rate,
                                                             self.platform_commission,
                                                             self.partner_commission,
                                                             self.trading_commission,
                                                             self.chain_commission)
        self.save()

        # todo {'ret_code': 912100027, 'ret_msg': 'The ad status of your P2P order has been changed. Please try another ad.', 'result': None, 'ext_code': '', 'ext_info': {}, 'time_now': '1713650504.469008'}
        order_id = bybit_session.create_order_buy(self.item.item_id, self.p2p_quantity, self.amount,
                                                  price['curPrice'],
                                                  token_id=self.p2p_token,
                                                  currency_id=self.payment_method.token)
        if order_id is None:  # Забанен за отмену заказов
            self.account.set_banned()
            self.account = None
            self.save()
            return

        self.dt_created = datetime.datetime.now()
        self.order_id = order_id
        self.save()


class P2POrderMessage(models.Model):
    order = models.ForeignKey(P2POrderBuyToken, on_delete=models.CASCADE)

    TYPE_STR = 'str'
    TYPE_PDF = 'pdf'
    TYPE_VIDEO = 'video'
    TYPE_PIC = 'pic'

    message_id = models.CharField(max_length=50)
    account_id = models.CharField(max_length=50, blank=True, null=True)
    text = models.TextField(default='', blank=True, null=True)
    dt = models.DateTimeField(blank=True, null=True, default=datetime.datetime.now)
    uuid = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    nick_name = models.CharField(max_length=50, blank=True, null=True)
    type = models.CharField(max_length=50, default=1)  # 1 - переписка, иначе служебное

    file = models.FileField(upload_to='sent', blank=True, null=True)  # TODO Папка sent закрыта для доступа из вне

    # content_type = models.CharField(default=TYPE_STR, choices=CONTENT_TYPE, max_length=50)

    @classmethod
    def from_json(cls, order_id, data):
        from CORE.service.bybit.parser import BybitSession  # FIXME

        if P2POrderMessage.objects.filter(message_id=data['id']).exists():
            return

        if data['contentType'] == cls.TYPE_STR:
            if P2POrderMessage.objects.filter(uuid=data['msgUuid']).exists():
                return
        # elif data['contentType'] in [cls.TYPE_PIC, cls.TYPE_PDF, cls.TYPE_VIDEO]:
        #     file_name = f"sent/{data['message'].rsplit('/', 1)[-1]}"
        #     if P2POrderMessage.objects.filter(file=file_name).exists():
        #         return

        message = P2POrderMessage(order_id=order_id)
        message.message_id = data['id']
        message.account_id = data['accountId']
        message.dt = datetime.datetime.utcfromtimestamp(int(data.get('createDate', 0)) / 1000)
        message.uuid = data['msgUuid']
        message.user_id = data['userId']
        message.nick_name = data['nickName']
        message.type = data['msgType']
        if data['contentType'] == cls.TYPE_STR:
            message.text = data['message']
        elif data['contentType'] in [cls.TYPE_PIC, cls.TYPE_PDF, cls.TYPE_VIDEO]:
            filename, content = BybitSession.download_p2p_file_attachment(file_path=data['message'])
            message.file = ContentFile(content, name=filename)
        else:  # NON IMPLEMENTED
            message.text = data['message']

        return message

    def get_file_base64(self):
        if self.file:
            return file_as_base64(self.file.path)

    def to_json(self):
        nickname = self.nick_name,
        if self.type == '1':
            if self.user_id == str(self.order.account.user_id):
                side = 'USER'
                nickname = self.order.name
            else:
                side = 'TRADER'
        else:
            side = 'SUPPORT'

        res = {
            'nick_name': nickname,
            'text': self.text,
            'dt': self.dt.strftime('%d.%m.%Y %H:%M:%S') if self.dt else None,
            'uuid': self.uuid,
            'file': self.get_file_base64(),
            'side': side,
        }
        print(res)
        return res
