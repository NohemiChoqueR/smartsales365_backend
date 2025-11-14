# cart/serializers.py
from rest_framework import serializers
from .models import Cart, CartItem

class CartItemSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = CartItem
        fields = [
            "id",
            "cart",
            "producto",
            "producto_nombre",
            "cantidad",
            "precio_unitario",
            "subtotal",
            "empresa",
        ]
        read_only_fields = ["subtotal", "producto_nombre", "empresa"]

    def get_subtotal(self, obj):
        try:
            return obj.cantidad * obj.precio_unitario
        except:
            return 0


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    usuario_email = serializers.CharField(source="usuario.email", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    total = serializers.SerializerMethodField()
    cantidad_items = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "usuario",
            "usuario_email",
            "empresa",
            "empresa_nombre",
            "created_at",
            "estado",
            "total",
            "cantidad_items",
            "items",
        ]
        read_only_fields = ["items", "created_at", "usuario_email", "empresa_nombre"]

    def get_total(self, obj):
        return obj.total

    def get_cantidad_items(self, obj):
        return obj.cantidad_items