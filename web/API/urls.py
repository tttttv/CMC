from django.urls import path
from django.conf.urls.static import static
from . import views
from django.conf import settings

urlpatterns = [
    path('get_widget_palette', views.get_widget_palette_view, name='get_widget_palette'),
    path('get_payment_methods', views.get_payment_methods_view, name='get_payment_methods'),
    path('widget', views.create_widget_view, name='create_widget'),
    path('widget_settings', views.get_widget_settings_view, name='widget_setting'),

    path('exchange/from', views.get_available_from_view, name="get_from"),
    path('exchange/to', views.get_available_to_view, name="get_to"),
    path('exchange/price', views.get_price_view, name="get_price"),
    path('order', views.create_order_view, name="order_create"),
    path('order/state', views.get_order_state_view, name="order_state"),
    path('order/cancel', views.cancel_order_view, name="order_cancel"),
    path('order/continue', views.continue_with_new_price, name="order_continue"),
    path('order/paid', views.mark_order_as_paid_view, name="order_paid"),
    path('order/message', views.get_chat_messages_view, name="order_messages"),

    path('order/message/send', views.send_chat_message_view, name="order_message_send"),
    path('order/message/send_image', views.send_chat_image_view, name="order_image_send"),
]