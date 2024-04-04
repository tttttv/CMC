from django.urls import path
from django.conf.urls.static import static
from . import views
from django.conf import settings

urlpatterns = [
    path('widget', views.create_widget_view, name='create_widget'),
    path('exchange/from', views.get_avalible_from_view, name="get_from"),
    path('exchange/to', views.get_avalible_to_view, name="get_to"),
    path('exchange/price', views.get_price_view, name="get_price"),
    path('order', views.create_order_view, name="order_create"),
    path('order/state', views.get_order_state_view, name="order_state"),
    path('order/cancel', views.cancel_order_view, name="order_cancel"),
    path('order/paid', views.mark_order_as_paid_view, name="order_paid"),
    path('order/message', views.get_chat_messages_view, name="order_messages"),
    path('order/message/send', views.send_chat_message_view, name="order_message_send"),
]