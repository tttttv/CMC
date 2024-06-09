from rest_framework.response import Response
from functools import wraps
import datetime
from CORE.models import OrderBuyToken, Widget, Partner


def partner_code_required(view_func):
    @wraps(view_func)
    def wrapper(self, request, pk=None, *args, **kwargs):
        partner_code = request.data.get('partner_code', None)
        if not partner_code:
            return Response({'message': 'partner_code required'}, 403)

        partner = Partner.objects.get(code=partner_code)
        if not partner:
            return Response({'message': 'invalid'}, 403)

        return view_func(self, request, pk, partner, *args, **kwargs)
    return wrapper


def widget_hash_required(view_func):
    @wraps(view_func)
    def wrapper(self, request, pk=None, *args, **kwargs):
        order_hash = request.data.get('widget_hash', None)
        if not order_hash:
            return Response({'message': 'widget_hash required'}, 403)

        widget = Widget.objects.get(hash=order_hash)
        if not widget:
            return Response({'message': 'invalid'}, 403)

        return view_func(self, request, pk, widget, *args, **kwargs)
    return wrapper


def order_hash_required(view_func):
    @wraps(view_func)
    def wrapper(self, request, pk=None, *args, **kwargs):
        if request.method == "GET":
            order_hash = request.query_params.get('order_hash', None)
        else:
            order_hash = request.data.get('order_hash', None)

        if not order_hash:
            return Response({'message': 'order_hash required'}, 403)

        order = OrderBuyToken.objects.get(hash=order_hash)
        if not order:
            return Response({'message': 'invalid'}, 403)

        return view_func(self, request, pk, order, *args, **kwargs)
    return wrapper

