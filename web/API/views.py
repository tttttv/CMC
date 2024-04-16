import datetime
import hashlib
import time
from time import sleep

from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views.decorators.csrf import csrf_exempt

from CORE.models import P2POrderBuyToken, BybitAccount, P2PItem, BybitSettings, P2POrderMessage, Partner, Widget
from CORE.service.CONFIG import P2P_TOKENS, TOKENS_DIGITS
from CORE.service.bybit.parser import BybitSession
from CORE.service.tools.tools import get_price, calculate_withdraw_quantity
from CORE.tasks import process_buy_order_task, update_latest_email_codes_task, update_p2pitems_task

def create_widget_view(request):
    """ TODO NEW """
    partner_code = request.POST['partner_code']
    try:
        partner = Partner.objects.get(code=partner_code)
    except:
        return JsonResponse({}, status=404)

    widget = Widget(partner=partner)
    widget.withdrawing_token = request.POST['withdrawing_token']
    widget.withdrawing_chain = request.POST['withdrawing_chain']
    widget.withdrawing_address = request.POST['withdrawing_address']
    widget.partner_commission = float(request.POST['partner_commission'])
    widget.save()

    return JsonResponse({'widget': widget.hash})

def get_avalible_from_view(request):
    settings = BybitSettings.objects.get(id=1)
    methods = settings.get_avalible_topup_methods()
    return JsonResponse({'methods': methods})

def get_avalible_to_view(request):
    settings = BybitSettings.objects.get(id=1)
    methods = settings.get_avalible_withdraw_methods()

    widget_hash = request.GET.get('widget', None)
    if widget_hash:
        widget = Widget.objects.get(hash=widget_hash)
        for method in methods:
            if method['id'] == widget.withdrawing_token:
                for chain in method['chains']:
                    if chain['id'] == widget.withdrawing_chain:
                        method['chains'] = chain
                        methods = [method]
                        break

    return JsonResponse({'methods': methods})

def get_price_view(request):
    """
    amount - сколько валюты заплатить
    quantity - сколько крипты получит

    :param request:
    :return:
    """
    settings = BybitSettings.objects.get(id=1)
    anchor = request.GET.get('anchor', 'currency')
    payment_method = int(request.GET.get('payment_method', 377))
    amount = float(request.GET.get('amount', 0))
    quantity = float(request.GET.get('quantity', 0))
    token = request.GET.get('token', 'USDT')
    chain = request.GET.get('chain', 'MANTLE')

    if anchor == 'currency' and amount == 0:
        return JsonResponse({'message': 'amount is zero with anchor=currency', 'code': 3}, status=403)
    elif anchor == 'token' and quantity == 0:
        return JsonResponse({'message': 'quantity is zero with anchor=token', 'code': 3}, status=403)

    widget_hash = request.GET.get('widget', None)
    if widget_hash: #Если вдруг по виджету передана не та крипта
        widget = Widget.objects.get(hash=widget_hash)
        if token != widget.withdrawing_token or chain != widget.withdrawing_chain:
            return JsonResponse({}, status=404)

    pm = settings.get_payment_method(payment_method)
    if pm:
        currency = pm['currency']
    else:
        return JsonResponse({'message': 'Currency not found', 'code': 1}, status=404)

    try:
        chain_commission = settings.get_chain(token, chain)['withdraw_commission']
        amount, quantity, best_p2p, better_p2p = get_price(payment_method, amount, quantity, currency, token, chain, 0.01, 0.01, chain_commission,  anchor=anchor)
    except TypeError as ex:
        return JsonResponse({'message': 'cant get price', 'code': 2}, status=403)

    price = amount / quantity
    data = {
        'price': "%.2f" % (amount / quantity),
        'amount': amount,
        'quantity': quantity,
        'better_amount': better_p2p.min_amount if better_p2p else None,
        'best_p2p': best_p2p.item_id,
        'best_p2p_price': best_p2p.price
    }
    return JsonResponse(data)

@csrf_exempt
def create_order_view(request):
    settings = BybitSettings.objects.get(id=1)

    data = {
        'order_hash': 35742549198872617291353508656626642567 ^ 4
    }
    return JsonResponse(data)

    if not settings.is_working:
        return JsonResponse({'message': 'not avalible now', 'code': 0}, status=403)
    print(request.POST)
    name = request.POST['name']
    card_number = request.POST['card_number']
    payment_method = int(request.GET.get('payment_method', 377))
    amount = float(request.POST['amount'])
    price = float(request.POST['price'])
    token = request.POST.get('token', 'USDT')
    chain = request.POST.get('chain', 'MANTLE')
    address = request.POST['address']
    email = request.POST['email']
    item_id = request.POST['item_id']

    order = P2POrderBuyToken()
    order.name = name
    order.card_number = card_number
    order.email = email

    if False: #Todo валидация адреса
        return JsonResponse({'message': 'wrong address', 'code': 7}, status=403)

    account = BybitAccount.get_free()
    if not account:
        return JsonResponse({'message': 'No free accounts avalible', 'code': 1}, status=403)
    order.account = account

    order.item = P2PItem.objects.get(item_id=item_id)
    if not order.item.is_active:
        return JsonResponse({'message': 'Item is not active anymore', 'code': 2}, status=403)

    if not settings.get_payment_method(payment_method):
        return JsonResponse({'message': 'Invalid payment method', 'code': 3}, status=403)
    order.payment_method = payment_method

    order.amount = amount
    order.p2p_price = price

    pm = settings.get_payment_method(payment_method)
    if pm:
        currency = pm['currency']
    else:
        return JsonResponse({'message': 'Currency not found', 'code': 4}, status=404)

    order.currency = currency

    tk = settings.get_token(token)
    if not tk:
        return JsonResponse({'message': 'Token not found', 'code': 5}, status=404)
    order.withdraw_token = token

    if not settings.get_chain(token, chain):
        return JsonResponse({'message': 'Chain not found', 'code': 6}, status=404)
    order.withdraw_chain = chain

    order.withdraw_address = address

    order.chain_commission = settings.get_chain(token, chain)['withdraw_commission']
    order.trading_commission = 0.001

    widget_hash = request.GET.get('widget', None)
    if widget_hash:  # Если передан виджет
        widget = Widget.objects.get(hash=widget_hash)

        if order.withdraw_token != widget.withdrawing_token \
                or order.withdraw_chain != widget.withdrawing_chain\
                or order.withdraw_address != widget.withdrawing_address:  # Если вдруг по виджету передана не та крипта или адрес
            return JsonResponse({}, status=404)

        order.widget = widget
        order.partner_commission = order.widget.platform_commission
        order.platform_commission = order.widget.partner_commission
    else:
        order.partner_commission = 0
        order.platform_commission = 0.02

    order.save()
    process_buy_order_task.apply_async(args=[order.id])

    data = {
        'order_hash': order.get_hash()
    }
    return JsonResponse(data)

