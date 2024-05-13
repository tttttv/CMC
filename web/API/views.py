import datetime
import hashlib
import time
from time import sleep

from django.http import JsonResponse
from django.shortcuts import render
import base64
from django.core.files.base import ContentFile

# Create your views here.
from django.views.decorators.csrf import csrf_exempt

from CORE.models import P2POrderBuyToken, BybitAccount, P2PItem, P2POrderMessage, Partner, Widget, \
    BybitCurrency
from CORE.service.CONFIG import P2P_TOKENS, TOKENS_DIGITS
from CORE.service.bybit.parser import BybitSession
from CORE.service.tools.tools import get_price, calculate_withdraw_quantity
from CORE.tasks import process_buy_order_task, update_latest_email_codes_task, update_p2pitems_task

def get_widget_palette_view(request):  # Для Партнеров
    """ Список цветов """
    partner_code = request.POST['partner_code']
    if Partner.objects.filter(code=partner_code).exists():
        return JsonResponse(Widget.DEFAULT_PALETTE)  # TODO default color взять с фронта?
    return JsonResponse({}, status=404)

def get_payment_methods_view(request):  # Для Партнеров
    """ Список валют """
    partner_code = request.POST['partner_code']
    if Partner.objects.filter(code=partner_code).exists():
        return [payment_method.to_json() for payment_method in BybitCurrency.all_payment_methods()]
    return JsonResponse({}, status=404)

def create_widget_view(request):  # Для Партнеров
    partner_code = request.POST['partner_code']
    try:
        partner = Partner.objects.get(code=partner_code)
    except:
        return JsonResponse({}, status=404)

    widget = Widget(partner=partner)  # Фиксируем address token chain
    widget.withdrawing_token = request.POST['withdrawing_token']  # на что меняем
    widget.withdrawing_chain = request.POST['withdrawing_chain']
    widget.withdrawing_address = request.POST['withdrawing_address']

    widget.partner_commission = float(request.POST['partner_commission'])
    widget.platform_commission = partner.platform_commission

    if 'color_palette' in request.POST:
        input_palette = request.POST['color_palette']
        color_palette = {input_palette[color] if color in input_palette else None
                         for color in widget.DEFAULT_PALETTE}
        widget.color_palette = color_palette  # else DEFAULT_PALETTE

    if 'redirect_url' in request.POST:
        widget.redirect_url = request.POST['redirect_url']
        # их url параметры + hash, status

    if 'payment_methods' in request.POST:  # currency
        for currency_id in request.POST['payment_methods']:
            payment_method = BybitCurrency.get_currency(currency_id)
            widget.payment_methods.add(payment_method)

    if 'full_name' in request.POST:
        widget.full_name = request.POST['full_name']

    if 'email' in request.POST:
        widget.full_name = request.POST['email']

    widget.save()

    return JsonResponse({'widget': widget.hash})


@csrf_exempt
def get_widget_settings_view(request):
    widget_hash = request.POST['widget_hash']
    print('widget_hash', widget_hash)
    try:
        widget = Widget.objects.get(hash=widget_hash)
        return JsonResponse({"token": widget.withdrawing_token,
                             "chain": widget.withdrawing_chain,
                             "address": widget.withdrawing_address,

                             "full_name": widget.full_name,
                             'email': widget.email,
                             "color_palette": widget.color_palette,

                             'payment_methods': list(widget.payment_methods.values_list('id', flat=True))
                             })
    except Exception as e:
        print(e)
        return JsonResponse({}, status=404)


def get_available_from_view(request):
    widget_hash = request.GET.get('widget', None)
    if widget_hash:
        widget = Widget.objects.get(hash=widget_hash)
        return JsonResponse(BybitCurrency.cache_exchange_from(widget.payment_methods))
    return JsonResponse({'methods': BybitCurrency.cache_exchange_from()})


def get_available_to_view(request):
    widget_hash = request.GET.get('widget', None)
    if widget_hash:
        widget = Widget.objects.get(hash=widget_hash)
        return JsonResponse(BybitCurrency.cache_exchange_to(widget.withdrawing_token, widget.withdrawing_chain))
    return JsonResponse({'methods': BybitCurrency.cache_exchange_to()})


