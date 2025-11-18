# products/serializers.py
from rest_framework import serializers
from sucursales.models import Sucursal


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


class MarcaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.SerializerMethodField()

    class Meta:
        model = Marca
        fields = ["id", "nombre", "descripcion", "pais_origen", "esta_activo", "empresa", "empresa_nombre"]

    def get_empresa_nombre(self, obj):
        return obj.empresa.nombre if obj.empresa else None


class SubCategoriaSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="categoria.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = SubCategoria
        fields = ["id", "nombre", "descripcion", "esta_activo", "categoria", "categoria_nombre", "empresa", "empresa_nombre"]

    def validate(self, data):
        """
        Asegura que la subcategoría pertenezca a la misma empresa que la categoría.
        """
        categoria = data.get("categoria")
        empresa = data.get("empresa")
        if categoria and empresa and categoria.empresa != empresa:
            raise serializers.ValidationError("La subcategoría debe pertenecer a la misma empresa que la categoría.")
        return data
        
    # def to_representation(self, instance):

    #     representation = super().to_representation(instance)
    #     representation['categoria'] = instance.categoria.nombre
    #     return representation


class CategoriaSerializer(serializers.ModelSerializer): # <-- MODIFICADO
    """
    Nivel 1: Ej. "ELECTROHOGAR".
    """
    subcategorias = SubCategoriaSerializer(many=True, read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    class Meta:
        model = Categoria
        fields = ["id", "nombre", "descripcion", "esta_activo", "empresa", "empresa_nombre", "subcategorias"]


class ImagenProductoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    class Meta:
        model = ImagenProducto
        fields = ["id", "producto", "producto_nombre", "url", "descripcion", "esta_activo", "empresa", "empresa_nombre"]


class DetalleProductoSerializer(serializers.ModelSerializer): # <-- CAMBIADO
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    class Meta:
        model = DetalleProducto
        # "Ficha Técnica"
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "potencia",
            "velocidades",
            "voltaje",
            "aire_frio",
            "tecnologias",
            "largo_cable",
            "esta_activo",
            "empresa",
            "empresa_nombre",
        ]

class ProductoSerializer(serializers.ModelSerializer):
    detalle = DetalleProductoSerializer(read_only=True)
    imagenes = ImagenProductoSerializer(many=True, read_only=True)
    marca_nombre = serializers.CharField(source="marca.nombre", read_only=True)
    subcategoria_nombre = serializers.CharField(source="subcategoria.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    descuento = serializers.SerializerMethodField()
    class Meta:
        model = Producto
        fields = [
            "id",
            "nombre",
            "sku",
            "precio_venta",
            "descripcion",
            "marca",
            "marca_nombre",
            "subcategoria",
            "subcategoria_nombre",
            "fecha_creacion",
            "esta_activo",
            "empresa",
            "empresa_nombre",
            "detalle",
            "imagenes",
            'descuento'
        ]
    
    def get_descuento(self, obj):
        """
        Método para obtener el descuento del producto si existe
        """
        descuento = Descuento.objects.filter(producto=obj, esta_activo=True).first()
        if descuento:
            return DescuentoSerializer(descuento).data
        return None  

    def validate(self, data):
        """
        Valida que el producto, la marca y la subcategoría sean de la misma empresa.
        """
        empresa = data.get("empresa")
        marca = data.get("marca")
        subcategoria = data.get("subcategoria")

        if marca and empresa and marca.empresa != empresa:
            raise serializers.ValidationError("La marca pertenece a otra empresa.")
        if subcategoria and empresa and subcategoria.empresa != empresa:
            raise serializers.ValidationError("La subcategoría pertenece a otra empresa.")

        return data
    
    def to_representation(self, instance):

        representation = super().to_representation(instance)
        if instance.marca:
            representation['marca'] = instance.marca.nombre
        if instance.subcategoria:
            representation['subcategoria'] = str(instance.subcategoria)
        return representation


class CampaniaSerializer(serializers.ModelSerializer):
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    class Meta:
        model = Campania
        fields = ["id", "nombre", "descripcion", "fecha_inicio", "fecha_fin", "esta_activo", "empresa", "empresa_nombre"]


class DescuentoSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    sucursal_nombre = serializers.CharField(source="sucursal.nombre", read_only=True)
    campania_nombre = serializers.CharField(source="campania.nombre", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)

    class Meta:
        model = Descuento
        fields = [
            "id",
            "nombre",
            "tipo",
            "monto",
            "porcentaje",
            "producto",
            "producto_nombre",
            "sucursal",
            "sucursal_nombre",
            "campania",
            "campania_nombre",
            "esta_activo",
            "empresa",
            "empresa_nombre",
        ]

    def validate(self, data):
        """
        Valida coherencia entre tipo, monto y porcentaje, y la empresa de las relaciones.
        """
        tipo = data.get("tipo")
        monto = data.get("monto")
        porcentaje = data.get("porcentaje")
        producto = data.get("producto")
        sucursal = data.get("sucursal")
        empresa = data.get("empresa")

        # --- Validación de tipo de descuento
        if tipo == "PORCENTAJE":
            if porcentaje is None:
                raise serializers.ValidationError("Debe especificar un porcentaje para un descuento porcentual.")
            data["monto"] = None
        elif tipo == "MONTO":
            if monto is None:
                raise serializers.ValidationError("Debe especificar un monto fijo para un descuento de tipo MONTO.")
            data["porcentaje"] = None

        # --- Validación de pertenencia a la misma empresa
        if producto and empresa and producto.empresa != empresa:
            raise serializers.ValidationError("El producto pertenece a otra empresa.")
        if sucursal and empresa and sucursal.empresa != empresa:
            raise serializers.ValidationError("La sucursal pertenece a otra empresa.")

        return data
