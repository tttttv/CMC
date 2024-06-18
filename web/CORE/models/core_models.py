import datetime
import random
import secrets
import time
from typing import Sequence, Optional, List

from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.db import models, transaction
from django.db.models import UniqueConstraint

from CORE.service.bybit.api import BybitAPI
from CORE.service.bybit.code_2fa import get_ga_token
from CORE.service.bybit.models import BybitPaymentTerm
from CORE.service.bybit.parser import BybitSession, InsufficientError, AuthenticationError, AdStatusChanged, InsufficientErrorSell
from CORE.service.tools.formats import file_as_base64, format_float_up, format_float
from CORE.exceptions import DoesNotExist, AmountException


class Config(models.Model):
    tokens_digits = models.JSONField(default=dict)
    timeouts = models.JSONField(default=dict)
    token_amounts = models.JSONField(default=dict)


class BybitP2PBlackList(models.Model):
    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'
    ITEM_SIDE = (
        (SIDE_SELL, 'Покупка USDT'),
        (SIDE_BUY, 'Продажа USDT'),
    )

    item_id = models.CharField(primary_key=True, max_length=50)
    user_id = models.IntegerField()

    is_active = models.BooleanField(default=True)
    update_dt = models.DateTimeField(default=datetime.datetime.now)

    side = models.CharField(max_length=10, choices=ITEM_SIDE)

    @classmethod
    def add_seller(cls, item_id, user_id, side=SIDE_SELL):
        BybitP2PBlackList.objects.create(item_id=item_id, user_id=user_id, side=side)
        P2PItem.objects.filter(item_id=item_id).update(is_active=False)

    @classmethod
    def get_blacklist(cls, side=SIDE_SELL) -> List[int]:
        return BybitP2PBlackList.objects.filter(is_active=True, side=side).values_list('user_id', flat=True)


def expire_day_default():
    return datetime.datetime.now() + datetime.timedelta(days=1)


# class InsufficientErrorSellers(models.Model):
#     item_id = models.IntegerField(primary_key=True)
#     user_id = models.IntegerField()
#
#     is_active = models.BooleanField(default=True)
#     expire_dt = models.DateTimeField(default=expire_day_default)


class BybitIncomingPayment(models.Model):
    item_id = models.IntegerField(unique=True)
    account = models.ForeignKey('BybitAccount', on_delete=models.CASCADE)

    tx_id = models.CharField(max_length=120)

    address = models.CharField(max_length=120)  # TODO Currency
    chain = models.CharField(max_length=120)
    token = models.CharField(max_length=120)

    created_time = models.DateTimeField()

    status = models.CharField(max_length=120)
    congested_status = models.IntegerField(default=0)

    amount = models.FloatField()

    confirmations = models.IntegerField(default=0)
    blockConfirmNumber = models.IntegerField(default=0)
    safeConfirmNumber = models.IntegerField(default=0)

    transaction_url = models.URLField(default=None, null=True, blank=True)
    address_transaction_url = models.URLField(default=None, null=True, blank=True)

    fee = models.CharField()

    @classmethod
    def from_json(cls, incoming_data, account):
        data = {
            'item_id': int(incoming_data['id']),
            'created_time': datetime.datetime.fromtimestamp(int(incoming_data['createTime'])),
            'tx_id': incoming_data['txId'],
            'address': incoming_data['address'],
            'chain': incoming_data['chain'],
            'token': incoming_data['coin'],
            'amount': float(incoming_data['amount']),

            'status': incoming_data['status'],

            'confirmations': int(incoming_data['confirmations']),
            'blockConfirmNumber': int(incoming_data['blockConfirmNumber']),
            'safeConfirmNumber': int(incoming_data['safeConfirmNumber']),
            'congested_status': int(incoming_data['congestedStatus']),

            'transaction_url': incoming_data.get('txidTransactionUrl', None),
            'address_transaction_url': incoming_data.get('addressTransactionUrl', None),
            'fee': incoming_data['fee']
        }
        return BybitIncomingPayment(**data, account=account)

    @property
    def confirmed(self):
        return self.confirmations > self.blockConfirmNumber

    def to_json(self):
        return {'id': self.id, 'created_time': self.created_time, 'amount': self.amount, 'confirmed': self.confirmed,
                'address': self.address, 'chain': self.chain, 'token': self.token, 'transaction_url': self.transaction_url,
                'address_transaction_url': self.address_transaction_url}


class AbstractCurrency(models.Model):
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

    payment_id = models.IntegerField(default=None, blank=True, null=True, verbose_name="ID Банка")  # 337 339
    token = models.CharField(max_length=10, choices=CURRENCY, verbose_name='Токен валюты')  # RUB / USDT / NEAR
    exchange_from = models.ManyToManyField("self", blank=True, symmetrical=False, related_name='exchange_to')

    min_amount = models.FloatField(default=500.0)
    max_amount = models.FloatField(default=2000000)

    class Meta:
        abstract = True

    def __str__(self):
        return self.name

    def logo(self):
        if self.type == self.TYPE_FIAT:
            return f'/static/CORE/banks/{self.id}.png'
        else:
            return f'/static/CORE/tokens/{self.token}.png'

    @staticmethod
    def cache_exchange(available_payment_methods: Sequence[int] = None, side: str = 'SELL'):  # ЛЕВАЯ ЧАСТЬ
        fiats = {}
        tokens = []
        if side == 'SELL':
            currencies = BybitCurrency.objects.filter(exchange_to__isnull=False).all().distinct()
            exchange_name = 'exchange_to'
        else:
            currencies = BybitCurrency.objects.filter(exchange_from__isnull=False).all().distinct()
            exchange_name = 'exchange_from'

        for currency in currencies:
            if available_payment_methods and currency.id not in available_payment_methods:
                continue

            if side == 'SELL':
                exchange = list(currency.exchange_to.values_list('id', flat=True))
            else:
                exchange = list(currency.exchange_from.values_list('id', flat=True))

            if currency.type == BybitCurrency.TYPE_FIAT:
                payment_method = {'id': currency.id, 'name': currency.name, 'logo': currency.logo(),
                                  exchange_name: exchange}
                if currency.token not in fiats:
                    fiats[currency.token] = {'id': currency.token,  # 'type': currency.type,
                                             'name': currency.get_token_display(),
                                             'payment_methods': [payment_method],
                                             'min_amount': currency.min_amount,
                                             'max_amount': currency.max_amount}
                else:
                    fiats[currency.token]['payment_methods'].append(payment_method)

            elif currency.type == BybitCurrency.TYPE_CRYPTO:
                token_data = {'id': currency.id,  # 'id': currency.token,  'type': currency.type,
                              'name': currency.get_token_display(), 'chains': currency.chains,
                              'logo': currency.logo(),
                              exchange_name: exchange}
                tokens.append(token_data)

        return {'fiat': list(fiats.values()), 'crypto': tokens}

    def validate_payment_amount(self, amount, chain) -> bool:
        min_amount, max_amount = self.payment_min_max(chain)
        return min_amount <= amount <= max_amount

    def payment_min_max(self, chain):
        if self.is_crypto:
            chain_info = self.get_chain(chain)
            return chain_info['min_payment'], chain_info['max_payment']
        else:
            return self.min_amount, self.max_amount

    def withdraw_min_max(self, chain):
        if self.is_crypto:
            chain_info = self.get_chain(chain)
            return chain_info['min_withdraw'], chain_info['max_withdraw']
        else:
            return self.min_amount, self.max_amount

    def validate_withdraw_amount(self, amount, chain) -> bool:
        min_amount, max_amount = self.withdraw_min_max(chain)
        return min_amount <= amount <= max_amount

    def validate_exchange(self, other):
        return self.exchange_from.filter(id=other.id).exists()

    def payment_methods(self):
        return list(self.exchange_from.values_list('payment_id', flat=True))

    def validate_chain(self, chain_id: str) -> bool:
        for chain in self.chains:
            if chain['id'] == chain_id:
                return True
        return False

    def get_chain(self, chain: str) -> Optional[dict]:
        for c in self.chains:
            if c['id'] == chain:
                return c
        return None

    @property
    def is_crypto(self):
        return self.type == BybitCurrency.TYPE_CRYPTO

    @property
    def is_fiat(self):
        return self.type == BybitCurrency.TYPE_FIAT

    @property
    def is_usdt(self):
        return self.token == BybitCurrency.CURRENCY_USDT


