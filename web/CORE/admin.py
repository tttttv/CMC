from django.contrib import admin

# Register your models here.
from CORE.models import *

admin.site.register(BybitCurrency)
admin.site.register(BybitAccount)
admin.site.register(RiskEmail)


class P2PItemAdmin(admin.ModelAdmin):
    list_display = ('side', 'item_id', 'get_payment_methods', 'price', 'min_amount')
    list_filter = ('side', 'is_active')
    search_fields = ('item_id', )


admin.site.register(P2PItem, P2PItemAdmin)


class OrderBuyTokenAdmin(admin.ModelAdmin):
    list_display = ('id', 'email', 'stage', 'state', 'payment_currency', 'withdraw_currency')
    list_filter = ('is_executing', )
    search_fields = ('email', 'hash')


admin.site.register(OrderBuyToken, OrderBuyTokenAdmin)
admin.site.register(P2POrderMessage)

admin.site.register(Partner)
admin.site.register(Widget)


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('type', 'name', 'chain', 'address')
    list_filter = ('name', 'chain')


admin.site.register(Currency, CurrencyAdmin)

admin.site.register(InternalCryptoAddress)
admin.site.register(BybitIncomingPayment)


admin.site.register(Config)

admin.site.register(PaymentTerm)
