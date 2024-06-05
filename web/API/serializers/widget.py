from rest_framework import serializers

from .order import PaymentCurrencySerializer
from CORE.models import *


class WidgetCreateSerializer(serializers.ModelSerializer):
    partner_code = serializers.CharField(source='partner.code', write_only=True)

    withdrawing_token = serializers.CharField()
    withdrawing_chain = serializers.CharField(required=False)
    withdrawing_address = serializers.CharField()

    partner_commission = serializers.FloatField(min_value=0, max_value=1.0)
    platform_commission = serializers.SerializerMethodField(read_only=True)

    hash = serializers.SerializerMethodField(read_only=True)

    def get_partner_commission(self, obj):
        return obj.platform_commission

    def get_partner_commission(self, obj):
        return obj.partner_commission

    def get_hash(self, obj):
        return obj.hash

    class Meta:
        model = Widget
        fields = ('id', 'hash', 'partner_code', 'partner',
                  'withdrawing_currency', 'payment_methods',
                  'withdrawing_token', 'withdrawing_chain', 'withdrawing_address',
                  'partner_commission', 'platform_commission',
                  'email', 'name', 'color_palette', 'redirect_url')
        read_only_fields = ['partner', 'withdrawing_currency', 'payment_methods']

    def create(self, validated_data):
        print('validated_data', validated_data)
        partner = validated_data.pop('partner')
        print('partner', partner)
        try:
            partner = Partner.objects.get(code=partner['code'])
        except Partner.DoesNotExist:
            raise serializers.ValidationError("Partner not found")

        withdrawing_token_id = validated_data.pop('withdrawing_token')
        withdrawing_chain = validated_data.pop('withdrawing_chain', None)
        withdrawing_address = validated_data.pop('withdrawing_address')

        _withdraw_method = BybitCurrency.get_by_token(withdrawing_token_id)
        print('_withdraw_method', _withdraw_method)
        withdraw_currency: Currency = Currency(currency=_withdraw_method)
        withdraw_currency.__dict__.update(_withdraw_method.__dict__)
        withdraw_currency.address = withdrawing_address  # TODO validate

        if withdraw_currency.is_crypto:
            if not withdraw_currency.validate_chain(withdrawing_chain):
                raise serializers.ValidationError("Chain invalid")
            withdraw_currency.chain = withdrawing_chain

        # widget = Widget.objects.create(
        widget=Widget(
            partner=partner,
            withdrawing_currency=withdraw_currency,
            **validated_data)

        if 'payment_methods' in validated_data:  # currency
            for currency_id in validated_data.pop('payment_methods'):
                payment_method = BybitCurrency.get_by_id(currency_id)
                widget.payment_methods.add(payment_method)

        widget.platform_commission = partner.platform_commission

        if 'color_palette' in validated_data:
            input_palette = validated_data.pop('color_palette')
            color_palette = {color: (input_palette[color] if color in input_palette else None)
                             for color in widget.DEFAULT_PALETTE}
            widget.color_palette = color_palette  # else DEFAULT_PALETTE

        widget.withdrawing_currency.save()
        widget.save()
        return widget


class WidgetSettingsSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    address = serializers.CharField(read_only=True)
    chain = serializers.CharField(read_only=True)
    chain_name = serializers.CharField(read_only=True)
    qrcode = serializers.CharField(read_only=True)

    withdraw_method = PaymentCurrencySerializer(read_only=True),
    email = serializers.CharField(read_only=True)
    color_palette = serializers.JSONField(read_only=True)
    payment_methods = PaymentCurrencySerializer(read_only=True, many=True)
