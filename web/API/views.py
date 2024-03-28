import datetime
from time import sleep

from django.http import JsonResponse
from django.shortcuts import render

# Create your views here.
from django.views.decorators.csrf import csrf_exempt

from CORE.models import P2POrderBuyToken, BybitAccount, P2PItem, BybitSettings, P2POrderMessage
from CORE.service.CONFIG import P2P_TOKENS, TOKENS_DIGITS
from CORE.service.bybit.parser import BybitSession
from CORE.service.tools.formats import format_float, format_float_up
from CORE.service.tools.tools import calculate_withdraw_amount, calculate_topup_amount, get_price
from CORE.tasks import process_buy_order_task, update_latest_email_codes_task, update_p2pitems_task

def get_avalible_from_view(request):
    settings = BybitSettings.objects.get(id=1)
    methods = settings.get_avalible_topup_methods()
    return JsonResponse({'methods': methods})

def get_avalible_to_view(request):
    settings = BybitSettings.objects.get(id=1)
    methods = settings.get_avalible_withdraw_methods()
    return JsonResponse({'methods': methods})

def get_price_view(request):
    settings = BybitSettings.objects.get(id=1)
    anchor = request.GET.get('anchor', 'currency')
    payment_method = int(request.GET.get('payment_method', 377))
    amount = float(request.GET['amount'])
    token = request.GET.get('token', 'USDT')
    chain = request.GET.get('chain', 'MANTLE')

    pm = settings.get_payment_method(payment_method)
    if pm:
        currency = pm['currency']
    else:
        return JsonResponse({'message': 'Currency not found', 'code': 1}, status=404)

    try:
        quantity, best_p2p, better_amount = get_price(payment_method, amount, currency, token, chain, anchor=anchor)
    except TypeError:
        return JsonResponse({'message': 'cant get price', 'code': 2}, status=403)

    data = {
        'price': amount / quantity,
        'quantity': quantity,
        'better_amount': better_amount,
        'best_p2p': best_p2p.item_id
    }
    return JsonResponse(data)

@csrf_exempt
def create_order_view(request):
    settings = BybitSettings.objects.get(id=1)

    if not settings.is_working:
        return JsonResponse({'message': 'not avalible now', 'code': 0}, status=403)

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

    # todo добавить проверку адреса

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

    order.withdraw_address = address  # Todo проверку корректности адреса
    order.save()
    process_buy_order_task.delay(id=order.id)

    data = {
        'order_hash': order.get_hash()
    }
    return JsonResponse(data)

def get_order_state_view(request):
    settings = BybitSettings.objects.get(id=1)
    order_hash = request.GET['order_hash']
    order = P2POrderBuyToken.get_order_by_hash(order_hash)
    if not order:
        return JsonResponse({}, status=404)

    state = None
    state_data = {}
    order_data = {
        'from': settings.get_payment_method(order.payment_method),
        'to': settings.get_token(order.p2p_token),
        'rate': order.amount / order.withdraw_quantity,
        'order_hash': order_hash
    }
    if order.state == P2POrderBuyToken.STATE_INITIATED:
        state = 'INITIALIZATION' #Ожидание создания заказа на бирже
    elif order.state == P2POrderBuyToken.STATE_WRONG_PRICE: #Ошибка создания - цена изменилась
        state = order.state
    elif order.state == P2POrderBuyToken.STATE_CREATED: #Заказ создан, ожидаем перевод
        state = 'PENDING'
        state_data = {
            'terms': order.terms,
            'time_left': (order.dt_created - datetime.datetime.now() + datetime.timedelta(minutes=20)).minutes,
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
    order_hash = request.POST['order_hash']
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    if order.state == order.STATE_CREATED:
        order.state = P2POrderBuyToken.STATE_CANCELLED
        order.save()
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

@csrf_exempt
def mark_order_as_paid_view(request):
    order_hash = request.POST['order_hash']
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    if order.state == P2POrderBuyToken.STATE_CREATED:
        order.state = P2POrderBuyToken.STATE_TRANSFERRED
        order.save()
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

def get_chat_messages_view(request):
    order_hash = request.GET['order_hash']
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    messages = P2POrderMessage.objects.filter(order=order).order_by('-dt')
    data = [m.to_json() for m in messages]

    return JsonResponse({'messages': data, 'title': 'Иван Иванов', 'avatar': '/static/CORE/misc/default_avatar.png'})

@csrf_exempt
def send_chat_message_view(request):
    order_hash = request.POST['order_hash']
    order = P2POrderBuyToken.get_order_by_hash(order_hash)

    text = request.POST['text']

    s = BybitSession(order.account)
    if s.send_message(order.order_id, text):
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Error sending message', 'code': 1}, status=403)