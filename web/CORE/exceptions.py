

class AmountException(Exception):
    pass


class MinPaymentException(AmountException):
    def __init__(self, min_amount: float):
        self.min_amount = min_amount
        super().__init__(f"Минимальное количество для пополнения {min_amount}.")


class MaxPaymentException(AmountException):
    def __init__(self, max_amount: float):
        self.max_amount = max_amount
        super().__init__(f"Максимально количество для пополнения {max_amount}.")


class MinWithdrawException(AmountException):
    def __init__(self, min_amount: float):
        self.min_amount = min_amount
        super().__init__(f"Минимальное количество для вывода {min_amount}.")


class MaxWithdrawException(AmountException):
    def __init__(self, max_amount: float):
        self.max_amount = max_amount
        super().__init__(f"Максимально количество для вывода {max_amount}.")


class DoesNotExist(Exception):
    def __init__(self):
        super().__init__('Ошибка получения цены. Попробуйте другую цену или другой способ пополнения.')

