import base64
import datetime
import random
import uuid

from django.core.files.base import ContentFile
from django.db import transaction
from django.http import JsonResponse
from rest_framework.response import Response
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.decorators import action
# Create your views here.
from rest_framework.viewsets import GenericViewSet

from API.mixins.decorators import widget_hash_required, order_hash_required
from API.serializers import OrderCreateSerializer, OrderStateSerializer, GetPriceSerializer, WidgetCreateSerializer, PaymentCurrencySerializer
from CORE.models import OrderBuyToken, BybitAccount, P2PItem, P2POrderMessage, Partner, Widget, \
    BybitCurrency, Currency
from CORE.service.tools.tools import Trade
from CORE.tasks import process_buy_order_task, task_send_message, task_send_image


class WidgetViewSet(GenericViewSet):
    serializer_class = WidgetCreateSerializer
    queryset = Widget.objects.all()

    @action(methods=['get'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'partner_code': openapi.Schema(type=openapi.TYPE_STRING)}),
    )
    def palette(self, request):  # Для Партнеров
        """ Список цветов """
        partner_code = request.data.get('partner_code', None)
        if partner_code and Partner.objects.filter(code=partner_code).exists():
            return JsonResponse(Widget.DEFAULT_PALETTE, status=200)
        return JsonResponse({}, status=404)

    @action(methods=['get'], detail=False)
    @swagger_auto_schema(
        manual_parameters=[openapi.Parameter('partner_code', openapi.IN_QUERY, 'partner_code', False, type=openapi.TYPE_STRING)],
        responses={200: PaymentCurrencySerializer(many=True)}
    )
    def get_payment_methods_view(self, request):
        """ Список валют """
        partner_code = request.data['partner_code']
        if Partner.objects.filter(code=partner_code).exists():
            payment_methods = BybitCurrency.all_payment_methods()
            serializer = PaymentCurrencySerializer(payment_methods, many=True)
            return Response(serializer.data, status=200)
        return Response({}, status=404)

    @swagger_auto_schema(
        request_body=WidgetCreateSerializer,
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={'widget_hash': openapi.Schema(type=openapi.TYPE_STRING)})}
    )
    def create(self, request):  # Для Партнеров
        """ Создание виджета """
        serializer = WidgetCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        widget = serializer.save()
        return JsonResponse({'widget_hash': widget.hash})

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'widget_hash': openapi.Schema(type=openapi.TYPE_STRING)}),
        responses={200: WidgetCreateSerializer(many=False)}
    )
    @widget_hash_required
    def current(self, request, pk, widget):
        serializer = WidgetCreateSerializer(widget)
        return Response(serializer.data)


