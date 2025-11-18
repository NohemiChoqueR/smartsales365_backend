from django.urls import path
from .views import (
    get_sales_predictions,
    get_dashboard_kpis,
    get_historical_sales_summary,
    get_productos_baja_rotacion,
    get_sales_prediction_range_view,
    get_product_prediction_view,
    get_trends_view,
    get_ia_insights,
    get_insights,
    retrain_model
)

urlpatterns = [
    path("predicciones/", get_sales_predictions),
    path("kpis/", get_dashboard_kpis),
    path("historial/", get_historical_sales_summary),
    path("baja-rotacion/", get_productos_baja_rotacion),
    # ENDPOINTS AVANZADOS
    path("pronostico-rango/", get_sales_prediction_range_view),
    path("prediccion-producto/", get_product_prediction_view),
    path("tendencias/", get_trends_view),
    # path("insights/", get_ia_insights),
    path("insights/", get_insights),
    path("reentrenar/", retrain_model),
]
