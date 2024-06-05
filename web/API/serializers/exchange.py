from rest_framework import serializers
from rest_framework.serializers import Serializer
from CORE.models import *


class GetPriceSerializer(serializers.Serializer):
    payment_method = serializers.IntegerField()
    payment_chain = serializers.CharField(required=False)
    payment_amount = serializers.FloatField()

    withdraw_method = serializers.IntegerField()
    withdraw_chain = serializers.CharField(required=False)
    withdraw_amount = serializers.FloatField()

    anchor = serializers.ChoiceField(required=False, default=OrderBuyToken.ANCHOR_SELL, choices=OrderBuyToken.ANCHORS)

