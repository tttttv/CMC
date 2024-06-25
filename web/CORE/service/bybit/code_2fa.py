import hmac, base64, struct, hashlib, time, json, os
import re

from imap_tools import MailBox, AND
import bs4


def get_hotp_token(secret, intervals_no):
    """This is where the magic happens."""
    key = base64.b32decode(normalize(secret), True)  # True is to fold lower into uppercase
    msg = struct.pack(">Q", intervals_no)
    h = bytearray(hmac.new(key, msg, hashlib.sha1).digest())
    o = h[19] & 15
    h = str((struct.unpack(">I", h[o:o + 4])[0] & 0x7fffffff) % 1000000)
    return prefix0(h)


def normalize(key):
    """Normalizes secret by removing spaces and padding with = to a multiple of 8"""
    k2 = key.strip().replace(' ', '')
    # k2 = k2.upper()	# skipped b/c b32decode has a foldcase argument
    if len(k2) % 8 != 0:
        k2 += '=' * (8 - len(k2) % 8)
    return k2


def prefix0(h):
    """Prefixes code with leading zeros if missing."""
    if len(h) < 6:
        h = '0' * (6 - len(h)) + h
    return h


def get_ga_token(secret):
    """The TOTP token is just a HOTP token seeded with every 30 seconds."""
    return get_hotp_token(secret, intervals_no=int(time.time()) // 30)


def get_codes(IMAP_USERNAME='ttt.ttv@yandex.ru', IMAP_PASSWORD='zuouxbywvuqfiubs', IMAP_SERVER='imap.yandex.ru'):
    mb = MailBox(IMAP_SERVER).login(IMAP_USERNAME, IMAP_PASSWORD)

    messages = mb.fetch(criteria=AND(seen=False, from_="bybit.com", subject='Withdrawal Request'),
                        mark_seen=True)

    requests = []
    for msg in messages:
        print(msg.from_, ': ', msg.subject)
        html = msg.html
        soup = bs4.BeautifulSoup(html)
        code = soup.find('div', string="The verification code is:").findNext('b').text
        amount = soup.find('div', string=re.compile('Withdrawal amount: (\d*.?\d*) ')).text
        amount = re.match(r'Withdrawal amount: (\d*.?\d*) ', amount).group(1)
        address = soup.find('div', string=re.compile("Withdrawal address: (.*?) ")).text
        address = re.match(r"Withdrawal address: (.*?) ", address).group(1)
        print(address, amount, code)
        requests.append(
            {
                'address': address,
                'amount': float(amount),
                'code': code,
                'dt': msg.date
            }
        )
    return requests


def get_addressbook_codes(IMAP_USERNAME='ttt.ttv@yandex.ru', IMAP_PASSWORD='zuouxbywvuqfiubs',
                          IMAP_SERVER='imap.yandex.ru'):
    mb = MailBox(IMAP_SERVER).login(IMAP_USERNAME, IMAP_PASSWORD)

    messages = mb.fetch(criteria=AND(seen=False, from_="bybit.com", subject='[Bybit]Email authentication'),
                        mark_seen=True)

    requests = []
    for msg in messages:
        print(msg.from_, ': ', msg.subject)
        html = msg.html
        soup = bs4.BeautifulSoup(html)

        code = soup.find('div', string=re.compile('<strong>(\d{6})</strong>')).text
        code = re.match(r'<strong>(\d{6})</strong>', code).group(1)

        print('GOT ADDRESSBOOK CODE', code)
        requests.append(
            {
                'code': code,
                'dt': msg.date
            }
        )
    return requests
