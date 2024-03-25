class BybitP2P:
    def __init__(self, item):
        self.id = item['id']
        self.userId = item['userId']
        self.price = float(item['price'])
        self.quantity = float(item['quantity'])
        self.minAmount = float(item['minAmount'])
        self.maxAmount = float(item['maxAmount'])

    def __repr__(self):
        return '{P2P: ' + self.id + ' ' + str(self.price) + '}'

class PaymentTerm:
    def __init__(self, item):
        self.paymentId = item['id']
        self.paymentType = item['paymentType']
        self.realName = item['realName']
        self.accountNo = item['accountNo']

    def __repr__(self):
        return '{Term: ' + self.realName + '}'

    def to_json(self):
        return {
            'payment_id': self.paymentId,
            'payment_type': self.paymentType,
            'real_name': self.realName,
            'account_no': self.accountNo
        }

    def print(self):
        print(' '.join([self.paymentId, str(self.paymentType), self.realName, self.accountNo]))

class OrderMessage:
    def __init__(self, item):
        self.id = item['id']
        self.accountId = item['accountId']
        self.text = item['message']
        self.createdDate = int(item.get('createdDate', 0))
        self.msgUuid = item['msgUuid']
        self.userId = item['userId']
        self.nickName = item['nickName']
        self.msgType = item['msgType'] #1 - переписка, иначе служебное