import requests

BASE_URL = 'http://158.160.113.89/api/'

def get_from():
    r = requests.get(BASE_URL + 'exchange/from')
    print(r.json())

def get_to():
    r = requests.get(BASE_URL + 'exchange/to')
    print(r.json())

def get_exchange_price(payment_method, amount, token, chain, anchor='currency'):
    params = {
        'anchor': anchor,
        'payment_method': payment_method,
        'amount': amount,
        'token': token,
        'chain': chain
    }

    r = requests.get(BASE_URL + 'exchange/price', params=params)
    print(r.url)
    print(r.json())

def create_order(payment_method, amount, price, token, chain, address, item_id, name='test', card_number='test', email='test'):
    data = {
        'name': name,
        'card_number': card_number,
        'payment_method': payment_method,
        'amount': amount,
        'price': price,
        'token': token,
        'chain': chain,
        'address': address,
        'email': email,
        'item_id': item_id
    }
    r = requests.post(BASE_URL + 'order', data=data)
    print(r.json())

def get_order_state(order_hash):
    data = {
        'order_hash': order_hash,
    }
    r = requests.get(BASE_URL + 'order/state', params=data)
    print(r.json())

'order/cancel'

def mark_order_as_paid(order_hash):
    data = {
        'order_hash': order_hash,
    }
    r = requests.post(BASE_URL + 'order/paid', data=data)
    print(r.json())

def get_order_messages(order_hash):
    data = {
        'order_hash': order_hash,
    }
    r = requests.get(BASE_URL + 'order/message', params=data)
    print(r.json())

def send_message(order_hash, text):
    data = {
        'order_hash': order_hash,
        'text': text
    }
    r = requests.post(BASE_URL + 'order/message/send', data=data)
    print(r.json())

if __name__ == '__main__':
    #get_exchange_price(377, 500, 'NEAR', 'NEAR')
    #create_order(377, 500, 101.55, 'NEAR', 'NEAR', 'b8c72480a7d962f389ff2954386e3f529770991df04d6c750923a1b3625bbf9d', '1701921848414109696')
    get_order_state('35742549198872617291353508656626642563')
    #mark_order_as_paid('35742549198872617291353508656626642563')
    #get_order_messages('35742549198872617291353508656626642563')
    #send_message('35742549198872617291353508656626642563', 'спасибо')
    #pass