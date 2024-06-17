import requests


data = {  # СБЕР -> NEAR
    'name': 'Ivan',
    'email': 'ya@gmail.com',

    'payment_method': 3,
    'payment_chain': None,
    'payment_address': '1234123412341234',
    'payment_amount': 500,

    'withdraw_method': 2,
    'withdraw_chain': 'NEAR',
    'withdraw_address': '3377c2555af5d56c33e0cf4e30b05034881342a2ac20b8ee68393192fdb25eef',  # YA
    'withdraw_amount': 0.74,

    'anchor': 'SELL'
}

data = {         # NEAR -> Сбер
    'name': 'Ivan',
    'email': 'ya@gmail.com',

    'payment_method': 2,
    'withdraw_method': 3,
    'payment_chain': 'NEAR',
    'payment_amount': 0.8,
    'withdraw_chain': None,
    'withdraw_amount': 0.0,
    'anchor': 'SELL',
    'payment_address': '3377c2555af5d56c33e0cf4e30b05034881342a2ac20b8ee68393192fdb25eef',
    'withdraw_address': '2202206779337471'
}


data = {         # NEAR -> Сбер
    'name': 'Сидоров Иван А.',
    'email': 'ya@gmail.com',

    'payment_method': 2,
    'withdraw_method': 3,
    'payment_chain': 'NEAR',
    'payment_amount': 0.9,
    'withdraw_chain': None,
    'withdraw_amount': 0.0,
    'anchor': 'SELL',
    'payment_address': '3377c2555af5d56c33e0cf4e30b05034881342a2ac20b8ee68393192fdb25eef',
    'withdraw_address': '2202206779337471'
}

data = {         # Тинек -> NEAR
    'name': 'Сидоров Иван А.',
    'email': 'ya@gmail.com',

    'payment_method': 5,  # 2
    'withdraw_method': 2,  # 3
    'payment_chain': None,
    # 'payment_amount': 500,
    'withdraw_chain': 'NEAR',
    # 'withdraw_amount': 0.0,

    'payment_address': '2200700844943083',
    'withdraw_address': '3377c2555af5d56c33e0cf4e30b05034881342a2ac20b8ee68393192fdb25eef',
    # 'anchor': 'SELL',
    # 'amount': 1000,

    'anchor': 'SELL',
    'amount': 500
}
# data = {         # NEAR -> Тинек
#     'name': 'Сидоров Иван А.',
#     'email': 'ya@gmail.com',
#
#     'payment_method': 2,  # 2
#     'withdraw_method': 5,  # 3
#     'payment_chain': "NEAR",
#     # 'payment_amount': 500,
#     'withdraw_chain': None,
#     # 'withdraw_amount': 0.0,
#     'anchor': 'BUY',
#     'payment_address': '2200700844943083',
#     'withdraw_address': '2202206779337471',
#     # 'amount': 1.0, # 0.72
#     'amount': 1000,
# }


# data = {         # USDT -> NEAR
#     'name': 'Сидоров Иван А.',
#     'email': 'ya@gmail.com',
#
#     'payment_method': 1,
#     'withdraw_method': 2,  # 3
#     'payment_chain': 'MANTLE',
#     'payment_amount': 10,
#     'withdraw_chain': 'NEAR',
#     'withdraw_amount': 0.0,
#     'anchor': 'SELL',
#     'payment_address': '3377c2555af5d56c33e0cf4e30b05034881342a2ac20b8ee68393192fdb25eef',
#     'withdraw_address': '3377c2555af5d56c33e0cf4e30b05034881342a2ac20b8ee68393192fdb25eef'
# }

host = 'http://127.0.0.1:8000'
# host = 'http://api.fleshlight.fun'


if True:
    r = requests.post(f'{host}/api/exchange/price/', data=data)
    print(r.status_code)
    print(r.text)
    resp_data = r.json()
    print('resp_data', resp_data)

    data['payment_amount'] = float(resp_data['payment_amount'])
    data['withdraw_amount'] = float(resp_data['withdraw_amount'])
    data['item_sell'] = resp_data['item_sell']
    data['item_buy'] = resp_data['item_buy']

    data['price_sell'] = resp_data['price_sell']
    data['price_buy'] = resp_data['price_buy']
    # exit()
    # {"price": "675.68", "payment_amount": 500.0, "withdraw_amount": 0.74, "better_amount": 1000.0, "item_sell": "1796864082878500864", "item_buy": null}


print('data', data)
from pprint import pprint
pprint(data)
# exit()

if True:
    r = requests.post(f'{host}/api/order/', data=data)
    print(r.status_code)
    print(r.text[:300])
    exit()

# data = {
#     'order_hash': '8fdUR6uO8sWdwFeqYypDykV-hZnXD47NzZ275Qf3E5dXgst7RU_wwvAB6pS48EUNhYPlBcb_omc0FvRl0PK38HpL7ZtvsxI6vm18cI6sJIwRrFo_TZIU2XUn7DpL1s5-'
# }
#
# if True:
#     r = requests.post('http://127.0.0.1:8000/api/order/continue', data=data)
#     print(r.status_code)
#     print(r.text[:300])


exit()


from CORE.models import *
from CORE.tasks import process_buy_order_task, update_p2pitems_task, task_send_message
from CORE.service.bybit.parser import BybitSession
update_p2pitems_task()

account = BybitAccount.objects.get(id=2)

account = BybitAccount.objects.last()
bybit_session = BybitSession(account)



from CORE.models import *
from CORE.tasks import process_buy_order_task, update_p2pitems_task
from CORE.service.bybit.parser import BybitSession
order = OrderBuyToken.objects.last()
process_buy_order_task(order.id)


order = OrderBuyToken.objects.last()
bybit_session = BybitSession(order.account)

order = OrderBuyToken.objects.last()
order.find_new_items()
order.save()


from CORE.tasks import task_send_message, task_send_image
task_send_message(148)

from CORE.tasks import task_send_message, task_send_image
task_send_image(134, 'application/pdf')



order.update_p2p_order_messages(side=P2PItem.SIDE_SELL)
order.update_p2p_order_messages(side=P2PItem.SIDE_BUY)
