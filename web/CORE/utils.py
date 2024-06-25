import time
from celery.utils.log import get_task_logger
from contextlib import contextmanager
from django.core.cache import cache
from django.db import transaction
from celery import current_app

from CORE.models import OrderBuyToken

LOCK_EXPIRE = 60 * 10  # Lock expires in 10 minutes  # TODO CONFIG


@contextmanager
def order_task_lock(order_id):
    with transaction.atomic():
        order = OrderBuyToken.objects.select_for_update(nowait=True).get(id=order_id, is_executing=False)
        order.is_executing = True
        order.save(update_fields=['is_executing'])  # raise Exc when locked
    try:
        yield True
    finally:
        order = OrderBuyToken.objects.get(id=order_id)
        order.is_executing = False
        order.save(update_fields=['is_executing'])


def get_active_celery_tasks():
    inspector = current_app.control.inspect()
    active_tasks = inspector.active()
    tasks = []
    if active_tasks:
        for worker, tasks_info in active_tasks.items():
            for task_info in tasks_info:
                task_data = {
                    'task_id': task_info['id'],
                    'name': task_info['name'],
                    'args': task_info['args'],
                    'kwargs': task_info['kwargs'],
                }
                tasks.append(task_data)
    return tasks
