import time
from celery.utils.log import get_task_logger
from contextlib import contextmanager
from django.core.cache import cache
from django.db import transaction

from CORE.models import P2POrderBuyToken

LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes

@contextmanager
def order_task_lock(order_id):
    with transaction.atomic():
        order = P2POrderBuyToken.objects.select_for_update(nowait=True).get(id=order_id, is_executing=False)
        order.is_executing = True
        order.save(update_fields=['is_executing'])  # raise Exc when locked
    try:
        yield True
    finally:
        order = P2POrderBuyToken.objects.get(id=order_id)
        order.is_executing = False
        order.save(update_fields=['is_executing'])


