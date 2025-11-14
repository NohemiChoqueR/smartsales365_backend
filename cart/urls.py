# cart/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CartViewSet, CartItemViewSet

router = DefaultRouter()
router.register(r'cart', CartViewSet)
router.register(r'cart-item', CartItemViewSet)

urlpatterns = [
    path('', include(router.urls)),
]