def get_order_state_view(request):
    settings = BybitSettings.objects.get(id=1)
    order_hash = int(request.GET['order_hash'])
    order = P2POrderBuyToken.get_order_by_hash(order_hash)
    if not order:
        return JsonResponse({}, status=404)

    state = None
    state_data = {}
    order_data = {
        'from': settings.get_payment_method(order.payment_method),
        'to': settings.get_token(order.p2p_token),
        'rate': (order.amount / order.withdraw_quantity) if order.withdraw_quantity else None,
        'amount': order.amount,
        'quantity': order.withdraw_quantity,
        'order_hash': order_hash
    }
    if order.state == P2POrderBuyToken.STATE_INITIATED:
        state = 'INITIALIZATION' #Ожидание создания заказа на бирже
    elif order.state == P2POrderBuyToken.STATE_WRONG_PRICE: #Ошибка создания - цена изменилась
        state = order.state
    elif order.state == P2POrderBuyToken.STATE_CREATED: #Заказ создан, ожидаем перевод
        state = 'PENDING'
        state_data = {
            'terms': order.terms, #{'real_name': 'Dzhabbarov Vladimir', 'account_no': '2202205075821931', 'payment_id': '2657782', 'payment_type': 377}
            'time_left': (order.dt_created - datetime.datetime.now() + datetime.timedelta(minutes=20)).seconds,
            'commentary': "Просим вас не указывать комментарии к платежу. ФИО плательщика должно соответствовать тому, которое вы указывали при создании заявки, платежи от третьих лиц не принимаются."
        }
    elif order.state == P2POrderBuyToken.STATE_TRANSFERRED: #Пользователь пометил как отправленный - ждем подтверждение
        state = 'RECEIVING'
    elif order.state == P2POrderBuyToken.STATE_PAID: #Заказ помечен как оплаченный - ждем подтверждение
        state = 'RECEIVING'
    elif order.state == P2POrderBuyToken.STATE_RECEIVED:  #Продавец подтвердил получение денег
        state = 'BUING'
    elif order.state == P2POrderBuyToken.STATE_TRADING: #Меняем на бирже
        state = 'TRADING'
    elif order.state == P2POrderBuyToken.STATE_TRADED: #Поменяли на бирже
        state = 'TRADING'
    elif order.state == P2POrderBuyToken.STATE_WITHDRAWING: #Выводим деньги
        state = 'WITHDRAWING'
    elif order.state == P2POrderBuyToken.STATE_WAITING_VERIFICATION: #Подтверждаем вывод
        state = 'WITHDRAWING'
    elif order.state == P2POrderBuyToken.STATE_WITHDRAWN: #Успешно
        state = 'SUCCESS'
        state_data = {
            'address': order.withdraw_address
        }
    elif order.state == P2POrderBuyToken.STATE_TIMEOUT: #Таймаут получения денег
        state = 'TIMEOUT'
    elif order.state == P2POrderBuyToken.STATE_ERROR: #Критическая ошибка, требующая связи через бота
        state = 'ERROR'

    data = {
        'order': order_data,
        'state': state,
        'state_data': state_data
    }

    return JsonResponse(data)

@csrf_exempt
def cancel_order_view(request):
    order_hash = int(request.POST['order_hash'])
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    if order.state == order.STATE_CREATED:
        order.state = P2POrderBuyToken.STATE_CANCELLED
        order.save()
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

@csrf_exempt
def mark_order_as_paid_view(request):
    order_hash = int(request.POST['order_hash'])
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    if order.state == P2POrderBuyToken.STATE_CREATED:
        order.state = P2POrderBuyToken.STATE_TRANSFERRED
        order.save()
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

def get_chat_messages_view(request):
    order_hash = int(request.GET['order_hash'])
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    messages = P2POrderMessage.objects.filter(order_id=order.order_id).order_by('-dt')
    data = [m.to_json() for m in messages]

    return JsonResponse({'messages': data, 'title': 'Иван Иванов', 'avatar': '/static/CORE/misc/default_avatar.png'})

@csrf_exempt
def send_chat_message_view(request):
    order_hash = int(request.POST['order_hash'])
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    text = request.POST['text']

    s = BybitSession(order.account)
    if s.send_message(order.order_id, text):
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Error sending message', 'code': 1}, status=403)