class ExchangeVIewSet(GenericViewSet):
    serializer_class = None

    @action(methods=['get'], detail=False)
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('widget', openapi.IN_QUERY, 'id виджета', False, type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'methods': openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                    'fiat': openapi.Schema(type=openapi.TYPE_ARRAY,
                                           items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                               'id': openapi.Schema(type=openapi.TYPE_STRING),
                                               'name': openapi.Schema(type=openapi.TYPE_STRING),
                                               'payment_methods': openapi.Schema(
                                                   type=openapi.TYPE_ARRAY,
                                                   items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                                       'id': openapi.Schema(type=openapi.TYPE_NUMBER),
                                                       'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                       'logo': openapi.Schema(type=openapi.TYPE_STRING),
                                                       'exchange_to': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_NUMBER))
                                                   })
                                               )
                                           })),
                    'crypto': openapi.Schema(type=openapi.TYPE_ARRAY,
                                             items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                                 'id': openapi.Schema(type=openapi.TYPE_STRING),
                                                 'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                 'logo': openapi.Schema(type=openapi.TYPE_STRING),
                                                 'exchange_to': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_NUMBER)),
                                                 'chains': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(
                                                     type=openapi.TYPE_OBJECT, properties={
                                                         'id': openapi.Schema(type=openapi.TYPE_STRING),
                                                         'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                         'withdraw_commission': openapi.Schema(type=openapi.TYPE_NUMBER),
                                                     })
                                                                          )
                                             })
                                             )
                }),
            }),
        }
    )
    def payments(self, request):
        widget_hash = request.query_params.get('widget', None)
        if widget_hash:
            widget = Widget.objects.get(hash=widget_hash)
            return Response({'methods': BybitCurrency.cache_exchange(widget.payment_methods.all())})
        return Response({'methods': BybitCurrency.cache_exchange()})

    @action(methods=['get'], detail=False)
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('widget', openapi.IN_QUERY, 'id виджета', False, type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'methods': openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                    'fiat': openapi.Schema(type=openapi.TYPE_ARRAY,
                                           items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                               'id': openapi.Schema(type=openapi.TYPE_STRING),
                                               'name': openapi.Schema(type=openapi.TYPE_STRING),
                                               'payment_methods': openapi.Schema(
                                                   type=openapi.TYPE_ARRAY,
                                                   items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                                       'id': openapi.Schema(type=openapi.TYPE_NUMBER),
                                                       'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                       'logo': openapi.Schema(type=openapi.TYPE_STRING),
                                                       'exchange_from': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_NUMBER))
                                                   })
                                               )
                                           })),
                    'crypto': openapi.Schema(type=openapi.TYPE_ARRAY,
                                             items=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                                 'id': openapi.Schema(type=openapi.TYPE_STRING),
                                                 'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                 'logo': openapi.Schema(type=openapi.TYPE_STRING),
                                                 'exchange_from': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_NUMBER)),
                                                 'chains': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Schema(
                                                     type=openapi.TYPE_OBJECT, properties={
                                                         'id': openapi.Schema(type=openapi.TYPE_STRING),
                                                         'name': openapi.Schema(type=openapi.TYPE_STRING),
                                                         'withdraw_commission': openapi.Schema(type=openapi.TYPE_NUMBER),
                                                     })
                                                                          )
                                             })
                                             )
                }),
            }),
        }
    )
    def withdraws(self, request):
        widget_hash = request.query_params.get('widget_hash', None)
        if widget_hash:
            widget = Widget.objects.get(hash=widget_hash)
            return JsonResponse(BybitCurrency.cache_exchange((widget.withdrawing_currency.currency_id,), side='BUY'))
        return JsonResponse({'methods': BybitCurrency.cache_exchange(side='BUY')})

    @swagger_auto_schema(
        request_body=GetPriceSerializer,
        responses={
            201: openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                'price': openapi.Schema(type=openapi.FORMAT_FLOAT),
                'payment_amount': openapi.Schema(type=openapi.FORMAT_FLOAT),
                'withdraw_amount': openapi.Schema(type=openapi.FORMAT_FLOAT),
                'better_amount': openapi.Schema(type=openapi.FORMAT_FLOAT),
                'price_sell': openapi.Schema(type=openapi.FORMAT_FLOAT),
                'price_buy': openapi.Schema(type=openapi.FORMAT_FLOAT),
                'item_sell': openapi.Schema(type=openapi.TYPE_STRING),
                'item_buy': openapi.Schema(type=openapi.TYPE_STRING),
            }, required=['price', 'payment_amount', 'withdraw_amount', 'better_amount', 'price_sell', 'price_buy']),

            404: openapi.Schema(type=openapi.TYPE_OBJECT, properties={'message': openapi.Schema(type=openapi.TYPE_STRING)})
        },
    )
    @action(methods=['post'], detail=False)
    def price(self, request):
        payment_method_id = int(request.data.get('payment_method'))
        payment_chain = request.data.get('payment_chain', None)

        withdraw_method_id = int(request.data['withdraw_method'])
        withdraw_chain = request.data.get('withdraw_chain', None)

        anchor = request.data.get('anchor', OrderBuyToken.ANCHOR_SELL)
        amount = float(request.data['amount'])

        if amount == 0.0:
            return JsonResponse({'message': 'amount is zero with anchor=currency', 'code': 3}, status=403)

        if anchor == OrderBuyToken.ANCHOR_SELL:
            payment_amount = amount
            withdraw_amount = 0.0
        elif anchor == OrderBuyToken.ANCHOR_BUY:
            payment_amount = 0.0
            withdraw_amount = amount
        else:
            return JsonResponse({'message': 'Bad anchor SELL | BUY', 'code': 3}, status=403)

        payment_method = BybitCurrency.get_by_id(payment_method_id)
        if payment_method.is_crypto and not payment_method.validate_chain(payment_chain):
            return JsonResponse({'message': 'chain invalid'}, status=403)

        withdraw_method = BybitCurrency.get_by_id(withdraw_method_id)
        if withdraw_method.is_crypto and not withdraw_method.validate_chain(withdraw_chain):
            return JsonResponse({'message': 'chain invalid'}, status=403)

        if not withdraw_method.validate_exchange(payment_method):
            return JsonResponse({'message': 'payment method invalid'}, status=403)

        widget_hash = request.query_params.get('widget', None)
        partner_commission = 0.0
        platform_commission = 0.02  # TODO CONFIG
        trading_commission = 0.001

        if widget_hash:  # Если вдруг по виджету передана не та крипта
            widget = Widget.objects.get(hash=widget_hash)
            if not widget.validate_withdraw(withdraw_method):
                return JsonResponse({'message': 'Bad widget withdraw method'}, status=404)
            partner_commission = widget.partner_commission
            platform_commission = widget.platform_commission

        try:
            trade = Trade(payment_method, withdraw_method,
                          payment_amount, withdraw_amount,
                          withdraw_chain, payment_chain,
                          trading_commission, partner_commission, platform_commission, is_direct=anchor == OrderBuyToken.ANCHOR_SELL)
            (payment_amount, withdraw_amount, usdt_amount, p2p_item_sell, p2p_item_buy,
             price_sell, price_buy, better_amount) = trade.get_amount()

        except TypeError as ex:
            print('ex', ex)
            raise ex
            return JsonResponse({'message': 'Биржа не работает', 'code': 2}, status=403)
        except ValueError as ex:
            print('ex', ex)
            raise ex
            return JsonResponse(
                {'message': 'Ошибка получения цены. Попробуйте другую цену или другой способ пополнения.', 'code': 3},
                status=403)

        data = {
            'price': "%.2f" % (payment_amount / withdraw_amount),

            'payment_amount': payment_amount,
            'withdraw_amount': withdraw_amount,

            'better_amount': better_amount,

            'item_sell': p2p_item_sell.item_id if p2p_item_sell else None,
            'item_buy': p2p_item_buy.item_id if p2p_item_buy else None,

            'price_sell': price_sell,
            'price_buy': price_buy,

        }
        return JsonResponse(data)


