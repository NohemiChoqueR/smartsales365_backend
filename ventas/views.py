# ventas/views.py
import stripe
from django.conf import settings
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from utils.viewsets import SoftDeleteViewSet
from utils.permissions import ModulePermission
from utils.logging_utils import log_action
from rest_framework.views import APIView
import logging

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

from .models import Metodo_pago, Pago, Venta, DetalleVenta
from .serializers import (
    MetodoPagoSerializer,
    PagoSerializer,
    VentaSerializer,
    DetalleVentaSerializer,
)
from products.models import Producto
from sucursales.models import Sucursal, StockSucursal

# ---------------------------------------------------------------------
# 🔹 ViewSet: Métodos de Pago
# ---------------------------------------------------------------------
class MetodoPagoViewSet(SoftDeleteViewSet):
    queryset = Metodo_pago.objects.all().order_by("nombre")
    serializer_class = MetodoPagoSerializer
    module_name = "MetodoPago"


# ---------------------------------------------------------------------
# 🔹 ViewSet: Pagos
# ---------------------------------------------------------------------
class PagoViewSet(SoftDeleteViewSet):
    queryset = Pago.objects.all().order_by("-fecha")
    serializer_class = PagoSerializer
    module_name = "Pago"


# ---------------------------------------------------------------------
# 🔹 ViewSet: Ventas
# ---------------------------------------------------------------------
class VentaViewSet(SoftDeleteViewSet):
    queryset = Venta.objects.all().order_by("-fecha")
    serializer_class = VentaSerializer
    module_name = "Venta"

    @action(detail=True, methods=["get"], url_path="detalles")
    def obtener_detalles(self, request, pk=None):
        """
        Obtiene los detalles de una venta específica.
        """
        venta = self.get_object()
        detalles = venta.detalles.all()
        serializer = DetalleVentaSerializer(detalles, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"], url_path="registrar")
    def registrar_venta(self, request):
        """
        Permite registrar una nueva venta con sus detalles.
        """
        data = request.data
        user = request.user
        empresa = getattr(user, "empresa", None)

        # Validaciones básicas
        detalles = data.get("detalles", [])
        if not detalles:
            return Response({"detail": "Debe incluir al menos un producto."}, status=400)
        
        sucursal_id = data.get("sucursal")
        try:
            sucursal = Sucursal.objects.get(id=sucursal_id, empresa=empresa)
        except Sucursal.DoesNotExist:
            return Response(
                {"detail": "Sucursal no encontrada o no pertenece a la empresa."},
                status=400
            )
        canal_venta = data.get("canal", "POS") # 'POS' como default si no se envía
        # Crear el pago si viene incluido
        pago_data = data.get("pago")
        pago_instance = None
        if pago_data:
            pago_serializer = PagoSerializer(data=pago_data)
            pago_serializer.is_valid(raise_exception=True)
            pago_instance = pago_serializer.save(empresa=empresa)
            
        # Crear la venta
        venta = Venta.objects.create(
            empresa=empresa,
            usuario=user,
            sucursal=sucursal,
            canal=canal_venta,
            pago=pago_instance,
            total=data.get("total", 0),
            estado=data.get("estado", "pendiente"),
        )

        # Crear los detalles Y ACTUALIZAR STOCK
        for det in detalles:
            producto_id = det.get("producto")
            cantidad = det.get("cantidad")
            precio = det.get("precio_unitario")

            try:
                producto = Producto.objects.get(id=producto_id, empresa=empresa)
            except Producto.DoesNotExist:
                return Response(
                    {"detail": f"Producto ID {producto_id} no encontrado o pertenece a otra empresa."},
                    status=404,
                )

            # ✅ CREAR DETALLE DE VENTA
            DetalleVenta.objects.create(
                empresa=empresa,
                venta=venta,
                producto=producto,
                cantidad=cantidad,
                precio_unitario=precio,
                subtotal=cantidad * float(precio),
            )

            # ✅ ACTUALIZAR STOCK EN LA SUCURSAL ESPECÍFICA
            try:
                stock_item = StockSucursal.objects.get(
                    empresa=empresa,
                    producto=producto,
                    sucursal=sucursal  # ← MISMA SUCURSAL DE LA VENTA
                )
                
                # Verificar que haya suficiente stock
                if stock_item.stock < cantidad:
                    return Response(
                        {"detail": f"Stock insuficiente para {producto.nombre}. Stock disponible: {stock_item.stock}, solicitado: {cantidad}"},
                        status=400
                    )
                
                # Reducir el stock
                stock_item.stock -= cantidad
                stock_item.save()
                
            except StockSucursal.DoesNotExist:
                return Response(
                    {"detail": f"Producto {producto.nombre} no tiene stock registrado en la sucursal {sucursal.nombre}"},
                    status=400
                )

        log_action(
            user=user,
            modulo=self.module_name,
            accion="CREAR",
            descripcion=f"Registró la venta #{venta.numero_nota} por un total de {venta.total} en sucursal {sucursal.nombre}",
            request=request,
        )

        return Response(VentaSerializer(venta).data, status=status.HTTP_201_CREATED)
# ---------------------------------------------------------------------
# 🔹 ViewSet: Detalles de Venta
# ---------------------------------------------------------------------
# ventas/views.py
class DetalleVentaViewSet(SoftDeleteViewSet):
    queryset = DetalleVenta.objects.all().order_by("venta__id")
    serializer_class = DetalleVentaSerializer
    module_name = "DetalleVenta"

    def get_queryset(self):
        qs = super().get_queryset()

        request = self.request
        user = request.user
        empresa = getattr(user, "empresa", None)

        # Siempre filtrar por empresa y ventas entregadas
        if empresa:
            qs = qs.filter(
                empresa=empresa,
                venta__empresa=empresa,
                venta__estado="entregado",
            )

        # Query params
        fecha_inicio = request.query_params.get("fecha_inicio")
        fecha_fin = request.query_params.get("fecha_fin")
        producto_id = request.query_params.get("producto") or request.query_params.get("producto_id")
        categoria_id = request.query_params.get("categoria") or request.query_params.get("categoria_id")

        if fecha_inicio:
            qs = qs.filter(venta__fecha__date__gte=fecha_inicio)
        if fecha_fin:
            qs = qs.filter(venta__fecha__date__lte=fecha_fin)

        if producto_id:
            qs = qs.filter(producto_id=producto_id)

        if categoria_id:
            qs = qs.filter(producto__subcategoria__categoria_id=categoria_id)

        return qs.order_by("venta__fecha")



class CrearStripePaymentIntentView(APIView):

    def post(self, request, *args, **kwargs):
        # 1. Recibimos los productos del carrito (igual que en tu Node.js)
        productos = request.data.get('productos', [])

        if not productos:
            return Response(
                {"error": "No se enviaron productos"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Calculamos el total (¡NUNCA confíes en un total del frontend!)
        try:
            total = sum(
                item['precio'] * item['quantity'] for item in productos
            )
            logger.info(f'Total a pagar: {total}')
        except (KeyError, TypeError):
             return Response(
                 {"error": "Formato de productos inválido"}, 
                 status=status.HTTP_400_BAD_REQUEST
             )

        # 3. Le pedimos a Stripe que prepare la transacción
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=int(total * 100), # Stripe usa centavos (ej: $10.50 son 1050)
                currency='bob', # O 'usd', 'eur', etc.
                automatic_payment_methods={'enabled': True},
            )

            # 4. Le devolvemos la "llave" a React
            return Response({
                'clientSecret': payment_intent.client_secret
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error al crear PaymentIntent de Stripe: {e}")
            return Response(
                {'error': f"Error de pago: {e}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
