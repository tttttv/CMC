import math
from CORE.service.CONFIG import  TOKENS_DIGITS

def format_float(number, digits=4, token=None):
    if token:
        digits = TOKENS_DIGITS[token]

    return math.floor(number * (10 ** int(digits))) / (10 ** int(digits))

def format_float_up(number, digits=4, token=None):
    if token:
        digits = TOKENS_DIGITS[token]

    return math.floor((number * (10 ** int(digits)) + 1)) / (10 ** int(digits))