class BybitCurrency(AbstractCurrency):

    def __str__(self):
        return self.name

    def to_json(self) -> dict:  # TODO Serialize
        return {'id': self.id, 'type': self.type,
                'name': self.name if self.is_fiat else self.get_token_display(),
                'token': self.token,  # FIXME DEL
                'chains': self.chains,
                'logo': self.logo()}

    @staticmethod
    def get_by_id(method_id: int):
        print('method_id:', method_id)
        return BybitCurrency.objects.get(id=method_id)

    @staticmethod
    def get_by_token(token: str):
        return BybitCurrency.objects.get(token=token)

    @staticmethod
    def all_payment_methods():
        return BybitCurrency.objects.filter(payment_id__isnull=False, exchange_to__isnull=False).distinct()


class Currency(AbstractCurrency):
    chain = models.CharField(default=None, blank=True, null=True)
    address = models.CharField(default=None, blank=True, null=True)  # Адрес/номер карты для ввода или вывода
    currency = models.ForeignKey(BybitCurrency, on_delete=models.CASCADE)

    def get_chain_commission(self):
        return float(self.get_chain(self.chain)['withdraw_commission'])

    def validate_payment_amount(self, amount, *_, **__) -> bool:
        return super().validate_payment_amount(amount, self.chain)

    def validate_withdraw_amount(self, amount, *_, **__) -> bool:
        return super().validate_withdraw_amount(amount, self.chain)

    def payment_min_max(self, *_):
        return super().payment_min_max(self.chain)

    def withdraw_min_max(self, *_):
        return super().withdraw_min_max(self.chain)

    def __str__(self):
        return f"Кошелек {self.name} - {self.address}"

    def to_json(self) -> dict:
        return {'id': self.id,
                'currency_id': self.currency_id,
                'type': self.type,
                'name': self.name if self.is_fiat else self.get_token_display(),
                'token': self.token,  # FIXME DEL
                'chain': self.chain, 'address': self.address,
                'logo': self.logo()}

    @staticmethod
    def get_by_id(method_id: int):
        print('method_id:', method_id)
        return BybitCurrency.objects.get(id=method_id)

    @staticmethod
    def get_by_token(token: str):
        return BybitCurrency.objects.get(token=token)

    def __hash__(self):
        return super().__hash__()

    def __eq__(self, other):
        if isinstance(other, Currency):
            return (self.address == other.address and self.chain == other.chain
                    and self.token == other.token and self.payment_id == other.payment_id and self.type == other.type)
        return False

    def __ne__(self, other):
        return not self.__eq__(other)


