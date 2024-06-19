import json
import time

from pybit.unified_trading import HTTP
from pybit.exceptions import (
    InvalidRequestError
)
import uuid

from CORE.exceptions import InsufficientBalance


class ProxyHTTP(HTTP):
    def __init__(self, proxy: dict = None, **kwargs):
        super().__init__(**kwargs)
        if proxy:
            self.client.proxies.update(proxy)


class BybitAPI:
    SIDE_BUY_CRYPTO = 'Buy'
    SIDE_BUY_FIAT = 'Sell'

    def __init__(self, api_key, api_secret, proxy_settings: dict = None):
        self.proxy_settings: dict = proxy_settings
        print('BybitAPI use proxy', proxy_settings)

        self.session = ProxyHTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
            proxy=proxy_settings
        )

    def get_trading_rate(self, crypto, fiat):
        r = self.session._submit_request(
            method="GET",
            path=f"{self.session.endpoint}/spot/v3/public/quote/ticker/price?symbol=" + crypto + fiat,
            auth=True,
        )

        if r['retCode'] == 0:
            return float(r['result']['price'])
        raise ValueError()

    def place_order(self, token_sell, token_buy, amount, side=SIDE_BUY_CRYPTO):
        try:
            r = self.session.place_order(
                category="spot",
                symbol=token_sell + token_buy,
                side=side,
                orderType="Market",
                qty=str(amount),
                marketUnit='baseCoin',
                isLeverage=0,
                orderFilter="Order",
            )

            if r['retCode'] == 0:
                return r['result']['orderId']
        except InvalidRequestError as exc:
            print(exc)
            print('status code', exc.status_code)
            if exc.status_code == 170131:
                raise InsufficientBalance()

    def get_order_status(self, order_id):
        r = self.session.get_open_orders(
            category="spot",
            orderId=order_id
        )

        if r['retCode'] == 0:
            return r['result']['list'][0]['orderStatus']
        else:
            print(r)
            raise ValueError

    def get_coin_balance(self, accountType="FUND", token='USDT'):
        resp = self.session.get_coin_balance(accountType=accountType, coin=token)
        print(resp)
        if resp['retCode'] == 0:
            balance = resp['result']['balance']['transferBalance']
            return float(balance) if balance else 0.0
        raise ValueError

    def transfer_to_trading(self, token, amount):
        try:
            truuid = uuid.uuid4()
            r = self.session.create_internal_transfer(
                transferId=str(truuid),
                coin=token,
                amount=str(amount),
                fromAccountType="FUND",
                toAccountType="UNIFIED",
            )
            print('transfer_to_trading resp:', r)
            if r['retCode'] == 0:
                print(r['result']['transferId'])

        except InvalidRequestError as exc:
            if exc.status_code == 131212:
                raise InsufficientBalance()

    def transfer_to_funding(self, token, amount):
        try:
            truuid = uuid.uuid4()
            r = self.session.create_internal_transfer(
                transferId=str(truuid),
                coin=token,
                amount=str(amount),
                fromAccountType="UNIFIED",
                toAccountType="FUND",
            )

            if r['retCode'] == 0:
                print(r['result']['transferId'])
        except InvalidRequestError as exc:
            if exc.status_code == 131212:
                raise InsufficientBalance()

    def withdraw(self, token, chain, address, amount):
        r = self.session.withdraw(
            coin=token,
            chain=chain,
            address=address,
            amount=str(amount),
            timestamp=int(time.time() * 1000),
            forceChain=1,
            accountType="FUND",
        )

        if r['retCode'] == 0:
            return True
        else:
            raise ValueError(json.dumps(r))

    def get_price(self, crypto: str, fiat: str, side: str = SIDE_BUY_CRYPTO):
        """
        a Ask seller - ордеры на продажу NEAR   По этой цене и выше будем лесенкой выкупать
        b Bid buyer - ордеры на покупку NEAR
        """
        r = self.session.get_orderbook(category="spot", symbol=crypto + fiat, limit=25)
        if r['retCode'] == 0:
            return r['result']['a' if side == self.SIDE_BUY_FIAT else 'b']

    def get_price_for_amount(self, token_sell: str, token_buy: str, amount: float, side: str = SIDE_BUY_CRYPTO):  # NEARUSDT (важен порядок)
        prices = self.get_price(token_sell, token_buy, side)  # a - Покупаем NEAR / b USDT за NEAR
        total_price = 0.0
        for (bid_price, bid_amount) in prices:
            if side == self.SIDE_BUY_FIAT:  # ASC
                total_price += float(bid_price) * min(amount, float(bid_amount))
            else:  # DESC
                total_price += 1.0 / float(bid_price) * min(amount, float(bid_amount))
            amount -= float(bid_amount)
            # print('bid', bid_price, bid_amount, 'left', amount)
            if amount < 0.0:
                return total_price
        raise Exception("Не хватило на бирже предложений на покупку")

    def get_trading_rate_for_amount(self, crypto: str, fiat: str, amount: float, side: str = SIDE_BUY_CRYPTO):
        total_price = self.get_price_for_amount(crypto, fiat, amount, side=side)
        trade_rate = total_price / amount
        return trade_rate

    def get_funding_balance(self, token: str = 'USDT') -> float:
        return self.get_coin_balance('FUND', token)

    def get_unified_balance(self, token: str = 'USDT') -> float:
        return self.get_coin_balance('UNIFIED', token)


if __name__ == '__main__':
    bybit_api = BybitAPI("lBRokZFJSDNcuQXpcL", "ZmoAS7JbkL4o4BFtKosoCn0e9A6ebcpZ14AE")

    trading_quantity = 30
    total_price = bybit_api.get_price_for_amount('NEAR', 'USDT', trading_quantity, side=BybitAPI.SIDE_BUY_FIAT)
    print('bins total_price', total_price)
    trade_rate = total_price / trading_quantity
    print('bins trade_rate', trade_rate)

    # market_order_id = bybit_api.place_order('NEAR', 'USDT', trading_quantity,
    #                                        side=BybitAPI.SIDE_BUY_CRYPTO)
    # print('market_order_id', market_order_id)

    # bybit_api.transfer_to_trading('USDT', 100)
    # bybit_api.transfer_to_funding('USDT', 100)

    print(bybit_api.get_funding_balance('NEAR'))
    print(bybit_api.get_unified_balance('NEAR'))

