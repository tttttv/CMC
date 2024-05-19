import json
import time

from pybit.unified_trading import HTTP
import uuid


class BybitAPI():
    def __init__(self, api_key, api_secret):
        self.session = HTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
        )

    def get_trading_rate(self, token_buy, token_sell):
        r = self.session._submit_request(
            method="GET",
            path=f"{self.session.endpoint}/spot/v3/public/quote/ticker/price?symbol=" + token_buy + token_sell,
            auth=True,
        )

        if r['retCode'] == 0:
            return float(r['result']['price'])

    def place_order(self, token_sell, token_buy, amount):
        r = self.session.place_order(
            category="spot",
            symbol=token_sell + token_buy,
            side="Buy",
            orderType="Market",
            qty=amount,
            marketUnit='baseCoin',
            isLeverage=0,
            orderFilter="Order",
        )

        if r['retCode'] == 0:
            return r['result']['orderId']

    def get_order_status(self, order_id):
        params = {
            'orderId': order_id
        }

        r = self.session.get_open_orders(
            category="spot",
            orderId=order_id
        )

        # r = self.session._submit_request(
        #    method="POST",
        #    path=f"{self.session.endpoint}/spot/v3/private/order",
        #    query=params,
        #    auth=True,
        # )

        if r['retCode'] == 0:
            return r['result']['list'][0]['orderStatus']
        else:
            print(r)
            raise ValueError

    def transfer_to_trading(self, token, amount):
        truuid = uuid.uuid4()
        r = self.session.create_internal_transfer(
            transferId=str(truuid),
            coin=token,
            amount=str(amount),
            fromAccountType="FUND",
            toAccountType="UNIFIED",
        )

        if r['retCode'] == 0:
            print(r['result']['transferId'])

    def transfer_to_funding(self, token, amount):
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

    def get_price(self, token_sell, token_buy, side='a'):
        """
        a Ask seller - ордеры на продажу NEAR   По этой цене и выше будем лесенкой выкупать
        b Bid buyer - ордеры на покупку NEAR
        """
        r = self.session.get_orderbook(category="spot", symbol=token_sell+token_buy, limit=25)
        # r = self.session.get_orderbook(category="linear", symbol=token_sell + token_buy)

        if r['retCode'] == 0:
            return r['result'][side]

    def get_price_for_amount(self, token_sell: str, token_buy: str, amount: float, side: str = 'a'):  # NEARUSDT (важен порядок)
        prices = self.get_price(token_sell, token_buy, side)  # a - Покупаем NEAR / b USDT за NEAR
        total_price = 0.0
        for (bid_price, bid_amount) in prices:
            if side == 'a':  # ASC
                total_price += float(bid_price) * min(amount, float(bid_amount))
            else:  # DESC
                total_price += 1.0 / float(bid_price) * min(amount, float(bid_amount))
            amount -= float(bid_amount)
            print('bid', bid_price, bid_amount, 'left', amount)
            if amount < 0.0:
                return total_price
        raise Exception("Не хватило на бирже предложений на покупку")


if __name__ == '__main__':
    api = BybitAPI("lBRokZFJSDNcuQXpcL", "ZmoAS7JbkL4o4BFtKosoCn0e9A6ebcpZ14AE")

    amount = 10
    price = api.get_price_for_amount('NEAR', 'USDT', amount, side='b')
    print('price', price)

    rate = api.get_trading_rate('NEAR', 'USDT')
    # rate = api.get_trading_rate('USDT', 'NEAR')
    print(rate * amount)

    # tr_id = print(api.place_order('NEAR', 'USDT', 5)
    # order_id = api.transfer_to_trade('USDT', 5)
    # status = api.get_order(1633785335043596032)
    # api.withdraw('USDT', 'MANTLE', '0xcb689021987ee9a838081fb27f9dee02098566ee', 3)
    # api.withdraw('NEAR', 'NEAR', '9bfbc37407cbe64cd7b56fc6ef7fa2dfb07210ad6a4c497c831d8ddfc331ca6b', 0.5)
    # api.withdraw('NEAR', 'NEAR', 'b8c72480a7d962f389ff2954386e3f529770991df04d6c750923a1b3625bbf9d', 0.5)
    # api.withdraw('USDT', 'TRX', 'TAibabMu5sWJBunQQHKj5QLQ4k4rDMLSeB', 3)
