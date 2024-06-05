from django.contrib import admin

# Register your models here.
from CORE.models import *

admin.site.register(BybitCurrency)
admin.site.register(BybitAccount)
admin.site.register(RiskEmail)


class P2PItemAdmin(admin.ModelAdmin):
    list_display = ('side', 'item_id', 'get_payment_methods', 'price', 'min_amount')
    list_filter = ('side', 'is_active')


admin.site.register(P2PItem, P2PItemAdmin)

admin.site.register(OrderBuyToken)
admin.site.register(P2POrderMessage)

admin.site.register(Partner)
admin.site.register(Widget)


class CurrencyAdmin(admin.ModelAdmin):
    list_display = ('type', 'name', 'chain', 'address')
    list_filter = ('name', 'chain')


admin.site.register(Currency, CurrencyAdmin)

admin.site.register(InternalCryptoAddress)
admin.site.register(BybitIncomingPayment)


