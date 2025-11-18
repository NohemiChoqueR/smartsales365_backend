# reportes/urls.py
from django.urls import path
from .views import GenerarReporteView, ExportarDatosView

urlpatterns = [
    path("generar/", GenerarReporteView.as_view(), name="reportes-generar"),
    path("exportar/", ExportarDatosView.as_view(), name="reportes-exportar"),
]
