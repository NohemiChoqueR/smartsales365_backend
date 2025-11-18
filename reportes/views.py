import json
from decimal import Decimal
from datetime import datetime, date

from django.db import models
from django.db.models import Q, Sum, Count
from django.core.exceptions import FieldDoesNotExist

from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ventas.models import Venta
from products.models import Producto
from users.models import User

from reportes.generators import generar_reporte_pdf, generar_reporte_excel
from reportes.services.llm_interpreter import interpretar_prompt


# ============================================
# CONFIG
# ============================================

DJANGO_LOOKUP_OPERATORS = [
    "exact", "iexact", "contains", "icontains", "in",
    "gt", "gte", "lt", "lte", "isnull", "range",
    "year", "month", "day", "week_day",
    "startswith", "istartswith", "endswith", "iendswith",
]

ALLOWED_AGGREGATIONS = {"Sum": Sum, "Count": Count}


def _parse_simple_date(value):
    """Convierte siempre a solo fecha (sin hora)."""
    if isinstance(value, datetime):
        return value.date()

    if isinstance(value, date):
        return value

    if isinstance(value, str):
        try:
            return datetime.strptime(value, "%Y-%m-%d").date()
        except:
            return value

    return value


def _validate_and_convert_value(model_class, lookup: str, value):
    parts = lookup.split("__")
    current_model = model_class
    field_instance = None

    lookup_op = parts[-1] if parts[-1] in DJANGO_LOOKUP_OPERATORS else "exact"
    field_path_parts = parts[:-1] if lookup_op != "exact" else parts

    for part in field_path_parts:
        try:
            field_instance = current_model._meta.get_field(part)
            if hasattr(field_instance, "related_model") and field_instance.related_model:
                current_model = field_instance.related_model
        except FieldDoesNotExist:
            field_instance = None
            break

    if value is None:
        return None

    if lookup_op == "isnull":
        return bool(value)

    if lookup_op == "range":
        if isinstance(value, list) and len(value) == 2:
            return [_parse_simple_date(value[0]), _parse_simple_date(value[1])]
        return value

    if lookup_op == "in":
        return value

    if field_instance:
        ftype = type(field_instance)

        if ftype in (models.DecimalField, models.FloatField):
            return Decimal(str(value))

        if ftype == models.IntegerField:
            return int(value)

        if ftype in (models.DateField, models.DateTimeField):
            return _parse_simple_date(value)

        if ftype == models.BooleanField:
            return str(value).lower() == "true"

    return value


def _build_queryset_from_interpretacion(user, interpretacion):
    tipo = interpretacion.get("tipo_reporte")
    filtros_dict = interpretacion.get("filtros", {})
    agrupacion = interpretacion.get("agrupacion", [])
    calculos = interpretacion.get("calculos", {})
    orden = interpretacion.get("orden", [])

    empresa = getattr(user, "empresa", None)
    if not empresa:
        raise ValueError("El usuario no tiene empresa asignada.")

    if tipo == "ventas":
        ModelClass = Venta
        qs = Venta.objects.filter(empresa=empresa)\
            .select_related("usuario", "sucursal")\
            .prefetch_related("detalles__producto")

    elif tipo == "productos":
        ModelClass = Producto
        qs = Producto.objects.filter(empresa=empresa, esta_activo=True)\
            .select_related("marca", "subcategoria__categoria")

    elif tipo == "usuarios":
        ModelClass = User
        qs = User.objects.filter(empresa=empresa, esta_activo=True)

    else:
        raise ValueError(f"tipo_reporte '{tipo}' no soportado.")

    qf = Q()

    for lookup, raw_value in filtros_dict.items():
        if raw_value in ("", None, [], {}):
            continue

        try:
            cv = _validate_and_convert_value(ModelClass, lookup, raw_value)
            qf &= Q(**{lookup: cv})
        except Exception as e:
            print(f"[WARN] Filtro inválido ignorado {lookup}={raw_value} ({e})")
            continue

    qs = qs.filter(qf)

    hubo_agrup = False

    if agrupacion:
        hubo_agrup = True
        qs = qs.values(*agrupacion)

        if calculos:
            anot = {}
            for alias, spec in calculos.items():
                func = ALLOWED_AGGREGATIONS.get(spec.get("funcion"))
                campo = spec.get("campo")
                if func and campo:
                    anot[alias] = func(campo)
            qs = qs.annotate(**anot)

    if orden:
        qs = qs.order_by(*orden)
    else:
        qs = qs.order_by("-fecha" if tipo == "ventas" else "nombre")

    return qs, tipo, hubo_agrup


# ============================================
# 1. GENERAR REPORTE IA
# ============================================

class GenerarReporteView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):

        prompt = request.data.get("prompt", "")
        formato_manual = request.data.get("formato_manual")

        if not prompt:
            return Response({"error": "Debe enviar prompt."}, status=400)

        interpretacion = interpretar_prompt(prompt)
        print("🔍 INTERPRETACION:", interpretacion)
        if interpretacion.get("error"):
            return Response({"error": interpretacion["error"]}, status=400)

        try:
            qs, tipo, hubo_agrup = _build_queryset_from_interpretacion(request.user, interpretacion)
        except Exception as e:
            print("[ERROR SQL]:", e)
            return Response({"error": "Error construyendo datos."}, status=500)

        if not hubo_agrup:

            if tipo == "ventas":
                fields = [
                    "id", "numero_nota", "fecha", "total",
                    "estado", "canal",
                    "usuario__email", "usuario__nombre", "usuario__apellido",
                    "sucursal__nombre"
                ]

            elif tipo == "productos":
                fields = [
                    "id", "nombre", "sku", "precio_venta",
                    "marca__nombre", "subcategoria__nombre",
                    "subcategoria__categoria__nombre",
                ]

            elif tipo == "usuarios":
                fields = [
                    "id", "email", "nombre", "apellido",
                    "telefono", "role__name", "empresa__nombre",
                ]

            data = list(qs.values(*fields))

        else:
            data = list(qs)

        interpretacion["tipo_reporte"] = tipo

        if formato_manual == "pdf":

            if len(data) == 0:
                columnas = ["Sin datos"]
                filas = [["No hay resultados"]]
            else:
                columnas = list(data[0].keys())
                filas = [[str(item.get(c, "")) for c in columnas] for item in data]

            titulo = interpretacion.get("prompt", "Reporte IA")
            return generar_reporte_pdf("reporte_ia", titulo, columnas, filas)

        if formato_manual == "excel":
            return generar_reporte_excel(data, interpretacion)

        return Response(data, status=200)


# ============================================
# 2. EXPORTACIÓN MANUAL DESDE FRONT
# ============================================

class ExportarDatosView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        data = request.data.get("data")
        formato = request.data.get("formato")
        titulo = request.data.get("titulo", "Reporte IA")

        if not isinstance(data, list):
            return Response({"error": "Debe enviar data como lista"}, status=400)

        if formato not in ["pdf", "excel"]:
            return Response({"error": "Formato inválido"}, status=400)

        if formato == "pdf":

            if len(data) == 0:
                columnas = ["Sin datos"]
                filas = [["No hay resultados"]]
            else:
                columnas = list(data[0].keys())
                filas = [[str(item.get(c, "")) for c in columnas] for item in data]

            return generar_reporte_pdf("reporte_manual", titulo, columnas, filas)

        interpretacion = {"prompt": titulo, "tipo_reporte": "manual"}
        return generar_reporte_excel(data, interpretacion)
