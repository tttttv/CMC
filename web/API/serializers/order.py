from rest_framework import serializers
from CORE.models import *


class OrderCreateSerializer(serializers.Serializer):
    name = serializers.CharField(read_only=True)
    email = serializers.EmailField(required=True)

    payment_method = serializers.IntegerField(required=True)
    payment_chain = serializers.CharField(required=False, default=None)
    payment_address = serializers.CharField(required=True)
    payment_amount = serializers.FloatField(required=True)

    withdraw_method = serializers.IntegerField(required=True)
    withdraw_chain = serializers.CharField(required=False, default=None)
    withdraw_address = serializers.CharField(required=True)
    withdraw_amount = serializers.FloatField(required=True)

    anchor = serializers.ChoiceField(required=True, choices=OrderBuyToken.ANCHORS)

    item_sell = serializers.CharField(required=True)
    price_sell = serializers.FloatField(required=True)
    item_buy = serializers.CharField(required=True)
    price_buy = serializers.FloatField(required=True)


class PaymentCurrencySerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    type = serializers.ChoiceField(read_only=True, choices=BybitCurrency.TYPES)
    name = serializers.CharField(read_only=True)
    chain = serializers.CharField(read_only=True)
    address = serializers.CharField(read_only=True)
    logo = serializers.SerializerMethodField(read_only=True)

    def get_logo(self, currency):
        return currency.logo()

    class Meta:
        model = Currency
        fields = '__all__'


class InternalCryptoAddress(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    address = serializers.CharField(read_only=True)
    chain = serializers.CharField(read_only=True)
    chain_name = serializers.CharField(read_only=True)
    qrcode = serializers.CharField(read_only=True)

    class Meta:
        model = InternalCryptoAddress
        fields = ('id', 'address', 'chain', 'chain_name', 'qrcode')


class OrderStateDataSerializer(serializers.ModelSerializer):
    payment = PaymentCurrencySerializer(read_only=True, source='payment_currency'),
    withdraw = PaymentCurrencySerializer(read_only=True, source='withdraw_currency'),
    transfer = InternalCryptoAddress(required=False, source='internal_address'),

    rate = serializers.FloatField(read_only=True),
    payment_amount = serializers.FloatField(read_only=True),
    withdraw_amount = serializers.FloatField(read_only=True),
    order_hash = serializers.CharField(read_only=True),

    stage = serializers.ChoiceField(read_only=True, choices=OrderBuyToken.STAGES),
    state = serializers.CharField(read_only=True)

    class Meta:  # FIXME DEL ***
        model = OrderBuyToken
        fields = '__all__'


class StateDataSerializer(serializers.Serializer):
    terms = serializers.JSONField(read_only=True, required=False)
    time_left = serializers.IntegerField(read_only=True, required=False)
    commentary = serializers.CharField(read_only=True, required=False)


class OrderStateSerializer(StateDataSerializer):
    order = OrderStateDataSerializer(read_only=True)
    state = serializers.CharField(read_only=True)
    state_data = StateDataSerializer(read_only=True)
