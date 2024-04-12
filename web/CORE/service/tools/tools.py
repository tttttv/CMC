from CORE.service.CONFIG import TOKENS_DIGITS, TRANSACTION_FEES, P2P_TOKENS
from CORE.service.tools.formats import format_float, format_float_up



def calculate_withdraw_quantity(token, chain, amount, p2p_price, withdraw_token_rate, platform_commission, partner_commission, trading_commission, chain_commission):
    digits = TOKENS_DIGITS[token]
    return format_float(
        (((amount / p2p_price) * (1 - partner_commission - platform_commission)) / withdraw_token_rate) * ( 1 - trading_commission) - chain_commission
        , digits)


def calculate_topup_amount(token, quantity, p2p_price, trade_rate, platform_commission, partner_commission, trading_commission, chain_commission):
    digits = TOKENS_DIGITS[token]
    return format_float_up(
        (((quantity + chain_commission) / ( 1 - trading_commission )) * trade_rate / ( 1 - partner_commission - platform_commission)) * p2p_price
        , 2)



#todo заложить комиссию трейдинга на бирже
def get_price(payment_method, amount, quantity, currency, token, chain, platform_commission, partner_commission, chain_commission, trading_commission=0.001, anchor='currency'): #anchor currency - фикс сумма фиата, token - фикс крипта
    from CORE.models import BybitAccount, P2PItem

    if not (token in P2P_TOKENS):
        print(1)
        p2p_token = 'USDT'
        trade_rate = BybitAccount.get_random_account().get_api().get_trading_rate(token, 'USDT') #Todo тут только usdt
    else:
        p2p_token = token
        trade_rate = 1

    print(amount, currency, p2p_token, payment_method, quantity)
    if amount == 0 and quantity != 0:
        all_items = P2PItem.objects.filter(side=P2PItem.SIDE_SELL, is_active=True, currency=currency, token=p2p_token).order_by('-price').all()
        items = []
        for item in all_items:
            print(item.price * quantity, item.min_amount, item.max_amount)
            if (item.price * quantity) > item.min_amount and (item.price * quantity) < item.max_amount:
                items.append(item)

        all_better_items = P2PItem.objects.filter(side=P2PItem.SIDE_SELL, is_active=True, currency=currency, token=p2p_token).order_by('-price', '-min_amount').all()
        better_items = []
        for item in all_better_items:
            print(item.price * quantity, item.min_amount, item.max_amount)
            if (item.price * quantity) < item.max_amount:
                better_items.append(item)
    else:
        items = P2PItem.objects.filter(side=P2PItem.SIDE_SELL, is_active=True, min_amount__lte=amount,
                                       max_amount__gte=amount, currency=currency, token=p2p_token).order_by('-price').all()
        better_items = P2PItem.objects.filter(side=P2PItem.SIDE_SELL, is_active=True,
                                              max_amount__gte=amount, currency=currency, token=p2p_token).order_by('-price', '-min_amount').all()

    print(items)
    for i in items:
        print(i.payment_methods, i.item_id)
        if(int(payment_method) in i.payment_methods):
            best_p2p = i
            break
    else:
        return None

    better_p2p = None #Ищем курс лучше для большего объема
    print(better_items)
    for i in better_items:
        print(i.payment_methods, i.item_id)
        if (int(payment_method) in i.payment_methods):
            better_p2p = i
            break

    p2p_price = best_p2p.price

    print(p2p_price, trade_rate)
    if anchor == 'currency': #Считаем сколько крипты получит клиент
        quantity = calculate_withdraw_quantity(token, chain, amount, p2p_price, trade_rate, platform_commission, partner_commission, trading_commission, chain_commission)
    elif anchor == 'token': #Считаем сколько нужно заплатить фиата за количество крипты
        amount = calculate_topup_amount(token, quantity, p2p_price, trade_rate, platform_commission, partner_commission, trading_commission, chain_commission)

    return amount, quantity, best_p2p, better_p2p
