# cart/views.py
from django.shortcuts import render
from rest_framework import status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from utils.viewsets import SoftDeleteViewSet
from .models import Cart, CartItem
from .serializers import CartSerializer, CartItemSerializer
from rest_framework.decorators import action

class CartViewSet(SoftDeleteViewSet):
    queryset = Cart.objects.all().order_by("-created_at")
    serializer_class = CartSerializer
    module_name = "Cart"

    def create(self, request, *args, **kwargs):
        """
        En lugar de crear duplicados, retorna el carrito activo del usuario
        (o crea uno nuevo).
        """
        user = request.user
        empresa = getattr(user, "empresa", None)
        cart, created = Cart.get_or_create_active(user, empresa=empresa)
        serializer = self.get_serializer(cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)
    
    @action(detail=False, methods=['post'], url_path='clear-active')
    def clear_active_cart(self, request, *args, **kwargs):
        """
        Busca el carrito activo del usuario y elimina todos sus CartItems.
        
        El frontend debe llamar a este endpoint DESPUÉS de que 
        /api/ventas/registrar/ responda con éxito (HTTP 201).
        """
        user = request.user
        empresa = getattr(user, "empresa", None)

        try:
            # 1. Re-utilizamos tu propia lógica para encontrar el carrito activo
            cart, created = Cart.get_or_create_active(user, empresa=empresa)

            if created:
                # Si se 'creó' uno, significa que no había uno activo para limpiar.
                # No es un error, simplemente no hay nada que hacer.
                return Response(status=status.HTTP_204_NO_CONTENT)

            # 2. ESTA ES LA LÍNEA CLAVE:
            # Tu Serializer (CartSerializer) usa 'items' como related_name.
            # Esta línea encuentra todos los CartItem asociados a ese
            # carrito y los borra de la base de datos.
            cart.items.all().delete()

            return Response(
                {"detail": "Carrito limpiado exitosamente."}, 
                status=status.HTTP_200_OK
            )

        except Exception as e:
            return Response(
                {"detail": f"Error al limpiar el carrito: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class CartItemViewSet(SoftDeleteViewSet):
    queryset = CartItem.objects.all()
    serializer_class = CartItemSerializer
    module_name = "CartItem"

    def create(self, request, *args, **kwargs):
        """
        Añade item al carrito. Si el mismo producto ya existe en el carrito,
        incrementa la cantidad y devuelve el item actualizado.
        """
        user = request.user
        cart_id = request.data.get("cart")
        if not cart_id:
            return Response({"detail": "cart es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        cart = get_object_or_404(Cart, pk=cart_id)

        # simple check: el carrito debe pertenecer al usuario
        if cart.usuario != user:
            return Response({"detail": "El carrito no pertenece al usuario."}, status=status.HTTP_403_FORBIDDEN)

        producto_id = request.data.get("producto")
        if not producto_id:
            return Response({"detail": "producto es requerido"}, status=status.HTTP_400_BAD_REQUEST)

        cantidad = int(request.data.get("cantidad", 1))

        existing = CartItem.objects.filter(cart=cart, producto_id=producto_id).first()
        if existing:
            existing.cantidad = existing.cantidad + cantidad
            precio_unitario = request.data.get("precio_unitario", None)
            if precio_unitario is not None:
                existing.precio_unitario = precio_unitario
            existing.save()
            serializer = self.get_serializer(existing)
            return Response(serializer.data, status=status.HTTP_200_OK)

        data = request.data.copy()
        data["cart"] = cart.id
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
