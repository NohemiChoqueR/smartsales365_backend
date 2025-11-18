# predictions/views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import pandas as pd
from datetime import datetime, timedelta
from django.db.models import Sum
from rest_framework.permissions import AllowAny 
from django.apps import apps 
from .apps import PredictionsConfig # Importamos la "Plantilla"
from django.utils import timezone
from dateutil.relativedelta import relativedelta

# --- Importamos los modelos de la BD ---
try:
    from ventas.models import DetalleVenta
except ImportError:
    DetalleVenta = None
try:
    from products.models import Producto 
except ImportError:
    Producto = None

# ===================================================================
# --- VISTA 1: PREDICCIÓN DE VENTAS 
# ===================================================================
class PredictSalesView(APIView):
    permission_classes = [AllowAny]
    
    # --- ¡CAMBIO AQUÍ! ---
    def get(self, request, subcategoria_id, format=None): 
        model = PredictionsConfig.sales_category_model
        if model is None:
            return Response({"error": "Modelo de Ventas por Categoría no cargado."}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # --- Pistas: ['subcategoria_id', 'mes', 'ventas_mes_anterior'] ---
        hoy = timezone.now()
        mes_actual = hoy.month

        primer_dia_mes_actual = hoy.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        ultimo_dia_mes_pasado = primer_dia_mes_actual - timedelta(seconds=1) 
        primer_dia_mes_pasado = ultimo_dia_mes_pasado.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # --- ¡CAMBIO AQUÍ! ---
        ventas_pasadas = DetalleVenta.objects.filter(
            producto__subcategoria_id=subcategoria_id, # <-- ¡Usamos tu cambio!
            venta__fecha__range=(primer_dia_mes_pasado, ultimo_dia_mes_pasado)
        ).aggregate(total_vendido=Sum('cantidad'))
        
        ventas_mes_anterior = ventas_pasadas.get('total_vendido', 0)
        if ventas_mes_anterior is None: ventas_mes_anterior = 0

        # --- ¡CAMBIO AQUÍ! ---
        data_para_predecir = {
            'subcategoria_id': [subcategoria_id], # <-- ¡Usamos tu cambio!
            'mes': [mes_actual],
            'ventas_mes_anterior': [ventas_mes_anterior]
        }
        columnas_ordenadas = ['subcategoria_id', 'mes', 'ventas_mes_anterior'] # <-- ¡Usamos tu cambio!
        df_predict = pd.DataFrame(data_para_predecir, columns=columnas_ordenadas)

        prediccion_array = model.predict(df_predict)
        prediccion_final = round(prediccion_array[0])

        # --- ¡CAMBIO AQUÍ! ---
        return Response({
            "subcategoria_id": subcategoria_id, # <-- ¡Usamos tu cambio!
            "prediccion_proximo_mes (unidades)": prediccion_final,
            "datos_usados_para_predecir": {
                "mes_actual": mes_actual,
                "ventas_reales_mes_pasado": ventas_mes_anterior
            }
        }, status=status.HTTP_200_OK)

# ===================================================================
# --- VISTA 2: PREDICCIÓN DE DEMANDA POR PRODUCTO 
# ===================================================================
class PredictDemandView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, producto_id, format=None):
        model = PredictionsConfig.demand_product_model
        if model is None:
            return Response({"error": "Modelo de Demanda por Producto no cargado."}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        hoy = datetime.now()
        mes_actual = hoy.month
        semana_actual = hoy.isocalendar().week
        hace_7_dias = hoy - timedelta(days=7)
        
        ventas_pasadas = DetalleVenta.objects.filter(
            producto_id=producto_id,
            venta__fecha__gte=hace_7_dias
        ).aggregate(total_vendido=Sum('cantidad'))
        ventas_semana_anterior = ventas_pasadas.get('total_vendido', 0)
        if ventas_semana_anterior is None: ventas_semana_anterior = 0

        data_para_predecir = {
            'producto_id': [producto_id],
            'mes': [mes_actual],
            'semana_del_anio': [semana_actual],
            'ventas_semana_anterior': [ventas_semana_anterior]
        }
        columnas_ordenadas = ['producto_id', 'mes', 'semana_del_anio', 'ventas_semana_anterior']
        df_predict = pd.DataFrame(data_para_predecir, columns=columnas_ordenadas)

        prediccion_array = model.predict(df_predict)
        prediccion_final = round(prediccion_array[0])

        return Response({
            "producto_id": producto_id,
            "prediccion_proxima_semana (unidades)": prediccion_final,
            "datos_usados_para_predecir": {
                "mes_actual": mes_actual,             
                "semana_actual": semana_actual,      
                "ventas_reales_ultimos_7_dias": ventas_semana_anterior
            }
        }, status=status.HTTP_200_OK)

# ===================================================================
# --- VISTA 3: RECOMENDACIÓN DE PRODUCTOS 
# ===================================================================
class RecommendProductView(APIView):
    permission_classes = [AllowAny]
    
    def get(self, request, producto_id, format=None):
        model = PredictionsConfig.recommendation_model
        
        if model is None:
            return Response({"error": "Modelo de Recomendación no cargado."}, 
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        if Producto is None:
            return Response({"error": "No se pudo importar 'Producto'"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        try:
            otros_productos_ids = list(Producto.objects.exclude(id=producto_id).values_list('id', flat=True))
        except Exception as e:
            return Response({"error": f"Error al buscar productos: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not otros_productos_ids:
            return Response({"error": "No se encontraron otros productos para recomendar."}, status=status.HTTP_404_NOT_FOUND)

        data_para_predecir = {
            'producto_A': [producto_id] * len(otros_productos_ids),
            'producto_B': otros_productos_ids
        }
        df_predict = pd.DataFrame(data_para_predecir)
        
        probabilidades = model.predict_proba(df_predict)
        probabilidad_de_compra_juntos = probabilidades[:, 1]
        
        resultados = zip(otros_productos_ids, probabilidad_de_compra_juntos)
        resultados_ordenados = sorted(resultados, key=lambda x: x[1], reverse=True)
        top_3_recomendaciones_tuplas = resultados_ordenados[:3]
        
        top_3_final = []
        for prod_id, prob in top_3_recomendaciones_tuplas:
            top_3_final.append({
                "producto_id_recomendado": prod_id,
                "probabilidad": f"{prob * 100:.2f}%"
            })

        return Response({
            "producto_consultado": producto_id,
            "recomendaciones": top_3_final
        }, status=status.HTTP_200_OK)