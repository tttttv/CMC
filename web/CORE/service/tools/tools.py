import datetime
from dataclasses import dataclass
from typing import Any, Optional

from CORE.models import OrderBuyToken, P2POrderMessage, BybitAccount, P2PItem, AccountInsufficientItems
from CORE.service.CONFIG import TOKENS_DIGITS, P2P_BUY_TIMEOUTS
from django.db.models import F, Q
from django.db.models import Min

from CORE.exceptions import MinWithdrawException, DoesNotExist, MaxWithdrawException, MinPaymentException, MaxPaymentException
from CORE.service.tools.formats import format_float_up, format_float

SIDE_BUY_CRYPTO = 'a'
SIDE_BUY_FIAT = 'b'
STAGE_PROCESS_PAYMENT = 1
STAGE_PROCESS_WITHDRAW = 2


@dataclass
class Trade:
    payment_method: Any
    withdraw_method: Any

    payment_amount: float = 0.0
    withdraw_amount: float = 0.0
    withdraw_chain: Optional[str] = None
    payment_chain: Optional[str] = None

    trading_commission: float = 0.0018
    partner_commission: float = 0.00
    platform_commission: float = 0.02

    is_direct: bool = True

    # Если не заданы находим новые p2p items
    p2p_item_buy: Optional[P2PItem] = None  # p2p item покупки USDT
    p2p_item_sell: Optional[P2PItem] = None  # p2p item продажи USDT

    stage: int = STAGE_PROCESS_PAYMENT
    usdt_amount: Optional[float] = None

    account_id: Optional[int] = None

    def get_amount(self):  # TODO rename ***
        if self.is_direct:
            return self.direct()
        return self.inverse()

    # def crypto_transaction(self, amount, side=P2PItem.SIDE_SELL):
    #     digits = TOKENS_DIGITS[self.withdraw_method.token]
    #     if side == P2PItem.SIDE_SELL:  # Ввод крипты  FIXME Учитывать комиссию chain при вводе ???
    #         return float((('{:.' + str(digits) + 'f}').format((amount -
    #                                                            self.get_chain_commission(self.withdraw_method, self.withdraw_chain)))))
    #     else:  # Вывод крипты
    #         return float((('{:.' + str(digits) + 'f}').format((amount +
    #                                                            self.get_chain_commission(self.withdraw_method, self.withdraw_chain)))))

    @classmethod
    def get_chain_commission(cls, method, chain):
        return float(method.get_chain(chain)['withdraw_commission'])

    @classmethod
    def p2p_quantity(cls, amount, p2p_price, p2p_side=P2PItem.SIDE_SELL):  # Сколько нужно купить на п2п
        if p2p_side == P2PItem.SIDE_SELL:
            # digits = TOKENS_DIGITS['USDT']  # TODO config
            # return float((('{:.' + str(digits) + 'f}').format(amount / p2p_price)))
            return amount / p2p_price
        else:
            # digits = TOKENS_DIGITS['RUB']
            # return float((('{:.' + str(digits) + 'f}').format(amount * p2p_price)))
            return amount * p2p_price

    @classmethod
    def format_amount(cls, token, amount):
        digits = TOKENS_DIGITS[token]
        return float((('{:.' + str(digits) + 'f}').format(amount)))

    # @classmethod
    # def format_amount_up(cls, token, amount):
    #     return format_float_up(amount, token=token)

    def calculate_trade_quantity(self, amount, token_rate, trade_side=SIDE_BUY_CRYPTO):
        if trade_side == SIDE_BUY_CRYPTO:
            chain_commission = self.get_chain_commission(self.withdraw_method, self.withdraw_chain)
            return ((amount / token_rate) + chain_commission) * (1 - self.trading_commission), token_rate
        return amount * token_rate * (1 - self.trading_commission), 1 / token_rate

    def get_trade_price(self, method, payment_amount: float, withdraw_amount: float, trade_side=SIDE_BUY_CRYPTO):
        if method.is_usdt:
            if payment_amount:
                return payment_amount, 1
            if withdraw_amount:
                return withdraw_amount, 1
            raise ValueError()

        trade_rate = self.get_trading_rate(method.token, payment_amount, withdraw_amount)  # , trade_side=trade_side)
        print('trade_rate', trade_rate)
        return self.calculate_trade_quantity(payment_amount or withdraw_amount, trade_rate, trade_side=trade_side)

    def direct(self):
        from CORE.models import P2PItem  # FIXME
        price_sell = better_amount = None

        # STEP 1
        print('direct', self.payment_amount)
        print('payment', self.payment_method.name)
        print('withdraw', self.withdraw_method.name)
        print('stage', self.stage)

        if self.stage == STAGE_PROCESS_PAYMENT:
            self.payment_amount = format_float(self.payment_amount, self.payment_method.token)

            if self.payment_method.is_fiat:
                if self.p2p_item_sell is None:
                    print('p2p_item_sell is None')
                    self.p2p_item_sell, better_p2p = self.get_p2p_price(self.payment_method.payment_id, self.payment_amount, 0.0,
                                                                        self.payment_method.token, 'USDT',
                                                                        p2p_side=P2PItem.SIDE_SELL)
                    if better_p2p is not None:
                        better_amount = better_p2p.min_amount

                price_sell = self.p2p_item_sell.price
                usdt_amount = Trade.p2p_quantity(self.payment_amount, price_sell, p2p_side=P2PItem.SIDE_SELL)  # FORMATED
                print('p2p usdt_amount', usdt_amount)

            else:
                usdt_amount, price_sell = self.get_trade_price(self.payment_method, self.payment_amount, 0.0, trade_side=SIDE_BUY_FIAT)
                print('usdt_amount crypto', usdt_amount)

            usdt_amount = format_float(usdt_amount, token='USDT')

            print('trade usdt_amount', usdt_amount)
            usdt_amount = usdt_amount * (1 - self.partner_commission - self.platform_commission)
            print('usdt_amount comm', usdt_amount)
        else:
            usdt_amount = self.usdt_amount  # Первый stage пропущен

        usdt_amount = format_float(usdt_amount, token='USDT')
        print('usdt_amount', usdt_amount)

        # STEP 2
        if self.withdraw_method.is_fiat:  # Продаем USDT
            print('withdraw take p2p')
            if self.p2p_item_buy is None:
                self.p2p_item_buy, better_p2p = self.get_p2p_price(self.withdraw_method.payment_id, usdt_amount, 0.0,
                                                                   self.withdraw_method.token, 'USDT',
                                                                   p2p_side=P2PItem.SIDE_BUY)
                if better_p2p is not None:
                    better_amount = better_p2p.min_amount if better_amount is None else min(better_amount, better_p2p.min_amount)

            price_buy = self.p2p_item_buy.price
            withdraw_amount = Trade.p2p_quantity(usdt_amount, price_buy, p2p_side=P2PItem.SIDE_BUY)
            print('p2p withdraw_amount', withdraw_amount)

        else:  # withdraw_method.is_crypto
            withdraw_amount, price_buy = self.get_trade_price(self.withdraw_method, usdt_amount, 0.0, trade_side=SIDE_BUY_CRYPTO)
            print('trade withdraw_amount', withdraw_amount)

        withdraw_amount = format_float(withdraw_amount, token=self.withdraw_method.token)

        print('after trade withdraw_amount', withdraw_amount)
        return self.payment_amount, withdraw_amount, usdt_amount, self.p2p_item_sell, self.p2p_item_buy, price_sell, price_buy, better_amount

    def inverse(self):
        from CORE.models import P2PItem  # FIXME
        price_sell = better_amount = None

        print('inverse')
        print('self.withdraw_amount', self.withdraw_amount)

        if self.stage == STAGE_PROCESS_PAYMENT:
            self.withdraw_amount = format_float(self.withdraw_amount, self.withdraw_method.token)

        # STEP 1
        if self.withdraw_method.is_fiat:
            if self.p2p_item_buy is None:
                self.p2p_item_buy, better_p2p = self.get_p2p_price(self.withdraw_method.payment_id, 0.0, self.withdraw_amount,
                                                                   self.withdraw_method.token, 'USDT',
                                                                   p2p_side=P2PItem.SIDE_BUY)
                if better_p2p is not None:
                    better_amount = better_p2p.min_amount

            price_buy = self.p2p_item_buy.price
            usdt_amount = Trade.p2p_quantity(self.withdraw_amount, self.p2p_item_buy.price, p2p_side=P2PItem.SIDE_SELL)

        else:  # withdraw_method.is_crypto:
            # withdraw_amount = self.crypto_transaction(amount=self.withdraw_amount, side=P2PItem.SIDE_BUY)  # !!!
            print('withdraw_amount', self.withdraw_amount)
            withdraw_commission = self.get_chain_commission(self.withdraw_method, self.withdraw_chain)
            withdraw_amount = format_float_up(self.withdraw_amount + withdraw_commission, token=self.withdraw_method.token)

            print('withdraw_amount comm', withdraw_amount)
            usdt_amount, price_buy = self.get_trade_price(self.withdraw_method, 0.0, withdraw_amount, trade_side=SIDE_BUY_FIAT)

        usdt_amount = format_float_up(usdt_amount, token='USDT')
        print('usdt_amount', usdt_amount)

        usdt_amount = usdt_amount / (1 - self.partner_commission - self.platform_commission)

        usdt_amount = format_float_up(usdt_amount, token='USDT')
        print('usdt_amount comm', usdt_amount)

        if self.stage == STAGE_PROCESS_PAYMENT:  # FIXME !!! withdraw_amount unchanged
            # STEP 2
            if self.payment_method.is_fiat:
                if self.p2p_item_sell is None:
                    self.p2p_item_sell, better_p2p = self.get_p2p_price(self.payment_method.payment_id, 0.0, usdt_amount,
                                                                        self.payment_method.token, 'USDT',
                                                                        p2p_side=P2PItem.SIDE_SELL)  # *** SIDE_BUY
                    if better_p2p is not None:
                        better_amount = better_p2p.min_amount if better_amount is None else min(better_amount, better_p2p.min_amount)

                price_sell = self.p2p_item_sell.price
                payment_amount = Trade.p2p_quantity(usdt_amount, self.p2p_item_sell.price, p2p_side=P2PItem.SIDE_BUY)

            else:  # payment_method.is_crypto:
                print('usdt_amount', usdt_amount)
                payment_amount, price_sell = self.get_trade_price(self.payment_method, 0.0, usdt_amount, trade_side=SIDE_BUY_CRYPTO)
                print('price_sell', price_sell)
                print('payment_amount', payment_amount)

            self.payment_amount = format_float_up(payment_amount, token=self.payment_method.token)
            print('payment_amount up', payment_amount)

        return self.payment_amount, self.withdraw_amount, usdt_amount, self.p2p_item_sell, self.p2p_item_buy, price_sell, price_buy, better_amount

    @classmethod
    def get_trading_rate(cls, token, payment_amount: float, withdraw_amount: float, trade_side=SIDE_BUY_CRYPTO):
        from CORE.models import BybitAccount
        bybit_api = BybitAccount.get_random_account().get_api()  # FIXME Брать аккаунт из order ???

        trade_rate = bybit_api.get_trading_rate(token, 'USDT')

        # if payment_amount == 0.0 and withdraw_amount != 0.0:
        #     trade_rate = bybit_api.get_trading_rate_for_amount(token, 'USDT', withdraw_amount, trade_side)
        # elif withdraw_amount == 0.0 and payment_amount != 0.0:
        #     trade_rate = bybit_api.get_trading_rate_for_amount(token, 'USDT', payment_amount, trade_side)
        # else:
        #     raise ValueError
        return trade_rate

    def get_p2p_price(self, payment_method: int, payment_amount: float, withdraw_amount: float, currency, token, p2p_side):
        from CORE.models import P2PItem

        token = 'USDT'  # todo тут только usdt

        is_p2p_buying_crypto = p2p_side == P2PItem.SIDE_SELL
        print('p2p price')
        print('payment_amount', payment_amount)
        print('withdraw_amount', withdraw_amount)
        print('currency', currency)
        print('p2p_side', p2p_side)
        print(p2p_side == P2PItem.SIDE_BUY, withdraw_amount == 0.0, payment_amount == 0.0)

        if ((p2p_side == P2PItem.SIDE_SELL and payment_amount == 0.0 and withdraw_amount != 0.0) or
                (p2p_side == P2PItem.SIDE_BUY and payment_amount != 0.0 and withdraw_amount == 0.0)):
            print('FIRST')
            items_query = P2PItem.objects.annotate(req_amount=(F('price') * (withdraw_amount or payment_amount))).filter(
                Q(req_amount__gt=F('min_amount')) & Q(req_amount__lt=F('max_amount')))

        elif ((p2p_side == P2PItem.SIDE_SELL and withdraw_amount == 0.0 and payment_amount != 0.0) or
              (p2p_side == P2PItem.SIDE_BUY and withdraw_amount != 0.0 and payment_amount == 0.0)):
            print('SECOND')
            items_query = P2PItem.objects.filter(min_amount__lte=payment_amount or withdraw_amount, max_amount__gte=payment_amount or withdraw_amount)
        else:
            raise ValueError

        items_query = items_query.filter(side=p2p_side, is_active=True, currency=currency, token=token, payment_methods__contains=[payment_method])

        exclude_insufficient = None
        if self.account_id is not None:
            print('EXCLUDE')
            exclude_insufficient = AccountInsufficientItems.objects.filter(
                account_id=self.account_id,
                expire_dt__gt=datetime.datetime.now()
            ).values_list('item_id', flat=True).all()

            # AccountInsufficientItems.objects.filter(
            #     account_id=self.account_id,
            #     expire_dt__gt=datetime.datetime.now()
            # ).values_list('item__item_id', flat=True).all()

            print('exclude_insufficient', exclude_insufficient)
            if exclude_insufficient:
                items_query = items_query.exclude(id__in=exclude_insufficient)

        print('SQL')
        print(items_query.query)
        # items = items_query.order_by('price' if is_p2p_buying_crypto else '-price').all()
        # print('items', items.count())
        best_p2p = items_query.order_by('price' if is_p2p_buying_crypto else '-price').first()
        # for i in items[:5]:
        #     print('item', i, i.price, i.min_amount, i.max_amount)
        # print()
        # for i in items:
        #     print('item', i, i.price, i.min_amount, i.max_amount, 'ttt', i.price * (withdraw_amount or payment_amount))
        #     if int(payment_method) in i.payment_methods:
        #         best_p2p = i
        #         break
        # else:
        if best_p2p is None:
            if ((p2p_side == P2PItem.SIDE_SELL and payment_amount == 0.0 and withdraw_amount != 0.0) or
                    (p2p_side == P2PItem.SIDE_BUY and payment_amount != 0.0 and withdraw_amount == 0.0)):
                print('EXCEPTION FIRST')  # FIXME !!! Нужно второй этап с ошибкой возвращать в Traid()
                items_query = P2PItem.objects.filter(side=p2p_side, is_active=True, currency=currency, token=token, payment_methods__contains=[payment_method])
                if exclude_insufficient:
                    items_query = items_query.exclude(id__in=exclude_insufficient)

                if not items_query.annotate(req_amount=(F('price') * (withdraw_amount or payment_amount))).filter(Q(req_amount__gt=F('min_amount'))).exists():
                    # min_amount = items_query.aggregate(Min('min_amount'))['min_amount__min']
                    min_item = items_query.order_by('min_amount', 'price' if is_p2p_buying_crypto else '-price').first()

                    if min_item is None:
                        raise DoesNotExist()

                    if is_p2p_buying_crypto:
                        raise MinWithdrawException(format_float_up(min_item.min_amount / min_item.price))

                if not items_query.annotate(req_amount=(F('price') * (withdraw_amount or payment_amount))).filter(Q(req_amount__lt=F('max_amount'))).exists():
                    # max_amount = items_query.aggregate(Min('max_amount'))['max_amount__max']
                    max_item = items_query.order_by('min_amount', 'price' if is_p2p_buying_crypto else '-price').first()
                    if max_item is None:
                        raise DoesNotExist()

                    raise MaxWithdrawException(format_float_up(max_item.max_amount / max_item.price))

            elif ((p2p_side == P2PItem.SIDE_SELL and withdraw_amount == 0.0 and payment_amount != 0.0) or
                  (p2p_side == P2PItem.SIDE_BUY and withdraw_amount != 0.0 and payment_amount == 0.0)):
                print('EXCEPTION SECOND')

                items_query = P2PItem.objects.filter(side=p2p_side, is_active=True, currency=currency, token=token, payment_methods__contains=[payment_method])
                if exclude_insufficient:
                    items_query = items_query.exclude(id__in=exclude_insufficient)

                if not items_query.filter(min_amount__lte=payment_amount or withdraw_amount).exists():
                    min_amount = items_query.aggregate(Min('min_amount'))['min_amount__min']
                    if min_amount is None:
                        raise DoesNotExist()

                    raise MinPaymentException(min_amount)

                if not items_query.filter(max_amount__gte=payment_amount or withdraw_amount).exists():
                    max_amount = items_query.aggregate(Min('max_amount'))['max_amount__max']
                    if max_amount is None:
                        raise DoesNotExist()

                    raise MaxPaymentException(max_amount)

            # if P2PItem.objects.filter(is_active=True).exists():
            #     raise DoesNotExist
            raise DoesNotExist()

        print('BEST P2P', best_p2p.price, best_p2p.min_amount, best_p2p.id)

        # better_query = P2PItem.objects.filter(side=p2p_side, is_active=True, max_amount__gte=payment_amount or withdraw_amount,
        #                                       currency=currency, token=token, payment_methods__contains=[payment_method])

        # Ищем курс лучше для большего объема
        if ((p2p_side == P2PItem.SIDE_SELL and payment_amount == 0.0 and withdraw_amount != 0.0) or
                (p2p_side == P2PItem.SIDE_BUY and payment_amount != 0.0 and withdraw_amount == 0.0)):
            print('BEST FIRST')
            better_query = P2PItem.objects.annotate(req_amount=(F('price') * (withdraw_amount or payment_amount))).filter(Q(req_amount__lt=F('min_amount')))

        elif ((p2p_side == P2PItem.SIDE_SELL and withdraw_amount == 0.0 and payment_amount != 0.0) or
              (p2p_side == P2PItem.SIDE_BUY and withdraw_amount != 0.0 and payment_amount == 0.0)):
            print('BEST SECOND')
            better_query = P2PItem.objects.filter(min_amount__gte=payment_amount or withdraw_amount)

        else:
            raise ValueError

        better_query = better_query.filter(side=p2p_side, is_active=True, currency=currency, token=token, payment_methods__contains=[payment_method])
        if exclude_insufficient:
            better_query = better_query.exclude(id__in=exclude_insufficient)

        if is_p2p_buying_crypto:
            better_p2p = better_query.filter(price__lt=best_p2p.price).order_by('min_amount', 'price').first()
            # better_min_amount = better_query.aggregate(Min('price'))['price__min']
            print('FIRST better_p2p', better_p2p)
        else:
            # better_min_amount = better_query.aggregate(Max('price'))['price__max']
            better_p2p = better_query.filter(price__gt=best_p2p.price).order_by('min_amount', '-price').first()
            print('SECOND better_p2p', better_p2p)

        # better_p2p = None
        # for i in better_items:
        #     print(i.payment_methods, i.item_id)
        #     if int(payment_method) in i.payment_methods:
        #         better_p2p = i
        #         print('FINAL', i.price, i.min_amount, i.id)
        #         break

        # p2p_price = best_p2p.price

        # print(p2p_price, better_p2p)
        return best_p2p, better_p2p