class P2PItem(models.Model):
    SIDE_BUY = 'BUY'
    SIDE_SELL = 'SELL'
    ITEM_SIDE = (
        (SIDE_SELL, 'Покупка USDT'),
        (SIDE_BUY, 'Продажа USDT'),
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

    restrictions = models.JSONField(default=dict)
    cur_price_hash = models.CharField(default=None, null=True, blank=True, max_length=50)

    def __repr__(self):
        return '{P2P: ' + str(self.id) + ' ' + str(self.price) + '}'

    def __str__(self):
        return '[' + self.side + '] ' + str(self.item_id)

    def to_json(self):
        return {'price': self.price, 'item_id': self.item_id, 'user_id': self.user_id, 'dt_updated': self.dt_updated}

    @staticmethod
    def get_payment_methods():
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
        item.restrictions = data.get('tradingPreferenceSet', None)
        item.dt_updated = datetime.datetime.now()
        return item


class AccountInsufficientItems(models.Model):
    is_active = models.BooleanField(default=True)

    account = models.ForeignKey('BybitAccount', on_delete=models.CASCADE)
    item = models.ForeignKey(P2PItem, on_delete=models.CASCADE)

    expire_dt = models.DateTimeField(default=expire_day_default)

    class Meta:
        constraints = [
            UniqueConstraint(fields=['account', 'item'], name='account_item')
        ]


class BybitAccount(models.Model):
    is_active = models.BooleanField(default=True)
    user_id = models.IntegerField(unique=True)  # Айди пользователя
    cookies = models.JSONField(default=list)  # Куки пользователя
    cookies_updated = models.DateTimeField(default=datetime.datetime.now)  # Время установки кук
    cookies_valid = models.BooleanField(default=True)  # Не возникало ошибок с куками
    ga_secret = models.CharField(max_length=30, default='GHO5UKQ3IDTCRIXY')  # Секрет гугл 2фа

    imap_username = models.CharField(default=None, max_length=50, blank=True, null=True)  # Почта привязанная к аккаунту
    imap_server = models.CharField(default=None, max_length=50, blank=True, null=True)  # Сервер почты
    imap_password = models.CharField(default=None, max_length=30, blank=True, null=True)  # Пароль от почты

    PROXY_TYPE_NONE = None
    PROXY_TYPE_SOCKS4 = 'socks4'
    PROXY_TYPE_SOCKS5 = 'socks5'
    PROXY_TYPE_HTTP = 'http'

    PROXY_TYPES = (
        (PROXY_TYPE_NONE, 'без прокси'),
        (PROXY_TYPE_SOCKS4, 'socks4'),
        (PROXY_TYPE_SOCKS5, 'socks5'),
        (PROXY_TYPE_HTTP, 'http'),
    )

    proxy_host = models.CharField(max_length=50, default=None, blank=True, null=True)
    proxy_port = models.CharField(max_length=50, default=None, blank=True, null=True)
    proxy_type = models.CharField(max_length=50, default=PROXY_TYPE_NONE, choices=PROXY_TYPES, blank=True, null=True)

    proxy_username = models.CharField(max_length=50, default=None, blank=True, null=True)
    proxy_password = models.CharField(max_length=50, default=None, blank=True, null=True)

    api_key = models.CharField(max_length=50, blank=True, null=True)
    api_secret = models.CharField(max_length=50, blank=True, null=True)

    is_active_commentary = models.CharField(max_length=200, default='')

    active_order = models.OneToOneField('OrderBuyToken', on_delete=models.SET_NULL, null=True, blank=True)

    insufficient = models.ManyToManyField(P2PItem, default=None, null=True, blank=True, through=AccountInsufficientItems, related_name='accounts')

    @property
    def use_proxy(self) -> bool:
        return self.proxy_type != self.PROXY_TYPE_NONE

    @property
    def proxy_auth(self) -> Optional[tuple]:
        if not self.use_proxy:
            return None
        return self.proxy_username, self.proxy_password

    @property
    def proxy_settings(self) -> Optional[dict]:
        if not self.use_proxy:
            return None

        if self.proxy_username and self.proxy_password:
            auth = f'{self.proxy_username}:{self.proxy_password}@'
        else:
            auth = ''

        return {
            'http': f'{self.proxy_type}://{auth}{self.proxy_host}:{self.proxy_port}',
            'https': f'{self.proxy_type}://{auth}{self.proxy_host}:{self.proxy_port}'
        }

    def add_insufficient(self, item: P2PItem):
        AccountInsufficientItems.objects.update_or_create(
            account=self,
            item=item,
            defaults={'is_active': True, 'expire_dt': expire_day_default()}
        )

    def risk_get_ga_code(self):
        return get_ga_token(self.ga_secret)

    @staticmethod
    def risk_get_email_code(address, amount):
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
        return BybitAPI(api_key=self.api_key, api_secret=self.api_secret, proxy_settings=self.proxy_settings)

    @classmethod
    def assign_order(cls, order_id):  # FIXME сделать свой with
        with transaction.atomic():
            query = BybitAccount.objects.filter(active_order__isnull=True)
            count = query.count()
            if count == 0:
                return None

            random_index = random.randint(0, count - 1)
            account = query.all()[random_index:random_index + 1].select_for_update().first()

            if account:
                account.active_order = OrderBuyToken.objects.get(id=order_id)
                account.save(update_fields=['active_order'])
                return account

    @classmethod
    def order_release_states(cls) -> tuple:
        return (OrderBuyToken.STATE_TIMEOUT, OrderBuyToken.STATE_ERROR, OrderBuyToken.STATE_CANCELLED,
                OrderBuyToken.STATE_WAITING_VERIFICATION, OrderBuyToken.STATE_WITHDRAWN, OrderBuyToken.STATE_WITHDRAWING)

    @classmethod
    def order_end_states(cls) -> tuple:
        return (OrderBuyToken.STATE_TIMEOUT, OrderBuyToken.STATE_ERROR, OrderBuyToken.STATE_CANCELLED,
                OrderBuyToken.STATE_WITHDRAWN, OrderBuyToken.STATE_ERROR_TRADE_VOLATILE)

    @classmethod
    def release_order(cls, account_id):
        with transaction.atomic():  # ***
            account = BybitAccount.objects.select_related().select_for_update().get(id=account_id)
            if account.active_order is not None:
                if account.active_order.state in cls.order_release_states():
                    account.active_order = None
                    account.save(update_fields=['active_order'])

    @classmethod
    def get_random_account(cls):
        return random.choice(BybitAccount.objects.filter(is_active=True).all())

    def set_banned(self):  # FIXME UNUSED
        self.is_active = False
        self.is_active_commentary = 'Banned for frod at ' + datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
        self.save()

    def set_cookie_die(self):
        self.is_active = False
        self.is_active_commentary = 'Cookie die at' + datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
        self.save()

    def set_proxy_dead(self):
        self.is_active_commentary = 'ProxyDead at ' + datetime.datetime.now().strftime('%d.%m.%Y %H:%M')
        self.save()


def default_session_token():
    return secrets.token_urlsafe(64)[:64]


class Partner(models.Model):
    name = models.CharField(max_length=50, default='Имя')  # Название выпустившего виджет
    balance = models.FloatField(default=0)  # Баланс комиссии
    platform_commission = models.FloatField(default=0.02)  # Комиссия платформы
    code = models.CharField(max_length=64, default=default_session_token)


class InternalCryptoAddress(models.Model):
    account = models.ForeignKey('BybitAccount', on_delete=models.CASCADE, related_name='internal_crypto_address')
    user_id = models.CharField(max_length=50)
    address = models.CharField(max_length=180)
    chain_name = models.CharField(max_length=20)  # token
    chain = models.CharField(max_length=20)
    qrcode = models.TextField()
    need_confirm = models.BooleanField(default=True)

    @classmethod
    def from_json(cls, data: dict, account: BybitAccount):
        return InternalCryptoAddress(**{'user_id': data['userId'], 'address': data['address'], 'chain_name': data['chainName'],
                                        'chain': data['chain'], 'need_confirm': data['needConfirm'], 'qrcode': data['qrcode']}, account=account)

    def to_json(self) -> dict:
        return {'id': self.id, 'account_no': self.address, 'chain': self.chain, 'chain_name': self.chain_name, 'qrcode': self.qrcode}

    def __str__(self):
        return f"InternalAddress {self.id}, {self.chain}: {self.address}"


def default_widget_hash():
    return secrets.token_urlsafe(64)[:64]


class Widget(models.Model):
    DEFAULT_PALETTE = {'accentColor': None, 'secondaryAccentColor': None, 'textColor': None,
                       'secondaryTextColor': None, 'bodyColor': None, 'blockColor': None, 'contrastColor': None,
                       'buttonHoverColor': None, 'buttonDisabledColor': None, 'uiKitBackgroundColor': None,
                       'uiKitBorderColor': None}

    partner = models.ForeignKey(Partner, on_delete=models.CASCADE)
    hash = models.CharField(max_length=64, default=default_widget_hash, unique=True)

    withdrawing_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, related_name='widget_withdrawing_currency')

    partner_commission = models.FloatField(default=0.01)  # Комиссия партнера
    platform_commission = models.FloatField(default=0.02)  # Комиссия платформы

    email = models.CharField(max_length=50, default=None, blank=True, null=True)  # DEL
    name = models.CharField(max_length=50, default=None, blank=True, null=True)  # DEL

    color_palette = models.JSONField(default=DEFAULT_PALETTE, blank=True, null=True)

    payment_methods = models.ManyToManyField(BybitCurrency, default=None, verbose_name='Способы оплаты',
                                             related_name="widget", blank=True, null=True)
    # private
    redirect_url = models.TextField(validators=[URLValidator()], default=None, blank=True, null=True)

    def validate_withdraw(self, currency: Currency) -> bool:
        return self.withdrawing_currency == currency


