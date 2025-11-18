"""
URL configuration for smartsales project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# smartsales/urls.py
from django.contrib import admin
from django.urls import path, include
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from django.conf import settings
from users.mobile_urls import urlpatterns as mobile_urls_auth 
from django.conf.urls.static import static
schema_view = get_schema_view(
   openapi.Info(
      title="SmartSales365 API",
      default_version='v1',
      description="Sistema de Gestión Comercial Inteligente para electrodomésticos",
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email="contact@smartsales365.local"),
      license=openapi.License(name="BSD License"),
   ),
   public=True,
   permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls),

    # API grouped
    # path('api/', include([
    #     path('', include('users.urls')),
    #     # path('products/', include('products.urls')),
    #     # path('sales/', include('sales.urls')),
    # ])),
    path('api/', include('users.urls')),
    path('api/users/', include(mobile_urls_auth)),

    path('api/', include('products.urls')),
    path('api/', include('sucursales.urls')),
    path('api/', include('shipping.urls')),
    path("api/", include('notifications.urls')),
    # path("api/", include(productos_urls)),
    path("api/", include('ventas.urls')),
    path("api/", include('cart.urls')),
    path("api/", include('notifications.urls')),
    path("api/predict/", include('predictions.urls')),
    path("api/prediccion/", include("prediccion.urls")),
    
    path("api/reportes/", include("reportes.urls")),
    path("api/reports/", include('reports.urls')),
    # swagger / redoc
    path(r'swagger(<format>\.json|\.yaml)', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('api-docs/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]+ static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
