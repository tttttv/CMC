import requests

BASE_URL = 'http://158.160.113.89/api/'

def get_from():
    r = requests.get(BASE_URL + 'exchange/from')
    print(r.json())

def get_to():
    r = requests.get(BASE_URL + 'exchange/to')
    print(r.json())

def get_exchange_price():
    r = requests.get(BASE_URL + 'exchange/price')

def create_order():
    'order'

def get_order_state():
    'order/state'

'order/cancel'

def mark_order_as_paid():
    'order/paid'

'order/message'
'order/message/send'

if __name__ == '__main__':
    get_to()