def get_price_view(request):
    """
    amount - сколько валюты заплатить
    quantity - сколько крипты получит

    :param request:
    :return:
    """
    anchor = request.GET.get('anchor', 'currency')

    currency_id = int(request.GET.get('payment_method', 0))
    amount = float(request.GET.get('amount', 0))
    quantity = float(request.GET.get('quantity', 0))
    token = request.GET.get('token', 'USDT')
    chain = request.GET.get('chain', 'MANTLE')

    if anchor == P2POrderBuyToken.ANCHOR_CURRENCY and amount == 0:
        return JsonResponse({'message': 'amount is zero with anchor=currency', 'code': 3}, status=403)
    elif anchor == P2POrderBuyToken.ANCHOR_TOKEN and quantity == 0:
        return JsonResponse({'message': 'quantity is zero with anchor=token', 'code': 3}, status=403)

    widget_hash = request.GET.get('widget', None)
    if widget_hash:  # Если вдруг по виджету передана не та крипта
        widget = Widget.objects.get(hash=widget_hash)
        if token != widget.withdrawing_token or chain != widget.withdrawing_chain:
            return JsonResponse({}, status=404)

    pm = BybitCurrency.get_currency(currency_id)

    try:
        chain_commission = pm.get_chain(chain)['withdraw_commission']
        amount, quantity, best_p2p, better_p2p = get_price(pm.payment_id, amount, quantity, pm.token, token,
                                                           chain, 0.01, 0.01, chain_commission, anchor=anchor)
    except TypeError as ex:
        return JsonResponse({'message': 'Биржа не работает', 'code': 2}, status=403)
    except ValueError:
        return JsonResponse(
            {'message': 'Ошибка получения цены. Попробуйте другую цену или другой способ пополнения.', 'code': 3},
            status=403)

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
    print(request.POST)
    name = request.POST['name']
    card_number = request.POST['card_number']
    currency_id = int(request.POST.get('payment_method', 0))
    amount = float(request.POST['amount'])
    price = float(request.POST['price'])
    token = request.POST.get('token', 'USDT')
    chain = request.POST.get('chain', 'MANTLE')
    address = request.POST['address']
    email = request.POST['email']
    item_id = request.POST['item_id']
    anchor = request.GET.get('anchor', 'currency')  # FIXME NEW IN FRONT

    order = P2POrderBuyToken()
    order.name = name
    order.card_number = card_number
    order.email = email

    if False:  # Todo валидация адреса
        return JsonResponse({'message': 'wrong address', 'code': 7}, status=403)

    account = BybitAccount.get_free()
    if not account:
        return JsonResponse({'message': 'No free accounts available', 'code': 1}, status=403)
    order.account = account

    order.item = P2PItem.objects.get(item_id=item_id)
    if not order.item.is_active:
        return JsonResponse({'message': 'Item is not active anymore', 'code': 2}, status=403)

    order.amount = amount
    order.p2p_price = price
    order.anchor = anchor

    order.payment_method = BybitCurrency.get_currency(currency_id)

    withdraw_currency = BybitCurrency.get_token(token)
    order.withdraw_token = token
    withdraw_chain = withdraw_currency.get_chain(chain)

    if not withdraw_chain:
        return JsonResponse({'message': 'Chain not found', 'code': 6}, status=404)

    if not withdraw_currency.validate_exchange(order.payment_method):
        return JsonResponse({'message': 'Exchange not allowed', 'code': 6}, status=404)

    order.withdraw_chain = chain

    order.withdraw_address = address

    order.chain_commission = withdraw_chain['withdraw_commission']
    order.trading_commission = 0.001

    widget_hash = request.GET.get('widget', None)
    if widget_hash:  # Если передан виджет
        widget = Widget.objects.get(hash=widget_hash)

        if order.withdraw_token != widget.withdrawing_token \
                or order.withdraw_chain != widget.withdrawing_chain \
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
        'order_hash': str(order.hash)
    }
    return JsonResponse(data)


