# predictions/apps.py
import os
import sys
import joblib
from django.apps import AppConfig
from django.conf import settings

class PredictionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'predictions'
    
    # --- ¡TRES "CAJONES" CON LOS NOMBRES CORRECTOS! ---
    sales_category_model = None   # Cerebro 1
    demand_product_model = None   # Cerebro 2
    recommendation_model = None # Cerebro 3

    def ready(self):
        if 'runserver' in sys.argv:
            print(f"Iniciando carga de TODOS LOS MODELOS ML (comando 'runserver')...")
            
            # --- CEREBRO 1: VENTAS (Sub)CATEGORÍA ---
            # ¡Buscamos el nombre de archivo CORRECTO!
            PATH_M1 = os.path.join(settings.BASE_DIR, 'ml_models', 'sales_category_model.pkl')
            try:
                PredictionsConfig.sales_category_model = joblib.load(PATH_M1)
                print(f"✅ [Servidor] Modelo 1 (Ventas Categoría) cargado.")
            except Exception as e:
                print(f"⚠️ [Servidor] WARNING (M1): No se cargó 'sales_category_model.pkl': {e}")
            
            # --- CEREBRO 2: DEMANDA POR PRODUCTO ---
            # ¡Buscamos el nombre de archivo CORRECTO!
            PATH_M2 = os.path.join(settings.BASE_DIR, 'ml_models', 'demand_product_model.pkl')
            try:
                PredictionsConfig.demand_product_model = joblib.load(PATH_M2)
                print(f"✅ [Servidor] Modelo 2 (Demanda Producto) cargado.")
            except Exception as e:
                print(f"⚠️ [Servidor] WARNING (M2): No se cargó 'demand_product_model.pkl': {e}")
            
            # --- CEREBRO 3: RECOMENDACIÓN ---
            # ¡Buscamos el nombre de archivo CORRECTO!
            PATH_M3 = os.path.join(settings.BASE_DIR, 'ml_models', 'recommendation_model.pkl')
            try:
                PredictionsConfig.recommendation_model = joblib.load(PATH_M3)
                print(f"✅ [Servidor] Modelo 3 (Recomendación) cargado.")
            except Exception as e:
                print(f"⚠️ [Servidor] WARNING (M3): No se cargó 'recommendation_model.pkl': {e}")
        
        else:
            print(f"... (Carga de modelos ML omitida para el comando: {' '.join(sys.argv)}) ...")