def default_order_hash():
    return secrets.token_urlsafe(128)[:128]


class OrderBuyToken(models.Model):
    # STAGE 1
    STATE_INITIATED = 'INITIATED'  # *
    STATE_WRONG_PRICE = 'WRONG'
    STATE_CREATED = 'CREATED'  # *
    STATE_TRANSFERRED = 'TRANSFERRED'  # Переведено клиентом / Ожидаем подтверждения от bybit*

    STATE_PAYMENT_AMOUNT_NOT_ENOUGH = 'PAYMENT_AMOUNT_NOT_ENOUGH'  # Переведено не достаточно  ***

    STATE_PAID = 'PAID'  # Ждет подтверждения продавца *

    STATE_RECEIVING_CRYPTO = 'RECEIVING_CRYPTO'  # Ожидаем поступления крипты
    STATE_TRADING_CRYPTO = 'STATE_TRADING_CRYPTO'  # Покупка USDT на бирже за крипту
    STATE_TRADED_CRYPTO = 'STATE_TRADED_CRYPTO'  # Подтверждение обмена / Вывод на Funding
    STATE_CHECK_BALANCE = 'CHECK_BALANCE'  # Проверка поступления денег на Funding  *

    STATE_WAITING_TRANSACTION_PROCESSED = "WAIT_TRANSACTION"  # Ждем пока bybit проверит транзакцию с киптой

    # STAGE 2
    STATE_RECEIVED = 'RECEIVED'  # Токен получен
    STATE_TRADING = 'TRADING'
    STATE_TRADED = 'TRADED'
    STATE_WITHDRAWING = 'WITHDRAWING'  # Токен получен

    STATE_WAITING_VERIFICATION = 'VERIFICATION'  # Ожидание верификации по почте
    STATE_WITHDRAWN = 'WITHDRAWN'  # Токен выведен на кошелек

    STATE_WAITING_CONFIRMATION = 'WAITING_CONFIRMATION'  # Подтверждение получение средств
    STATE_BUY_CONFIRMED = 'BUY_CONFIRMED'  # Закрываем p2p заказ на продажу USDT
    STATE_BUY_NOT_CONFIRMED = 'BUY_NOT_CONFIRMED'  # Закрываем p2p заказ на продажу USDT

    STATE_TIMEOUT = 'TIMEOUT'  # Отменен по времени
    STATE_ERROR = 'ERROR'  # Ошибка вывода после получения средств клиента
    STATE_ERROR_TRADE_VOLATILE = 'TRADE_VOLATILE'
    STATE_TRADE_WRONG_PRICE = 'ERROR'  # На бирже значимо изменилась цена обмена
    STATE_CANCELLED = 'CANCELED'  # Отменен пользователем
    STATE_ACCOUNT_BANNED = 'ACC_BANNED'
    STATE_P2P_APPEAL = 'P2P_APPEAL'

    STATES = (
        (STATE_INITIATED, 'Инициализирован'),

        (STATE_WRONG_PRICE, 'Не совпадает цена'),
        (STATE_PAYMENT_AMOUNT_NOT_ENOUGH, 'Переведено не достаточно'),

        (STATE_CREATED, 'Сделка создана'),
        (STATE_TRANSFERRED, 'Средства переведены клиентом'),
        (STATE_PAID, 'Ждет продавца'),
        (STATE_RECEIVED, 'USDT Получены'),

        (STATE_TRADING, 'Обмен на бирже'),
        (STATE_TRADED, 'Обменено на бирже'),

        (STATE_WITHDRAWING, 'Вывод'),
        (STATE_WAITING_VERIFICATION, '2-ФА'),

        (STATE_WITHDRAWN, 'Средства выведены'),

        (STATE_TIMEOUT, 'Просрочен'),

        (STATE_ERROR, 'Ошибка'),
        (STATE_CANCELLED, 'Отменен пользователем'),

        (STATE_ACCOUNT_BANNED, 'Заблокирован аккаунт'),  # state только системный
        (STATE_P2P_APPEAL, 'Создана апелляция'),

        (STATE_WAITING_CONFIRMATION, 'Ожидание подтверждения получения'),
        (STATE_BUY_CONFIRMED, 'Пользователь подтвердил получение средств'),
        (STATE_BUY_NOT_CONFIRMED, 'НЕ ПОДТВЕРДИЛИ'),

        (STATE_RECEIVING_CRYPTO, 'Ожидаем поступления криптовалюты'),
        (STATE_TRADING_CRYPTO, 'Покупка на бирже USDT'),
        (STATE_TRADED_CRYPTO, 'Подтверждение покупки на бирже USDT'),
        (STATE_CHECK_BALANCE, 'Проверка баланса'),

        (STATE_ERROR_TRADE_VOLATILE, 'Цена на бирже выросла'),

        (STATE_WAITING_TRANSACTION_PROCESSED, 'Ожидание подтверждения транзакции')
    )

    ANCHOR_BUY = 'BUY'
    ANCHOR_SELL = 'SELL'

    ANCHORS = (
        (ANCHOR_BUY, 'Покупка'),
        (ANCHOR_SELL, 'Продажа')
    )

    STAGE_PROCESS_PAYMENT = 1
    STAGE_PROCESS_WITHDRAW = 2
    STAGES = (
        (STAGE_PROCESS_PAYMENT, 'STAGE 1'),
        (STAGE_PROCESS_WITHDRAW, 'STAGE 2')
    )
    hash = models.CharField(max_length=128, default=default_order_hash, unique=True)

    stage = models.IntegerField(default=STAGE_PROCESS_PAYMENT, choices=STAGES, verbose_name='Этап ордера')
    account = models.ForeignKey(BybitAccount, on_delete=models.CASCADE, related_name='order_set')
    widget = models.ForeignKey(Widget, on_delete=models.CASCADE, blank=True, null=True)

    payment_name = models.CharField(max_length=100, default='')
    withdraw_name = models.CharField(max_length=100, default='')

    email = models.CharField(max_length=100, default='')

    p2p_item_sell = models.ForeignKey(P2PItem, on_delete=models.CASCADE, blank=True, null=True,
                                      related_name='p2p_order_buy', verbose_name='Покупка USDT')  # <-- payment currency fiat

    p2p_item_buy = models.ForeignKey(P2PItem, on_delete=models.CASCADE, blank=True, null=True,
                                     related_name='p2p_order_sell', verbose_name='Продажа USDT')  # <-- withdraw currency fiat

    price_sell = models.FloatField(default=None, blank=True, null=True, verbose_name='Курс при вводе')  # Зафиксированная цена p2p_item
    price_buy = models.FloatField(default=None, blank=True, null=True, verbose_name='Курс при выводе')

    order_sell_id = models.CharField(max_length=30, blank=True, null=True)
    order_buy_id = models.CharField(max_length=30, blank=True, null=True)

    payment_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, blank=True, null=True,
                                         related_name='order_payment')
    withdraw_currency = models.ForeignKey(Currency, on_delete=models.CASCADE, blank=True, null=True,
                                          related_name='order_withdraw')
    internal_address = models.ForeignKey(InternalCryptoAddress, on_delete=models.CASCADE, blank=True, null=True)
    incoming_payment = models.OneToOneField(BybitIncomingPayment, on_delete=models.CASCADE, blank=True, null=True)

    payment_term = models.ForeignKey('PaymentTerm', on_delete=models.CASCADE, blank=True, null=True)

    # Информация для вывода средств

    payment_amount = models.FloatField()  # Сколько валюты человек отправляет
    withdraw_amount = models.FloatField(null=True)  # Сколько крипты выводим, null когда создается
    usdt_amount = models.FloatField(null=True)  # Промежуточное кол-во usdt

    partner_commission = models.FloatField()  # Комиссия создателя трейда
    platform_commission = models.FloatField()  # Комиссия платформы
    trading_commission = models.FloatField()  # Комиссия биржи за покупку

    # INITIATED
    dt_initiated = models.DateTimeField(default=datetime.datetime.now)

    # CREATED
    dt_created_sell = models.DateTimeField(default=None, blank=True, null=True)
    dt_created_buy = models.DateTimeField(default=None, blank=True, null=True)

    dt_confirmed_sell = models.DateTimeField(default=None, blank=True, null=True)
    dt_confirmed_buy = models.DateTimeField(default=None, blank=True, null=True)

    terms = models.JSONField(default=dict, blank=True, null=True)

    # TRANSFERRED
    dt_transferred = models.DateTimeField(default=None, blank=True, null=True)

    # PAID
    dt_paid_sell = models.DateTimeField(default=None, blank=True, null=True)
    dt_paid_buy = models.DateTimeField(default=None, blank=True, null=True)

    # RECEIVED
    dt_received_sell = models.DateTimeField(default=None, blank=True, null=True)
    dt_received_buy = models.DateTimeField(default=None, blank=True, null=True)

    risk_token = models.CharField(max_length=50, blank=True, null=True)

    # TRADING
    dt_trading_sell = models.DateTimeField(default=None, blank=True, null=True)
    dt_trading_buy = models.DateTimeField(default=None, blank=True, null=True)

    # VERIFICATION
    dt_verification = models.DateTimeField(default=None, blank=True, null=True)

    # WITHDRAWN
    dt_withdrawn = models.DateTimeField(default=None, blank=True, null=True)

    state = models.CharField(max_length=30, choices=STATES, default=STATE_INITIATED)

    # CHECK NEW
    is_executing = models.BooleanField(default=False)
    anchor = models.CharField(max_length=20, default=ANCHOR_SELL, choices=ANCHORS)
    is_stopped = models.BooleanField(default=False)  # Долгое выполнение / Возникла ошибка

    error_message = models.TextField(blank=True, null=True)
    messages_log = models.JSONField(default=list)

    def add_message(self, message, **kwarg):
        message = {'dt': datetime.datetime.now(), 'message': message, 'stage': self.stage, 'state': self.state}
        message.update(kwarg)
        self.messages_log.append(message)
        self.save()

    @property
    def name(self):
        if self.stage == self.STAGE_PROCESS_PAYMENT and self.payment_name:
            return self.payment_name
        elif self.stage == self.STAGE_PROCESS_WITHDRAW and self.withdraw_name:
            return self.withdraw_name
        return 'You'  # FIXME

    @property
    def withdraw_from_trading_account(self):  # Сколько нужно перевести на Funding аккаунт
        return format_float(self.withdraw_amount + self.withdraw_currency.get_chain_commission(), token=self.withdraw_currency.token)

    def risk_get_ga_code(self):
        return self.account.risk_get_ga_code()

    def risk_get_email_code(self):
        return self.account.risk_get_email_code(self.withdraw_currency.address, self.withdraw_amount)

    def add_account(self):
        with transaction.atomic():
            query = BybitAccount.objects.only('id').filter(is_active=True, active_order__isnull=True)
            count = query.count()
            if count == 0:
                self.state = OrderBuyToken.STATE_ERROR
                self.save()
                return False
            random_index = random.randint(0, count - 1)

            account_query = query.select_for_update(of=("self",))[random_index:random_index + 1].all()

            if not account_query:
                self.state = OrderBuyToken.STATE_ERROR
                self.save()
                return False

            account = account_query[0]

            account.active_order = self
            self.account = account
            self.save()
            account.save()
            return True

    def update_items_price(self, bybit_session: BybitSession):
        print('VERIF STAGE 1')
        try:
            if self.stage == self.STAGE_PROCESS_PAYMENT and self.p2p_item_sell:
                print('update p2p_item_sell')
                sell_price_data = bybit_session.get_item_price(self.p2p_item_sell.item_id)
                print('sell_price_data', sell_price_data)
                self.p2p_item_sell.price = sell_price_data['price']
                self.p2p_item_sell.cur_price_hash = sell_price_data['curPrice']
                self.p2p_item_sell.save()
        except InsufficientError:
            raise InsufficientErrorSell

        if self.p2p_item_buy:
            print('update p2p_item_buy')
            buy_price_data = bybit_session.get_item_price(self.p2p_item_buy.item_id)
            print('buy_price_data', buy_price_data)
            self.p2p_item_buy.price = buy_price_data['price']
            self.p2p_item_buy.cur_price_hash = buy_price_data['curPrice']
            self.p2p_item_buy.save()

    def get_items_price(self, find_new_items: bool = True):
        from CORE.service.tools.tools import Trade

        bybit_session = BybitSession(self.account)

        if not find_new_items:
            print('BEFORE')
            self.update_items_price(bybit_session)

        trade = Trade(self.payment_currency, self.withdraw_currency, self.payment_amount, self.withdraw_amount,
                      self.withdraw_currency.chain, self.payment_currency.chain,
                      self.trading_commission, self.partner_commission, self.platform_commission,
                      is_direct=self.anchor == OrderBuyToken.ANCHOR_SELL,
                      p2p_item_sell=None if find_new_items else self.p2p_item_sell,
                      p2p_item_buy=None if find_new_items else self.p2p_item_buy,
                      stage=self.stage,
                      usdt_amount=self.usdt_amount if self.stage == self.STAGE_PROCESS_WITHDRAW else None,
                      account_id=self.account_id if self.account else None)

        return trade.get_amount()

    def check_p2p_timeout(self, minutes, side=P2PItem.SIDE_SELL):
        delta = datetime.datetime.now() - datetime.timedelta(minutes=minutes)

        if side == P2PItem.SIDE_SELL:
            if self.dt_created_sell.replace(tzinfo=None) < delta:
                self.state = OrderBuyToken.STATE_TIMEOUT
                self.error_message = 'P2P Sell Timeout'
                self.save()
                return True
        elif side == P2PItem.SIDE_BUY:
            if self.dt_created_buy.replace(tzinfo=None) < delta:
                self.state = OrderBuyToken.STATE_TIMEOUT
                self.error_message = 'P2P Buy Timeout'
                self.save()
                return True

        return False

    def verify_order(self, bybit_session: Optional[BybitSession] = None, find_new_items: bool = False, max_counts: int = 8) -> bool:
        print('verify_order max_counts', find_new_items, max_counts)
        print('STAGE', self.stage)

        if not bybit_session:
            bybit_session = BybitSession(self.account)

        try:
            (payment_amount, withdraw_amount, usdt_amount, p2p_item_sell, p2p_item_buy,
             price_sell, price_buy, better_amount) = self.get_items_price(find_new_items=find_new_items)

            if find_new_items:
                self.p2p_item_sell: P2PItem = p2p_item_sell

                self.p2p_item_buy: P2PItem = p2p_item_buy

                (payment_amount, withdraw_amount, usdt_amount, p2p_item_sell, p2p_item_buy,
                 price_sell, price_buy, better_amount) = self.get_items_price(find_new_items=False)

            print('new', p2p_item_sell, p2p_item_buy)
            print('old', self.p2p_item_sell, self.p2p_item_buy)

            if find_new_items:
                prev = {'item_buy': self.p2p_item_buy.to_json() if self.p2p_item_buy else None, 'price_buy': self.price_buy}
                new = { 'item_buy': p2p_item_buy.to_json() if p2p_item_buy else None, 'price_buy': price_buy}

                if self.state == self.STAGE_PROCESS_PAYMENT and self.p2p_item_sell != p2p_item_sell:
                    prev.update({'item_sell': self.p2p_item_sell.to_json() if self.p2p_item_sell else None, 'price_sell': self.price_sell})
                    new.update({'item_sell': p2p_item_sell.to_json() if p2p_item_sell else None, 'price_sell': price_sell})

                self.add_message(message=f'P2P новый ордер', prev=prev, new=new)

            if self.stage == self.STAGE_PROCESS_PAYMENT:
                self.p2p_item_sell: P2PItem = p2p_item_sell  # хэши обновляем
            self.p2p_item_buy: P2PItem = p2p_item_buy

        # TODO banned
        except AuthenticationError:
            print('AuthenticationError')
            self.account.set_cookie_die()
            self.state = OrderBuyToken.STATE_ERROR  # TODO Менять акк если stage 1
            self.save()
            return False
        except (InsufficientErrorSell, InsufficientError) as e:
            print('InsufficientError')
            if isinstance(e, InsufficientErrorSell):
                print(InsufficientErrorSell)
                if self.stage == self.STAGE_PROCESS_PAYMENT and self.p2p_item_sell:
                    if self.p2p_item_sell:
                        self.account.add_insufficient(self.p2p_item_sell)
            elif self.p2p_item_buy:
                self.account.add_insufficient(self.p2p_item_buy)

            if max_counts > 0:  # FIXME Переделать ВСЕ
                time.sleep(3)
                return self.verify_order(bybit_session=bybit_session, find_new_items=True, max_counts=max_counts - 1)  # FIXME max count + delay
            return False

        except (AmountException, DoesNotExist, ValueError) as ex:  # TODO AmountException Обработать как STATE_WRONG_PRICE
            print(f'AmountException/DoesNotExist: {str(ex)}')
            self.state = OrderBuyToken.STATE_ERROR
            self.error_message = 'p2p item not exist'
            self.save()
            return False

        print('verify order:', payment_amount, withdraw_amount, usdt_amount)
        print('order payment', self.payment_amount, self.withdraw_amount)

        print('price_sell', self.price_sell, 'new', price_sell)
        print('price_buy', self.price_buy, 'new', price_buy)  # FIXME !!! нужно в модель сохранить исходную и новую

        if self.stage == self.STAGE_PROCESS_PAYMENT:
            self.usdt_amount = usdt_amount
            self.price_sell = price_sell

        self.price_buy = price_buy

        if ((self.stage == self.STAGE_PROCESS_PAYMENT and (self.payment_amount * 1.0001 < payment_amount or self.withdraw_amount > withdraw_amount * 1.0001) or
             ((self.payment_amount != payment_amount and (self.payment_currency.is_fiat and self.price_sell < price_sell or
                                                          self.payment_currency.is_crypto and self.price_sell > price_sell))) or
             # STAGE 2
             (self.stage == self.STAGE_PROCESS_WITHDRAW and self.withdraw_amount > withdraw_amount * 1.01) or
             (self.withdraw_amount != withdraw_amount and (self.withdraw_currency.is_fiat and self.price_buy > price_buy or
                                                           self.withdraw_currency.is_crypto and self.price_buy < price_buy)))):
            print('WRONG PRICE withdraw', self.withdraw_amount, 'new', withdraw_amount, 'payment', self.payment_amount, 'new', payment_amount)

            # Сохраняется для передачи нового количества. Пользователь может согласиться или нет
            self.state = OrderBuyToken.STATE_WRONG_PRICE
            self.withdraw_amount = withdraw_amount
            self.payment_amount = payment_amount

            self.usdt_amount = usdt_amount

            self.save()
            return False

        # Мы заработали больше от изменения курса
        # if self.stage == self.STAGE_PROCESS_PAYMENT and (self.payment_currency.is_fiat and self.price_sell > price_sell or
        #                                                  self.payment_currency.is_crypto and self.price_sell < price_sell):
        #     print('Мы зарботали')
        #     print('new price', self.price_sell, price_sell)
        #     self.price_sell = price_sell
        #
        # elif self.stage == self.STAGE_PROCESS_WITHDRAW and (self.withdraw_currency.is_fiat and self.price_buy < price_buy or
        #                                                     self.withdraw_currency.is_crypto and self.price_buy > price_buy):
        #     print('Мы зарботали')
        #     print('new price', self.price_sell, price_sell)
        #     self.price_buy = price_buy  # FIXME оригинальная цена обмена теряется

        return True

    def create_trade_deposit(self) -> bool:
        if self.account is None:
            if not self.add_account():
                return False
        bybit_session = BybitSession(self.account)

        if not self.verify_order(bybit_session):
            return False

        deposit_data = bybit_session.get_deposit_address(token=self.payment_currency.token, chain=self.payment_currency.chain)
        print('deposit_data', deposit_data)
        self.internal_address = InternalCryptoAddress.from_json(deposit_data, self.account)
        if self.payment_currency.chain != self.internal_address.chain:
            self.state = OrderBuyToken.STATE_ERROR
            self.save()
            return False

        self.internal_address.save()
        self.save()
        print('saved')
        return True

    def create_p2p_order(self, side=P2PItem.SIDE_SELL, find_new_items=False, max_counts: int = 5) -> bool:
        from CORE.service.tools.tools import Trade  # FIXME

        print('create_p2p_order max_counts', max_counts, find_new_items)

        if self.account is None:
            if not self.add_account():
                return False

        bybit_session = BybitSession(self.account)

        if not self.verify_order(bybit_session, find_new_items=find_new_items):  # FIXME !!! Для вывода фиата разница > 3%
            return False

        try:
            if side == P2PItem.SIDE_SELL:  # Только Ввод
                print('create_p2p_order SIDE_SELL:', self.price_sell, self.p2p_item_sell.price)
                print('SIDE_SELL usdt_amount', self.usdt_amount)
                print('order usdt_amount', self.usdt_amount)
                print('order comm', self.usdt_amount / (1 - self.platform_commission - self.partner_commission))  # Проверить

                if self.p2p_item_sell is None or self.p2p_item_sell.cur_price_hash is None or self.price_sell != self.p2p_item_sell.price:
                    raise AdStatusChanged

                usdt_amount_no_comm = Trade.p2p_quantity(self.payment_amount, self.p2p_item_sell.price, p2p_side=P2PItem.SIDE_SELL)

                order_sell_id = bybit_session.create_order_buy(
                    self.p2p_item_sell.item_id,
                    quantity=usdt_amount_no_comm,  # Количество крипты
                    amount=self.payment_amount,  # Количество фиата
                    cur_price=self.p2p_item_sell.cur_price_hash,
                    token_id='USDT',
                    currency_id=self.payment_currency.token  # 'RUB'
                )

                if order_sell_id is None:  # Забанен за отмену заказов
                    self.account.set_banned()
                    self.account = None
                    self.error_message = 'Аккаунт забанен за создание заказов'
                    self.save()
                    return False  # Меняем аккаунт
                self.order_sell_id = order_sell_id
                self.dt_created_sell = datetime.datetime.now()

            elif side == P2PItem.SIDE_BUY:  # Только Вывод

                print('self.withdraw_amount', self.withdraw_amount)
                print('self.price_buy', self.price_buy)
                print('self.p2p_item_buy', self.p2p_item_buy)

                if self.p2p_item_buy is None or self.p2p_item_buy.cur_price_hash is None or self.price_buy != self.p2p_item_buy.price:
                    raise AdStatusChanged

                del_withdraw_amount = Trade.p2p_quantity(self.usdt_amount, self.price_buy, p2p_side=P2PItem.SIDE_BUY)
                print('SIDE_BUY withdraw_amount', del_withdraw_amount)  # Удалить

                print('amount', self.withdraw_amount)
                print('quantity', self.usdt_amount)

                quantity = self.withdraw_amount / self.price_buy
                print('calc quantity', quantity)
                rquantity = str(format_float_up(float(quantity), token='USDT'))
                print('calc f', rquantity)

                print('term', self.payment_term.paymentType, self.payment_term.payment_id)
                order_buy_id, risk_token = bybit_session.create_order_sell(
                    item_id=self.p2p_item_buy.item_id,
                    quantity=rquantity,  # Количество крипты
                    amount=self.withdraw_amount,  # Количество фиата
                    token_id='USDT',
                    currency_id=self.withdraw_currency.token,  # 'RUB'
                    cur_price=self.p2p_item_buy.cur_price_hash,
                    payment_type=self.payment_term.paymentType,
                    payment_id=self.payment_term.payment_id,
                )

                if order_buy_id is None:  # Забанен за отмену заказов
                    self.account.set_banned()
                    self.account = None
                    self.error_message = 'Аккаунт забанен за создание заказов'
                    self.state = OrderBuyToken.STATE_ERROR
                    self.save()

                    return False  # Возврат средств
                self.order_buy_id = order_buy_id
                self.dt_created_buy = datetime.datetime.now()

            self.save()

        except AdStatusChanged:
            print('AdStatusChanged')

            if max_counts > 0:
                time.sleep(3)  # FIXME Переделать
                return self.create_p2p_order(side=side, find_new_items=True, max_counts=max_counts - 1)
            return False
        return True

    @property
    def current_order_id(self):
        return self.order_sell_id if self.stage == self.STAGE_PROCESS_PAYMENT else self.order_buy_id

    def update_p2p_order_status(self, side=P2PItem.SIDE_SELL, bybit_session: Optional[BybitSession] = None):
        if bybit_session is None:
            bybit_session = BybitSession(self.account)

        if side == P2PItem.SIDE_SELL:  # Вносит фиат
            state, terms, _ = bybit_session.get_order_info(self.order_sell_id, self.payment_currency.payment_id)
            print('Got state', state)

        else:  # Выводит фиат
            state, terms, _ = bybit_session.get_order_info(self.order_buy_id, self.withdraw_currency.payment_id)
            print('Got state', state)

        self.terms = terms.to_json()
        if self.terms:  # Может не выгрузиться из-за ошибок
            self.state = OrderBuyToken.STATE_CREATED if side == P2PItem.SIDE_SELL else OrderBuyToken.STATE_TRANSFERRED
            self.save()  # Нужно отдать клиенту реквизиты и ждать оплаты

            self.update_p2p_order_messages(side=side, bybit_session=bybit_session)

    def update_p2p_order_messages(self, side=P2PItem.SIDE_SELL, bybit_session: Optional[BybitSession] = None):  # Выгружаем сообщения в базу
        if bybit_session is None:
            bybit_session = BybitSession(self.account)

        messages = bybit_session.get_order_messages(self.order_sell_id if side == P2PItem.SIDE_SELL
                                                    else self.order_buy_id)
        for msg in messages:
            message = P2POrderMessage.from_json(self.id, msg)
            if message:
                message.save()

    def verify_risk_token(self, risk_token, bybit_session: BybitSession):
        print('order.verify_risk_token', risk_token)
        components = bybit_session.get_risk_components(risk_token)
        print(components)
        if len(components) == 2:  # Если email верификация - плохо
            # bybit_session.verify_risk_send_email(risk_token)
            # code = input('please enter your code')
            # bybit_session.verify_risk_token(risk_token, order.account.risk_get_ga_code(), email_code=code)
            self.state = OrderBuyToken.STATE_ERROR
            self.error_message = 'NEED EMAIL 2FA'
            self.save()
            return False
        else:
            seconds_to_wait = 30 - (time.time() % 30)
            if seconds_to_wait < 20:
                time.sleep(seconds_to_wait)

            bybit_session.verify_risk_token(risk_token, self.account.risk_get_ga_code())
            print('verified')  # TODO CHECK response
            return True

    def finish_buy_order(self):
        bybit_session = BybitSession(self.account)

        risk_token = bybit_session.finish_p2p_sell(order_id=self.order_buy_id, payment_type=self.withdraw_currency.payment_id)
        print('risk_token', risk_token)
        if not self.verify_risk_token(risk_token, bybit_session):
            return

        bybit_session.finish_p2p_sell(order_id=self.order_buy_id, payment_type=self.withdraw_currency.payment_id, risk_token=risk_token)
        print('order finished')


