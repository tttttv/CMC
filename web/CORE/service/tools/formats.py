import math
from CORE.service.CONFIG import TOKENS_DIGITS
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

def file_as_base64(file_path):
    """
    :param `file_path` for the complete path of image.
    """

    if not os.path.isfile(file_path):
        return None

    mime_types = {
        '.png': 'image/png',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.mp4': 'video/mp4',
        '.pdf': 'application/pdf'
    }
    file_extension = os.path.splitext(file_path)[1]
    # print('file_extension', file_extension)
    if file_extension not in mime_types:
        raise ValueError("Unsupported file type. Only PNG, JPG, MP4, and PDF are allowed.")

    with open(file_path, 'rb') as img_f:
        encoded_string = base64.b64encode(img_f.read()).decode('utf8')

    mime_type = mime_types[file_extension]
    # return f'data:{mime_type};base64,{encoded_string}'
    return f'data:{mime_type};base64,{encoded_string}'


