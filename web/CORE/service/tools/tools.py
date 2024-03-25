from CORE.service.CONFIG import TOKENS_DIGITS, TRANSACTION_FEES, P2P_TOKENS
from CORE.service.tools.formats import format_float, format_float_up


def calculate_withdraw_amount(token, chain, amount, p2p_price, withdraw_price):
    from CORE.models import BybitSettings
    digits = TOKENS_DIGITS[token]
    settings = BybitSettings.objects.get(id=1)
    return float((('{:.' + str(digits) + 'f}').format(
        format_float((amount / p2p_price / withdraw_price) / (1 + settings.get_token(token)['withdraw_commission']) - TRANSACTION_FEES[token][chain], digits)
    )))


def calculate_topup_amount(token, amount, p2p_price, trade_rate):
    from CORE.models import BybitSettings
    settings = BybitSettings.objects.get(id=1)
    return format_float_up((amount * p2p_price * trade_rate) *  (1 + settings.get_token(token)['withdraw_commission']), TOKENS_DIGITS[token])



#todo заложить комиссию трейдинга на бирже
def get_price(payment_method, amount, currency, token, chain, anchor='currency'): #anchor currency - фикс сумма фиата, token - фикс крипта
    from CORE.models import BybitAccount, P2PItem

    if not (token in P2P_TOKENS):
        print(1)
        p2p_token = 'USDT'
        trade_rate = BybitAccount.get_random_account().get_api().get_price(token, 'USDT') #Todo тут только usdt
    else:
        p2p_token = token
        trade_rate = 1

    items = P2PItem.objects.filter(side=P2PItem.SIDE_SELL, is_active=True, min_amount__lte=amount,
                                   max_amount__gte=amount, currency=currency, token=p2p_token).order_by('-price').all()
    print(items)
    for i in items:
        print(i.payment_methods, i.item_id)
        if(int(payment_method) in i.payment_methods):
            best_p2p = i
            break
    else:
        return None

    better_p2p = None #Ищем курс лучше для большего объема
    better_items = P2PItem.objects.filter(side=P2PItem.SIDE_SELL, is_active=True,
                                   max_amount__gte=amount, currency=currency, token=p2p_token).order_by('-price', '-min_amount').all()
    print(better_items)
    for i in better_items:
        print(i.payment_methods, i.item_id)
        if (int(payment_method) in i.payment_methods):
            better_p2p = i
            break

    p2p_price = best_p2p.price

    print(p2p_price, trade_rate)
    if anchor == 'currency': #Возвращаем сколько крипты получит клиент
        return calculate_withdraw_amount(token, chain, amount, p2p_price, trade_rate), best_p2p, better_p2p.min_amount
    elif anchor == 'token': #Возвращаем сколько нужно заплатить фиата за количество крипты
        return calculate_topup_amount(token, amount, p2p_price, trade_rate), best_p2p, better_p2p.min_amount