class OrderViewSet(GenericViewSet):
    serializer_class = None

    @swagger_auto_schema(
        request_body=OrderCreateSerializer,
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            'order_hash': openapi.Schema(type=openapi.TYPE_STRING)})}
    )
    def create(self, request):  # TODO вынести все в сериализатор
        payment_name = request.data.get('payment_name', None)
        withdraw_name = request.data.get('withdraw_name', None)

        payment_method_id = int(request.data.get('payment_method'))
        payment_chain = request.data.get('payment_chain', None)
        payment_address = request.data['payment_address']  # Карта банка / Адрес криптокошелька
        payment_amount = float(request.data['payment_amount'])

        withdraw_method_id = int(request.data['withdraw_method'])
        withdraw_chain = request.data.get('withdraw_chain', None)
        withdraw_address = request.data['withdraw_address']
        withdraw_amount = float(request.data['withdraw_amount'])

        anchor = request.data.get('anchor', OrderBuyToken.ANCHOR_SELL)
        if anchor != OrderBuyToken.ANCHOR_SELL and anchor != OrderBuyToken.ANCHOR_BUY:
            return JsonResponse({'message': 'Bad anchor SELL | BUY', 'code': 3}, status=403)

        email = request.data['email']  # TODO verif

        # P2P
        p2p_item_sell = request.data.get('item_sell', None)
        price_sell = float(request.data.get('price_sell'))

        p2p_item_buy = request.data.get('item_buy', None)
        price_buy = float(request.data.get('price_buy'))

        if not payment_address or not withdraw_address:  # TODO validate
            return JsonResponse({'message': 'Withdraw and payment address not set'}, status=403)

        _payment_method = BybitCurrency.get_by_id(payment_method_id)

        payment_currency = Currency(currency_id=payment_method_id)
        payment_currency.__dict__.update(_payment_method.__dict__)
        payment_currency.address = payment_address

        _withdraw_method = BybitCurrency.get_by_id(withdraw_method_id)
        withdraw_currency = Currency(currency_id=withdraw_method_id)
        withdraw_currency.__dict__.update(_withdraw_method.__dict__)
        withdraw_currency.address = withdraw_address

        order: OrderBuyToken = OrderBuyToken()

        order.email = email

        if payment_currency.is_fiat:
            if p2p_item_sell is None:
                return JsonResponse({'message': 'Item buy can not be None', 'code': 2}, status=403)
            order.p2p_item_sell = P2PItem.objects.get(item_id=p2p_item_sell)
            if not order.p2p_item_sell.is_active:
                return JsonResponse({'message': 'Item is not active anymore', 'code': 2}, status=403)
            if payment_name is None:
                return JsonResponse({'message': 'Payment name not set', 'code': 2}, status=403)

        elif payment_currency.is_crypto:
            if not payment_currency or not payment_currency.validate_chain(payment_chain):
                return JsonResponse({'message': 'payment_chain invalid'}, status=403)
            payment_currency.chain = payment_chain

        order.price_sell = price_sell

        if withdraw_currency.is_fiat:
            if p2p_item_buy is None:
                return JsonResponse({'message': 'Item sell can not be None', 'code': 2}, status=403)
            order.p2p_item_buy = P2PItem.objects.get(item_id=p2p_item_buy)
            if not order.p2p_item_buy.is_active:
                return JsonResponse({'message': 'Item is not active anymore', 'code': 2}, status=403)
            if withdraw_name is None:
                return JsonResponse({'message': 'Withdraw name not set', 'code': 2}, status=403)

        elif withdraw_currency.is_crypto:
            if not withdraw_chain or not withdraw_currency.validate_chain(withdraw_chain):
                return JsonResponse({'message': 'withdraw_chain invalid'}, status=403)
            withdraw_currency.chain = withdraw_chain

        order.price_buy = price_buy
        order.payment_name = payment_name
        order.withdraw_name = withdraw_name

        with transaction.atomic():  # TODO custom with account
            query = BybitAccount.objects.only('id').filter(is_active=True, active_order__isnull=True)
            count = query.count()
            if count == 0:
                return JsonResponse({'message': 'No free accounts available', 'code': 1}, status=403)

            random_index = random.randint(0, count - 1)
            account_query = query.select_for_update(of=("self",))[random_index:random_index + 1].all()

            if not account_query:
                return JsonResponse({'message': 'No free accounts available', 'code': 1}, status=403)

            order.anchor = anchor
            order.payment_currency = payment_currency
            order.withdraw_currency = withdraw_currency

            order.payment_amount = payment_amount
            order.withdraw_amount = withdraw_amount
            order.trading_commission = 0.001  # FIXME CONFIG

            widget_hash = request.query_params.get('widget', None)
            if widget_hash:  # Если передан виджет
                widget = Widget.objects.get(hash=widget_hash)

                if not widget.validate_withdraw(
                        order.withdraw_currency):  # Если вдруг по виджету передана не та крипта или адрес
                    return JsonResponse({'message': 'Bad widget withdraw method'}, status=404)

                order.widget = widget
                order.partner_commission = order.widget.platform_commission
                order.platform_commission = order.widget.partner_commission
            else:
                order.partner_commission = 0
                order.platform_commission = 0.02  # FIXME CONFIG

            account = account_query[0]
            if account is None:
                return JsonResponse({'message': 'No free accounts available', 'code': 777}, status=403)
            account.active_order = order
            order.account = account

            order.payment_currency.save()
            order.withdraw_currency.save()
            order.save()
            account.save()

        process_buy_order_task.apply_async(args=[order.id])

        data = {
            'order_hash': str(order.hash)
        }
        return JsonResponse(data)

    @action(methods=['get'], detail=False)
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('order_hash', openapi.IN_QUERY, 'id заказа', True, type=openapi.TYPE_STRING),
        ],
        responses={200: OrderStateSerializer(many=False)}
    )
    @order_hash_required
    def state(self, request, pk, order):
        state = None
        state_data = {}
        order_data = {
            'payment': order.payment_currency.to_json(),
            'withdraw': order.withdraw_currency.to_json(),
            'rate': (order.payment_amount / order.withdraw_amount) if order.withdraw_amount else None,
            'payment_amount': order.payment_amount,
            'withdraw_amount': order.withdraw_amount,
            'order_hash': order.hash,
            'stage': order.stage,
        }

        if order.dt_created_sell:
            order_data['time_left'] = max(
                (order.dt_created_sell - datetime.datetime.now() + datetime.timedelta(minutes=60)).seconds, 0)
        else:
            order_data['time_left'] = 0

        if order.state == OrderBuyToken.STATE_INITIATED:
            state = 'INITIALIZATION'  # Ожидание создания заказа на бирже
            order_data['time_left'] = max((order.dt_initiated - datetime.datetime.now() + datetime.timedelta(minutes=60)).seconds, 0)

        elif order.state == OrderBuyToken.STATE_WRONG_PRICE:  # Ошибка создания - цена изменилась
            state_data = {
                'withdraw_amount': order.withdraw_amount
            }
            state = order.state
            order_data['time_left'] = max((order.dt_initiated - datetime.datetime.now() + datetime.timedelta(minutes=60)).seconds, 0)

        elif order.state == OrderBuyToken.STATE_CREATED:  # Заказ создан, ожидаем перевод
            state = 'PENDING'
            if order.payment_currency.is_fiat:
                state_data = {
                    'terms': order.terms,
                    'time_left': (order.dt_created_sell - datetime.datetime.now() + datetime.timedelta(minutes=20)).seconds,
                    'commentary': "Просим вас не указывать комментарии к платежу. ФИО плательщика должно соответствовать тому,"
                                  " которое вы указывали при создании заявки, платежи от третьих лиц не принимаются."
                }
            else:
                state_data = {
                    'terms': order.internal_address.to_json() if order.internal_address else None,
                    'time_left': (order.dt_created_sell - datetime.datetime.now() + datetime.timedelta(minutes=30)).seconds,
                    'commentary': "SEND ME CRYPTO BRO",
                }
        elif order.state == OrderBuyToken.STATE_TRANSFERRED:  # Пользователь пометил как отправленный - ждем подтверждение
            state = 'RECEIVING'
        elif order.state == OrderBuyToken.STATE_PAID or order.state == OrderBuyToken.STATE_WAITING_TRANSACTION_PROCESSED:  # Заказ помечен как оплаченный - ждем подтверждение
            state = 'RECEIVING'
        elif order.stage == order.STAGE_PROCESS_PAYMENT or order.state == OrderBuyToken.STATE_RECEIVED:  # Продавец подтвердил получение денег
            state = 'BUYING'
        elif order.state == OrderBuyToken.STATE_TRADING or order.state == OrderBuyToken.STATE_RECEIVING_CRYPTO:  # Меняем на бирже
            state = 'TRADING'
        elif order.state == OrderBuyToken.STATE_TRADED or order.state == order.STAGE_PROCESS_WITHDRAW and order.state == OrderBuyToken.STATE_RECEIVED:  # Поменяли на бирже
            state = 'TRADING'
        elif order.state == OrderBuyToken.STATE_WITHDRAWING:  # Выводим деньги
            state = 'WITHDRAWING'
        elif order.state == OrderBuyToken.STATE_WAITING_VERIFICATION:  # Подтверждаем вывод
            state = 'WITHDRAWING'
        elif order.state == OrderBuyToken.STATE_WITHDRAWN or order.state == OrderBuyToken.STATE_BUY_CONFIRMED:  # Успешно
            state = 'SUCCESS'
            state_data = {
                'address': order.withdraw_currency.address
            }
        elif order.state == OrderBuyToken.STATE_TIMEOUT:  # Таймаут получения денег
            state = 'TIMEOUT'
        elif order.state == OrderBuyToken.STATE_ERROR:  # Критическая ошибка, требующая связи через бота
            state = 'ERROR'
        elif order.state == OrderBuyToken.STATE_P2P_APPEAL:
            state = 'DISPUTE'

        elif order.state == OrderBuyToken.STATE_WAITING_CONFIRMATION:
            # state = 'PENDING'
            state = 'WITHDRAWING'
            if order.withdraw_currency.is_fiat:
                state_data = {
                    'terms': order.terms,
                    'time_left': (order.dt_created_buy - datetime.datetime.now() + datetime.timedelta(minutes=20)).seconds,
                    'commentary': "Средства были переведены. Необходимо подтвердить получение за указанное время или начать спор"

                }

        data = {
            'order': order_data,
            'state': state,
            'state_data': state_data
        }
        print('ORDER STATE RESP', data)
        return JsonResponse(data)

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'order_hash': openapi.Schema(type=openapi.TYPE_STRING)}),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={})}
    )
    @order_hash_required
    def cancel(self, request, pk, order):
        if order.state == order.STATE_CREATED:
            order.state = OrderBuyToken.STATE_CANCELLED
            order.save()
            return JsonResponse({})
        else:
            return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'order_hash': openapi.Schema(type=openapi.TYPE_STRING)}),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={})}
    )
    @order_hash_required
    def continue_with_new_price(self, request, pk, order):
        if order.state == order.STATE_WRONG_PRICE:
            if order.stage == order.STAGE_PROCESS_PAYMENT:
                order.state = OrderBuyToken.STATE_INITIATED
            else:  # order.state == order.STAGE_PROCESS_WITHDRAW:
                order.state = OrderBuyToken.STATE_RECEIVED

            try:
                trade = Trade(order.payment_currency, order.withdraw_currency, order.payment_amount, order.withdraw_amount,
                              order.withdraw_currency.chain, order.payment_currency.chain,
                              order.trading_commission, order.partner_commission, order.platform_commission,
                              is_direct=order.anchor == OrderBuyToken.ANCHOR_SELL)
                payment_amount, withdraw_amount, usdt_amount, p2p_item_sell, p2p_item_buy, price_sell, price_buy, better_amount = trade.get_amount()
            except TypeError as ex:  # FIXME ValueError
                return JsonResponse({'message': 'cant get new price', 'code': 2}, status=403)

            # order.p2p_item_sell = p2p_item_sell
            # order.p2p_item_buy = p2p_item_buy

            order.save()
            return JsonResponse({})
        else:
            return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'order_hash': openapi.Schema(type=openapi.TYPE_STRING)}),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={})}
    )
    @order_hash_required
    def confirm_payment(self, request, pk, order):
        if order.state == OrderBuyToken.STATE_CREATED:  # FIXME доп. проверять
            order.state = OrderBuyToken.STATE_TRANSFERRED
            order.save()
            return JsonResponse({})
        else:
            return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'order_hash': openapi.Schema(type=openapi.TYPE_STRING)}),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={})}
    )
    @order_hash_required
    def confirm_withdraw(self, request, pk, order):
        if order.state == OrderBuyToken.STATE_WAITING_CONFIRMATION:
            order.state = OrderBuyToken.STATE_BUY_CONFIRMED
            order.save()
            return JsonResponse({})
        else:
            return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={'order_hash': openapi.Schema(type=openapi.TYPE_STRING)}),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={})}
    )
    @order_hash_required
    def open_dispute(self, request, pk, order):
        if order.state == OrderBuyToken.STATE_WAITING_CONFIRMATION:
            order.state = OrderBuyToken.STATE_P2P_APPEAL
            order.save()
            return JsonResponse({})
        else:
            return JsonResponse({'message': 'Wrong order state', 'code': 1}, status=403)

    @action(methods=['get'], detail=False)
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter('order_hash', openapi.IN_QUERY, 'id заказа', True, type=openapi.TYPE_STRING),
        ],
        responses={200: OrderStateSerializer(many=False)}
    )
    @order_hash_required
    def messages(self, request, pk, order):
        messages = P2POrderMessage.objects.filter(order=order).order_by('-dt')
        data = [m.to_json() for m in messages]

        return JsonResponse({'messages': data, 'title': 'Иван Иванов', 'avatar': '/static/CORE/misc/default_avatar.png'})

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            'order_hash': openapi.Schema(type=openapi.TYPE_STRING),
            'text': openapi.Schema(type=openapi.TYPE_STRING)
        }),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={})}
    )
    def send_message(self, request):
        order_hash = request.data['order_hash']
        order = OrderBuyToken.objects.select_related('account').get(hash=order_hash)

        text = request.data['text']

        message_uuid = str(uuid.uuid4())  # генерация uuid для сообщения
        message = P2POrderMessage(
            order=order,
            message_id=message_uuid,
            uuid=message_uuid,
            text=text,
            account_id=order.account_id,
            user_id=order.account.user_id,
            nick_name=order.name,
            type='1'
        )
        message.save()

        task_send_message.delay(message.id)
        return JsonResponse({})

    @action(methods=['post'], detail=False)
    @swagger_auto_schema(
        request_body=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
            'order_hash': openapi.Schema(type=openapi.TYPE_STRING),
            'file': openapi.Schema(type=openapi.TYPE_STRING)
        }),
        responses={200: openapi.Schema(type=openapi.TYPE_OBJECT, properties={})}
    )
    def send_file(self, request):
        order_hash = request.data['order_hash']
        order = OrderBuyToken.objects.select_related('account').get(hash=order_hash)

        image_data = request.data.get("file")
        format, imgstr = image_data.split(';base64,')

        ext = format.split('/')[-1]
        if ext not in ['png', 'jpg', 'jpeg', 'mp4', 'pdf']:
            return JsonResponse({'error': 'Bad file extension. Allowed only: jpeg, png, mp4, pdf.'}, status=400)

        message_uuid = uuid.uuid4()
        file_name = request.data.get('file_name', f'{message_uuid}.{ext}')  # NEW INPUT
        content = ContentFile(base64.b64decode(imgstr), name=file_name)

        mime_types = {
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'mp4': 'video/mp4',
            'pdf': 'application/pdf'
        }
        content_type = mime_types[ext]

        msg_types = {
            'png': P2POrderMessage.CONTENT_TYPE_PIC,
            'jpg': P2POrderMessage.CONTENT_TYPE_PIC,
            'jpeg': P2POrderMessage.CONTENT_TYPE_PIC,
            'mp4': P2POrderMessage.CONTENT_TYPE_VIDEO,
            'pdf': P2POrderMessage.CONTENT_TYPE_PDF
        }
        msg_type = msg_types[ext]

        message = P2POrderMessage(
            order=order,
            message_id=message_uuid,
            uuid=message_uuid,
            text='',
            account_id=order.account_id,
            user_id=order.account.user_id,
            nick_name=order.name,
            content_type=msg_type,
            type='1'
        )
        message.file.save(file_name, content)
        message.save()

        task_send_image.delay(message.id, content_type)

        return JsonResponse({})
