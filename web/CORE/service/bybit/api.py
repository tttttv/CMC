import uuid
import time
import json

from pybit.exceptions import (
    InvalidRequestError
)

from CORE.service.bybit.patch import (
    ProxyHTTP, ProxyMarketHTTP, ProxyWebsocket
)

from CORE.exceptions import InsufficientBalance, DuplicateWithdraw


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
        self.market_session = ProxyMarketHTTP(
            testnet=False,
            api_key=api_key,
            api_secret=api_secret,
            proxy=proxy_settings
        )

    def get_instruments_info(self, sumbol: str = 'NEARUSDT') -> dict:
        r = self.session.get_instruments_info(
            category='spot',
            symbol=sumbol,
            status='Trading'
        )
        print(r)
        return r

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

    def place_limit_order(self, token_sell, token_buy, amount, price, side=SIDE_BUY_CRYPTO):
        try:
            r = self.session.place_order(
                category="spot",
                symbol=token_sell + token_buy,
                side=side,
                orderType="Limit",
                qty=str(amount),
                marketUnit='baseCoin',
                isLeverage=0,
                orderFilter="Order",
                price=price
            )
            print(r)

            if r['retCode'] == 0:
                return r['result']['orderId']
        except InvalidRequestError as exc:
            print(exc)
            print('status code', exc.status_code)
            if exc.status_code == 170131:
                raise InsufficientBalance()
            raise exc

    def get_order_status(self, order_id):
        r = self.session.get_open_orders(
            category="spot",
            orderId=order_id
        )
        if r['retCode'] == 0:
            print(r)
            order_info = r['result']['list'][0]
            add_info = {
                'avg_price': float(order_info['avgPrice']) if order_info['avgPrice'] else 0.0,
                'qty': float(order_info['qty']),
                'exec_qty': float(order_info['cumExecQty']) if order_info['cumExecQty'] else 0.0,
                'leaves_qty':  float(order_info['leavesQty']) if order_info['leavesQty'] else 0.0,
                'leaves_value': float(order_info['leavesValue']) if order_info['leavesValue'] else 0.0,
                'exec_fee': float(order_info['cumExecFee']) if order_info['cumExecFee'] else 0.0,
            }

            return order_info['orderStatus'], int(order_info['createdTime']), add_info
        else:
            print(r)
            raise ValueError

    def cancel_order(self, order_id):
        r = self.session.cancel_order(
            category="spot",
            orderId=order_id
        )
        try:
            if r['retCode'] == 0:
                return True
            else:
                print(r)
                raise ValueError
        except InvalidRequestError as exc:
            if exc.status_code == 170213:
                return False
            raise exc

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

    def withdraw(self, token, chain, address, amount, request_id: str):
        # try:
        r = self.session.withdraw(
            coin=token,
            chain=chain,
            address=address,
            amount=str(amount),
            timestamp=int(time.time() * 1000),
            forceChain=1,
            accountType="FUND",
            requestId=request_id
        )
        print(r)
        if r['retCode'] == 0:
            return r['result']['id']
        else:
            print(r)
            raise ValueError(json.dumps(r))

        # except InvalidRequestError as exc:
        #     if exc.status_code == 131212:
        #         raise DuplicateWithdraw()
        #     raise exc

    def get_withdrawable_amount(self, token) -> float:
        r = self.session.get_withdrawable_amount(coin=token)
        if r['retCode'] == 0:
            result = r['result']
            amount = result['withdrawableAmount']['FUND']['withdrawableAmount']
            return float(amount) if amount else 0.0
        raise ValueError

    def get_deposit_records(self):
        ...

    def get_withdrawal_records(self, withdraw_id):
        r = self.session.get_withdrawal_records(withdrawId=withdraw_id)
        if r['retCode'] == 0:
            for payment in r['result']['rows']:
                if payment['withdrawId'] == withdraw_id:
                    return payment
        return None, None

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

    # print(bybit_api.get_funding_balance('NEAR'))
    # print(bybit_api.get_unified_balance('NEAR'))

    # bybit_api.place_limit_order()

    # bybit_api.get_instruments_info()

    # order_id = bybit_api.place_limit_order('NEAR', 'USDT',
    #                                        trading_quantity, price=limit_price, side=BybitAPI.SIDE_BUY_CRYPTO)
    # print(order_id)

    # status = bybit_api.get_order_status(order.order_buy_id)

    # bybit_api.session.get_tickers(category='spot', symbol='NEARUSDT')

    # bybit_api.get_trading_rate('NEAR', 'USDT')

    print(bybit_api.get_order_status("1713151106802348032"))

    {'nextPageCursor': '1713151106802348032%3A1718959526335%2C1713151106802348032%3A1718959526335', 'category': 'spot', 'list': [
        {'symbol': 'NEARUSDT', 'orderType': 'Limit', 'orderLinkId': '1713151106802348033', 'slLimitPrice': '0', 'orderId': '1713151106802348032', 'cancelType': 'UNKNOWN',
         'avgPrice': '5.2661', 'stopOrderType': '', 'lastPriceOnCreated': '', 'orderStatus': 'Filled', 'takeProfit': '0', 'cumExecValue': '5.266100', 'smpType': 'None',
         'triggerDirection': 0, 'blockTradeId': '', 'isLeverage': '0', 'rejectReason': 'EC_NoError', 'price': '5.3303', 'orderIv': '', 'createdTime': '1718959526335',
         'tpTriggerBy': '', 'positionIdx': 0, 'trailingPercentage': '0', 'timeInForce': 'GTC', 'leavesValue': '0.064200', 'basePrice': '5.2647', 'updatedTime': '1718959526337',
         'side': 'Buy', 'smpGroup': 0, 'triggerPrice': '0.0000', 'tpLimitPrice': '0', 'trailingValue': '0', 'cumExecFee': '0.0018', 'leavesQty': '0.00', 'slTriggerBy': '',
         'closeOnTrigger': False, 'placeType': '', 'cumExecQty': '1.00', 'reduceOnly': False, 'activationPrice': '0', 'qty': '1.00', 'stopLoss': '0', 'marketUnit': '',
         'smpOrderId': '', 'triggerBy': ''}]
     }
