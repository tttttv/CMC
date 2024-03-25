from django.contrib import admin

# Register your models here.
from CORE.models import *

admin.site.register(BybitSettings)
admin.site.register(BybitAccount)
admin.site.register(RiskEmail)

class P2PItemAdmin(admin.ModelAdmin):
    list_display = ('side', 'item_id', 'get_payment_methods', 'price', 'min_amount')
    list_filter = ('side', 'is_active')

admin.site.register(P2PItem, P2PItemAdmin)

admin.site.register(P2POrderBuyToken)
admin.site.register(P2POrderMessage)