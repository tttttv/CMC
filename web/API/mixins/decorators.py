from rest_framework.response import Response
from functools import wraps
import datetime
from CORE.models import OrderBuyToken, Widget


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
        order_hash = request.data.get('order_hash', None)

        if not order_hash:
            return Response({'message': 'order_hash required'}, 403)

        order = OrderBuyToken.objects.get(hash=order_hash)
        if not order:
            return Response({'message': 'invalid'}, 403)

        return view_func(self, request, pk, order, *args, **kwargs)
    return wrapper

