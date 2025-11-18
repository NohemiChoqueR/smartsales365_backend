# prediccion/serializers.py
from rest_framework import serializers

class ProductoBajaRotacionSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nombre = serializers.CharField()
    marca = serializers.CharField()
    stock = serializers.IntegerField()
    imagen_url = serializers.CharField()
    total_vendido = serializers.IntegerField()