class P2POrderMessage(models.Model):
    order = models.ForeignKey(OrderBuyToken, on_delete=models.CASCADE)

    CONTENT_TYPE_STR = 'str'
    CONTENT_TYPE_PDF = 'pdf'
    CONTENT_TYPE_VIDEO = 'video'
    CONTENT_TYPE_PIC = 'pic'

    STATUS_DELIVERED = 'delivered'
    STATUS_ERROR = 'error'
    STATUS_SENDING = 'sending'

    STATUSES = (
        (STATUS_SENDING, 'отправляется'),
        (STATUS_DELIVERED, 'доставлено'),
        (STATUS_ERROR, 'ошибка')
    )
    bybit_order_id = models.CharField(max_length=255, null=True, blank=True)
    message_id = models.CharField(max_length=50)
    account_id = models.CharField(max_length=50, blank=True, null=True)
    text = models.TextField(default='', blank=True, null=True)
    dt = models.DateTimeField(blank=True, null=True, default=datetime.datetime.now)
    uuid = models.CharField(max_length=50, blank=True, null=True)
    user_id = models.CharField(max_length=50, blank=True, null=True)
    nick_name = models.CharField(max_length=50, blank=True, null=True)
    type = models.CharField(max_length=10, default=1)  # 1 - переписка, иначе служебное
    content_type = models.CharField(default=CONTENT_TYPE_STR, max_length=20)
    file = models.FileField(upload_to='sent', blank=True, null=True)  # TODO Папка sent закрыта для доступа из вне
    status = models.CharField(default=STATUS_DELIVERED, choices=STATUSES, max_length=20)

    @classmethod
    def from_json(cls, order_index, data):
        print('receive msg', data)
        if P2POrderMessage.objects.filter(message_id=data['id']).exists():
            return

        if data['msgUuid']:  # data['userId'] == order.account.user_id  Отправили мы, проверка на дубли
            if P2POrderMessage.objects.filter(uuid=data['msgUuid']).exists():
                return

        message = P2POrderMessage(order_id=order_index)
        message.message_id = data['id']
        message.account_id = data['accountId']
        message.dt = datetime.datetime.utcfromtimestamp(int(data.get('createDate', 0)) / 1000)
        message.uuid = data['msgUuid']
        message.user_id = data['userId']
        message.nick_name = data['nickName']
        message.type = data['msgType']
        message.content_type = data['contentType']
        if data['contentType'] == cls.CONTENT_TYPE_STR:
            message.text = data['message']
        elif data['contentType'] in [cls.CONTENT_TYPE_PIC, cls.CONTENT_TYPE_PDF, cls.CONTENT_TYPE_VIDEO]:
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
                nickname = 'YOU'  # self.order.name # TODO use order.stage and payment_name / withdraw_name
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
            'file_name': self.file.name,
            'side': side,
        }
        print(res)
        return res


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


class PaymentTerm(models.Model):
    is_active = models.BooleanField(default=True)
    payment_id = models.IntegerField()
    paymentType = models.CharField(max_length=50)
    realName = models.CharField(max_length=150)
    accountNo = models.CharField(max_length=16)  # FIXME может быть больше

    @classmethod
    def from_json(cls, item):
        data = {'payment_id': item['id'], 'paymentType': item['paymentType'], 'realName': item['realName'],
                'accountNo': item['accountNo']}
        return PaymentTerm(**data)

    @classmethod
    def from_bybit_term(cls, item: BybitPaymentTerm):
        data = {'payment_id': item.paymentId, 'paymentType': item.paymentType, 'realName': item.realName,
                'accountNo': item.accountNo}
        return PaymentTerm(**data)

    def __repr__(self):
        return '{Term: ' + self.realName + '}'

    def to_json(self):
        return {
            'id': self.id,
            'payment_id': self.payment_id,
            'paymentType': self.paymentType,
            'realName': self.realName,
            'accountNo': self.accountNo
        }
