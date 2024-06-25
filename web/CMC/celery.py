import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CMC.settings')
app = Celery('CMC', broker='redis://' + os.getenv('REDIS_USER', '') + ':' + os.getenv('REDIS_PASSWORD', '') + '@redis:6379/0')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


@app.on_after_configure.connect
def setup_periodic_tasks(sender, **kwargs):
    app.conf.beat_schedule = {
        'update_prices': {
            'task': 'CORE.tasks.update_p2pitems_task',
            'schedule': crontab(hour='*', minute='*/1'),
        },
        'remove_insufficient_items': {
            'task': 'CORE.tasks.task_remove_insufficient_items',
            'schedule': crontab(hour='*', minute='0'),
        },
        'remove_blacklist_accounts': {
            'task': 'CORE.tasks.task_remove_blacklist_accounts',
            'schedule': crontab(hour='*', minute='10'),
        },
        'update_latest_email_codes': {
            'task': 'CORE.tasks.update_latest_email_codes_task',
            'schedule': crontab(hour='*', minute='*/2'),
        },
        'process_orders': {
            'task': 'CORE.tasks.process_orders_task',
            'schedule': crontab(hour='*', minute='*/1'),
        },

        'healthcare_orders': {
            'task': 'CORE.tasks.healthcare_orders_task',
            'schedule': crontab(hour='*', minute='*/5'),
        },

        'process_messages': {
            'task': 'CORE.tasks.process_orders_messages_task',
            'schedule': crontab(hour='*', minute='*/1'),
        },

    }