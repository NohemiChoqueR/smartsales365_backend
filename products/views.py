# products/views.py
from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from datetime import timedelta
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated, AllowAny # Importado
from django.db.models import Q
from .nlp_parser import parse_natural_query
from rest_framework.views import APIView

from .models import (
    Marca,
    Categoria,
    SubCategoria,
    Producto,
    DetalleProducto,
    ImagenProducto,
    Descuento,
    Campania,
)
from .serializers import (
    MarcaSerializer,
    CategoriaSerializer,
    SubCategoriaSerializer, 
    ProductoSerializer,
    DetalleProductoSerializer,
    ImagenProductoSerializer,
    DescuentoSerializer,
    CampaniaSerializer,
)
from utils.permissions import ModulePermission
from utils.viewsets import SoftDeleteViewSet

# ---
# NOTA: Asumo que todos estos modelos (Marca, Categoria, etc.)
# tienen un campo 'empresa' y 'esta_activo'
# ---

class MarcaViewSet(SoftDeleteViewSet):
    permission_classes = [AllowAny]
    queryset = Marca.objects.all().order_by('nombre')
    serializer_class = MarcaSerializer
    module_name = "Marca"

    # --- CAMBIO AQUÍ ---
    def get_queryset(self):
        queryset = Marca.objects.all() # Base
        if self.request.user and self.request.user.is_authenticated:
            return queryset.filter(empresa=self.request.user.empresa, esta_activo=True)
        # Filtro público para la empresa 1
        return queryset.filter(empresa_id=1, esta_activo=True)

class CategoriaViewSet(SoftDeleteViewSet):
    permission_classes = [AllowAny]
    queryset = Categoria.objects.all().order_by('nombre')
    serializer_class = CategoriaSerializer
    module_name = "Categoria"

    # --- CAMBIO AQUÍ ---
    def get_queryset(self):
        queryset = Categoria.objects.all() # Base
        if self.request.user and self.request.user.is_authenticated:
            return queryset.filter(empresa=self.request.user.empresa, esta_activo=True)
        # Filtro público para la empresa 1
        return queryset.filter(empresa_id=1, esta_activo=True)

class SubCategoriaViewSet(SoftDeleteViewSet): 
    permission_classes = [AllowAny]
    queryset = SubCategoria.objects.all().order_by('categoria__nombre', 'nombre')
    serializer_class = SubCategoriaSerializer
    module_name = "SubCategoria"

    # --- CAMBIO AQUÍ ---
    def get_queryset(self):
        queryset = SubCategoria.objects.all() # Base
        if self.request.user and self.request.user.is_authenticated:
            return queryset.filter(empresa=self.request.user.empresa, esta_activo=True)
        # Filtro público para la empresa 1
        return queryset.filter(empresa_id=1, esta_activo=True)

class ProductoViewSet(SoftDeleteViewSet):
    queryset = Producto.objects.all().order_by('nombre')
    serializer_class = ProductoSerializer
    module_name = "Producto"
    permission_classes = [AllowAny]

    def get_queryset(self):
        # Empresa actual
        if self.request.user and self.request.user.is_authenticated:
            qs = Producto.objects.filter(
                empresa=self.request.user.empresa,
                esta_activo=True
            )
        else:
            qs = Producto.objects.filter(
                empresa_id=1,
                esta_activo=True
            )

        # ================================
        # 🔥 FILTRO POR CATEGORIA (NIVEL 1)
        # ================================
        categoria = self.request.query_params.get("categoria")
        if categoria:
            qs = qs.filter(subcategoria__categoria_id=categoria)

        # ================================
        # 🔥 FILTRO POR SUBCATEGORIA (NIVEL 2)
        # ================================
        subcategoria = self.request.query_params.get("subcategoria")
        if subcategoria:
            qs = qs.filter(subcategoria_id=subcategoria)

        # ================================
        # 🔥 FILTRO POR MARCA
        # ================================
        marca = self.request.query_params.get("marca")
        if marca:
            qs = qs.filter(marca_id=marca)

        # ================================
        # 🔥 FILTRO POR NOMBRE
        # ================================
        nombre = self.request.query_params.get("nombre")
        if nombre:
            qs = qs.filter(nombre__icontains=nombre)

        return qs.order_by("nombre")

