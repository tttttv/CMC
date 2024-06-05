from django.urls import path
from django.conf.urls.static import static
from . import views
from django.conf import settings



from django.urls import path, re_path
from django.conf.urls.static import static
from django.views.generic import TemplateView
from rest_framework import permissions, routers
from . import views
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from drf_yasg import openapi
from drf_yasg.views import get_schema_view
from drf_yasg.generators import OpenAPISchemaGenerator
import os

from django.urls import re_path
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi


class SchemaGenerator(OpenAPISchemaGenerator):
    def get_schema(self, request=None, public=False):
        schema = super(SchemaGenerator, self).get_schema(request, public)
        schema.basePath = os.path.join(schema.basePath, 'api/')
        return schema


schema_view = get_schema_view(
   openapi.Info(
      title="Snippets API",
      default_version='v1',
   ),
   public=True,
   # permission_classes=[permissions.IsAuthenticated,], FIXME
   permission_classes=[permissions.AllowAny,],
   urlconf='API.urls',
   generator_class=SchemaGenerator
)

swagger_urls = [
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    path('docs', TemplateView.as_view(
        template_name='API/docs.html',
        extra_context={'schema_url': 'openapi-schema'}
    ), name='swagger')
]

router = routers.DefaultRouter()
router.register(r'exchange', views.ExchangeVIewSet, basename='exchange')
router.register(r'order', views.OrderViewSet, basename='order')
router.register(r'widget', views.WidgetViewSet, basename='widget')


urlpatterns = [

] + router.urls + swagger_urls