def get_order_state_view(request):
    order_hash = request.GET['order_hash']
    order = P2POrderBuyToken.objects.get(hash=order_hash)
    if not order:
        return JsonResponse({}, status=404)

    state = None
    state_data = {}
    order_data = {
        'from': order.payment_method.id,
        'to': BybitCurrency.get_token(order.withdraw_token).to_json(),
        'rate': (order.amount / order.withdraw_quantity) if order.withdraw_quantity else None,
        'amount': order.amount,
        'quantity': order.withdraw_quantity,
        'order_hash': order_hash,
    }
    if order.dt_created:
        order_data['time_left'] = (order.dt_created - datetime.datetime.now() + datetime.timedelta(minutes=60)).seconds
    else:
        order_data['time_left'] = 0

    if order.state == P2POrderBuyToken.STATE_INITIATED:
        state = 'INITIALIZATION'  # Ожидание создания заказа на бирже
    elif order.state == P2POrderBuyToken.STATE_WRONG_PRICE:  # Ошибка создания - цена изменилась
        state_data = {
            'withdraw_quantity': order.withdraw_quantity
        }
        state = order.state
    elif order.state == P2POrderBuyToken.STATE_CREATED:  # Заказ создан, ожидаем перевод
        state = 'PENDING'
        state_data = {
            'terms': order.terms,
            # {'real_name': 'Dzhabbarov Vladimir', 'account_no': '2202205075821931', 'payment_id': '2657782', 'payment_type': 377}
            'time_left': (order.dt_created - datetime.datetime.now() + datetime.timedelta(minutes=20)).seconds,
            'commentary': "Просим вас не указывать комментарии к платежу. ФИО плательщика должно соответствовать тому, которое вы указывали при создании заявки, платежи от третьих лиц не принимаются."
        }
    elif order.state == P2POrderBuyToken.STATE_TRANSFERRED:  # Пользователь пометил как отправленный - ждем подтверждение
        state = 'RECEIVING'
    elif order.state == P2POrderBuyToken.STATE_PAID:  # Заказ помечен как оплаченный - ждем подтверждение
        state = 'RECEIVING'
    elif order.state == P2POrderBuyToken.STATE_RECEIVED:  # Продавец подтвердил получение денег
        state = 'BUYING'
    elif order.state == P2POrderBuyToken.STATE_TRADING:  # Меняем на бирже
        state = 'TRADING'
    elif order.state == P2POrderBuyToken.STATE_TRADED:  # Поменяли на бирже
        state = 'TRADING'
    elif order.state == P2POrderBuyToken.STATE_WITHDRAWING:  # Выводим деньги
        state = 'WITHDRAWING'
    elif order.state == P2POrderBuyToken.STATE_WAITING_VERIFICATION:  # Подтверждаем вывод
        state = 'WITHDRAWING'
    elif order.state == P2POrderBuyToken.STATE_WITHDRAWN:  # Успешно
        state = 'SUCCESS'
        state_data = {
            'address': order.withdraw_address
        }
    elif order.state == P2POrderBuyToken.STATE_TIMEOUT:  # Таймаут получения денег
        state = 'TIMEOUT'
    elif order.state == P2POrderBuyToken.STATE_ERROR:  # Критическая ошибка, требующая связи через бота
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
    order = P2POrderBuyToken.objects.get(hash=order_hash)

    if order.state == order.STATE_CREATED:
        order.state = P2POrderBuyToken.STATE_CANCELLED
        order.save()
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)


@csrf_exempt
def continue_with_new_price(request):
    order_hash = request.POST['order_hash']
    order = P2POrderBuyToken.objects.get(hash=order_hash)

    if order.state == order.STATE_WRONG_PRICE:
        order.state = P2POrderBuyToken.STATE_INITIATED
        try:
            # TODO withdraw token/fiat
            chain_commission = BybitCurrency.get_token(order.withdraw_token).get_chain(order.withdraw_chain)[
                'withdraw_commission']
            amount, quantity, best_p2p, better_p2p = get_price(order.payment_method.payment_id, order.amount,
                                                               order.withdraw_quantity,
                                                               order.currency, order.withdraw_token,
                                                               order.withdraw_chain,
                                                               # TODO widget.partner commisions
                                                               0.01, 0.01, chain_commission,  # 0.001
                                                               anchor=order.anchor)  # БЫЛО anchor='amount' ЯВНО БАГ

        except TypeError as ex:
            return JsonResponse({'message': 'cant get new price', 'code': 2}, status=403)

        item = P2PItem.objects.get(item_id=best_p2p.item_id)

        order.item_id = item.id
        order.p2p_price = best_p2p.price

        order.save()
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)


@csrf_exempt
def mark_order_as_paid_view(request):
    order_hash = request.POST['order_hash']
    order = P2POrderBuyToken.objects.get(hash=order_hash)

    if order.state == P2POrderBuyToken.STATE_CREATED:
        order.state = P2POrderBuyToken.STATE_TRANSFERRED
        order.save()
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)


def get_chat_messages_view(request):
    order_hash = request.GET['order_hash']
    order = P2POrderBuyToken.objects.get(hash=order_hash)

    messages = P2POrderMessage.objects.filter(order_id=order.order_id).order_by('-dt')
    data = [m.to_json() for m in messages]

    return JsonResponse({'messages': data, 'title': 'Иван Иванов', 'avatar': '/static/CORE/misc/default_avatar.png'})


@csrf_exempt
def send_chat_message_view(request):
    order_hash = request.POST['order_hash']
    order = P2POrderBuyToken.objects.get(hash=order_hash)

    text = request.POST['text']

    bybit_session = BybitSession(order.account)
    if bybit_session.send_message(order.order_id, text):
        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Error sending message', 'code': 1}, status=403)


@csrf_exempt
def send_chat_image_view(request):
    order_hash = request.GET['order_hash']
    order = P2POrderBuyToken.objects.get(hash=order_hash)

    image_data = request.POST.get("image")
    format, imgstr = image_data.split(';base64,')
    print("format", format, imgstr)
    ext = format.split('/')[-1]

    data = ContentFile(base64.b64decode(imgstr))
    file_name = "'myphoto." + ext

    message = P2POrderMessage(
        order_id='1781097796773679104',
        message_id='-1',
        image=data
    )

    bybit_session = BybitSession(order.account)
    if bybit_session.upload_file(image_data):  # FIXME TEST
        message.save()
        message.image.save(file_name, data, save=True)

        return JsonResponse({})
    else:
        return JsonResponse({'message': 'Error sending message', 'code': 1}, status=403)