class DetalleProductoViewSet(SoftDeleteViewSet):
    queryset = DetalleProducto.objects.all()
    serializer_class = DetalleProductoSerializer
    module_name = "DetalleProducto"
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = DetalleProducto.objects.all() # Correcto
        if self.request.user and self.request.user.is_authenticated:
            return queryset.filter(producto__empresa=self.request.user.empresa)
        # Filtro público para la empresa 1
        return queryset.filter(producto__empresa_id=1, producto__esta_activo=True) # Correcto

class ImagenProductoViewSet(SoftDeleteViewSet): 
    permission_classes = [AllowAny]
    queryset = ImagenProducto.objects.all()
    serializer_class = ImagenProductoSerializer
    module_name = "ImagenProducto"

    # --- CAMBIO AQUÍ ---
    def get_queryset(self):
        queryset = ImagenProducto.objects.all() # Base
        if self.request.user and self.request.user.is_authenticated:
            # Asumo que se filtra a través del producto
            return queryset.filter(producto__empresa=self.request.user.empresa)
        # Filtro público para la empresa 1
        return queryset.filter(producto__empresa_id=1, producto__esta_activo=True)


class CampaniaViewSet(SoftDeleteViewSet):
    permission_classes = [AllowAny]
    queryset = Campania.objects.all()
    serializer_class = CampaniaSerializer
    module_name = "Campania"

    # --- CAMBIO AQUÍ ---
    def get_queryset(self):
        queryset = Campania.objects.all() # Base
        if self.request.user and self.request.user.is_authenticated:
            return queryset.filter(empresa=self.request.user.empresa, esta_activo=True)
        # Filtro público para la empresa 1
        return queryset.filter(empresa_id=1, esta_activo=True)

class DescuentoViewSet(SoftDeleteViewSet):
    permission_classes = [AllowAny]
    queryset = Descuento.objects.all()
    serializer_class = DescuentoSerializer
    module_name = "Descuento"
    
    # --- CAMBIO AQUÍ ---
    def get_queryset(self):
        queryset = Descuento.objects.all() # Base
        if self.request.user and self.request.user.is_authenticated:
            return queryset.filter(empresa=self.request.user.empresa, esta_activo=True)
        # Filtro público para la empresa 1
        return queryset.filter(empresa_id=1, esta_activo=True)
    

class BuscarProductoNLPView(APIView):
    permission_classes = [AllowAny] # Correcto
    """
    Recibe un prompt de texto, lo interpreta con Gemini (Retail),
    y devuelve una lista de productos que coinciden.
    """
    def post(self, request, *args, **kwargs):
        
        prompt = request.data.get('prompt', '')
        if not prompt:
            return Response({"error": "No se proporcionó un 'prompt' de texto."}, status=400)

        # 1. Llamar al "Intérprete" de Productos (El nuevo)
        parsed_json = parse_natural_query(prompt)
        
        if "error" in parsed_json:
            return Response(parsed_json, status=500)

        # --- CAMBIO AQUÍ ---
        # Determinar la empresa ANTES de hacer la consulta
        empresa_a_filtrar = 1  # Por defecto es 1 (público)
        if request.user and request.user.is_authenticated:
            # Asumo que el ID de la empresa está en request.user.empresa_id
            # o puedes usar request.user.empresa.id
            empresa_a_filtrar = request.user.empresa_id 

        # 2. Construir el Filtro (Query)
        queryset = Producto.objects.filter(
            empresa_id=empresa_a_filtrar, # <-- USAMOS LA VARIABLE
            esta_activo=True
        )
        
        # --- ¡FILTROS MEJORADOS! ---
        
        # Filtro de Nombre (si existe)
        if parsed_json.get('nombre_producto'):
            queryset = queryset.filter(
                nombre__icontains=parsed_json['nombre_producto']
            )
        
        # (El resto de tus filtros están bien y no necesitan cambios)
        ...
        
        # 3. Serializar y Devolver los Resultados
        productos_encontrados = queryset.distinct()[:50]
        
        serializer = ProductoSerializer(productos_encontrados, many=True)
        return Response(serializer.data)