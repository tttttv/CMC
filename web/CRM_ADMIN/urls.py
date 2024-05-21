from django.urls import path
from django.conf.urls.static import static
from . import views
from django.conf import settings

urlpatterns = [
    path('auth', views.auth_view, name="auth"),
    path('', views.index_view, name='index'),
    path('items', views.items_view, name='items'),
    path('whitelist', views.whitelist_view, name='whitelist'),
    path('management', views.management_view, name='management'),
]