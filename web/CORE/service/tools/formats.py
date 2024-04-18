import math
from CORE.service.CONFIG import  TOKENS_DIGITS
import os
import base64

def format_float(number, digits=4, token=None):
    if token:
        digits = TOKENS_DIGITS[token]

    return math.floor(number * (10 ** int(digits))) / (10 ** int(digits))

def format_float_up(number, digits=4, token=None):
    if token:
        digits = TOKENS_DIGITS[token]

    return math.floor((number * (10 ** int(digits)) + 1)) / (10 ** int(digits))

def image_as_base64(image_file, format='png'):
    """
    :param `image_file` for the complete path of image.
    :param `format` is format for image, eg: `png` or `jpg`.
    """
    if not os.path.isfile(image_file):
        return None

    encoded_string = ''
    with open(image_file, 'rb') as img_f:
        encoded_string = base64.b64encode(img_f.read())
    return 'data:image/%s;base64,%s' % (format, encoded_string)