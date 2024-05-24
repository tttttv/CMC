import datetime
import traceback
import sys


class ExceptionLoggerMiddleware:
    """
    Перехват исключений и вывод их в консоль
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        return response

    def process_exception(self, request, exception):
        trace = traceback.format_exc()
        timestamp = datetime.datetime.now()
        message = (f'[{timestamp}]\n'
                   f'Exception raised on request {request}.\n'
                   f'User: {request.user.email}\n'
                   f'Partner: {request.user.partner}'
                   f'\n {trace}')

        print(message)
