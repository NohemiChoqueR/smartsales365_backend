# prediccion/views.py
from django.shortcuts import render

# Create your views here.
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone
from django.db.models import Sum, Count, Q, F
from datetime import datetime, timedelta

from ventas.models import Venta, DetalleVenta
from products.models import Producto, SubCategoria
from .ml_service import (
    get_sales_prediction,
    train_sales_model,
    get_sales_prediction_range,
    get_product_prediction,
    get_global_trends 
)
from .serializers import ProductoBajaRotacionSerializer
# from usuario.permissions import IsAdminOrVendedor


# ============================================================
# ░█▀█░█▀█░█▀▀░█▀▄░▀█▀░█▀▀░█▀▀
# ========== PREDICCIÓN IA (DASHBOARD) ========================
# ============================================================

# @api_view(["GET"])
# # @permission_classes([IsAdminOrVendedor])
# def get_sales_predictions(request):
#     empresa = request.user.empresa

#     try:
#         dias = int(request.query_params.get("dias", 30))
#     except:
#         return Response({"error": "El parámetro 'dias' debe ser numérico."}, 400)

#     predictions, metadata = get_sales_prediction(empresa, dias)

#     if metadata is None:
#         trained = train_sales_model(empresa)
#         if not trained:
#             return Response({"error": "No hay datos suficientes."}, 404)

#         predictions, metadata = get_sales_prediction(empresa, dias)

#     rmse = round(metadata.get("rmse", 0), 2)

#     metadata["interpretacion"] = (
#         f"El modelo tiene un error promedio de +/- {rmse} Bs. "
#         "Predice usando solo fechas, no considera promociones ni tendencias externas."
#     )

#     return Response({
#         "predicciones": predictions,
#         "metadata": metadata
#     })

# ============================================================
# ░█─░█░█▀█░▀█▀░█▀█░█▀█░█▀▄░█▀▀
# =============== KPIs =======================================
# ============================================================

@api_view(["GET"])
# @permission_classes([IsAdminOrVendedor])
def get_dashboard_kpis(request):
    empresa = request.user.empresa
    hoy = timezone.now().date()

    try:
        ventas_validas = Venta.objects.filter(
            empresa=empresa,
            estado="entregado"   # <-- tu estado real
        )

        total_historico = ventas_validas.aggregate(sum=Sum("total"))["sum"] or 0

        total_hoy = ventas_validas.filter(
            fecha__date=hoy
        ).aggregate(sum=Sum("total"))["sum"] or 0

        total_productos = Producto.objects.filter(
            empresa=empresa,
            esta_activo=True
        ).count()

        total_ordenes = ventas_validas.count()

        return Response({
            "total_historico_bs": float(round(total_historico, 2)),
            "total_hoy_bs": float(round(total_hoy, 2)),
            "total_productos": total_productos,
            "total_ordenes": total_ordenes
        })

    except Exception as e:
        return Response({"error": str(e)}, status=500)

# ============================================================
# ░█░█░█▀▀░█▀▄░█▀█░█▀█░▀█▀░▄▀█░█░░░█▀▀
# ========== HISTORIAL DE VENTAS =============================
# ============================================================

@api_view(["GET"])
def get_historical_sales_summary(request):
    from datetime import datetime, timedelta
    from django.db.models.functions import TruncMonth, TruncDay
    from django.db.models import Sum, Count

    empresa = request.user.empresa

    fecha_inicio = request.query_params.get("fecha_inicio")
    fecha_fin = request.query_params.get("fecha_fin")

    producto_id = request.query_params.get("producto") or request.query_params.get("producto_id")
    subcategoria_id = request.query_params.get("subcategoria") or request.query_params.get("subcategoria_id")
    categoria_id = request.query_params.get("categoria") or request.query_params.get("categoria_id")

    # -------------------------
    # 1. QUERY BASE
    # -------------------------
    qs = Venta.objects.filter(
        empresa=empresa,
        estado="entregado",
    )

    # -------------------------
    # 2. FILTROS FECHAS
    # -------------------------
    if fecha_inicio:
        qs = qs.filter(fecha__date__gte=fecha_inicio)
    if fecha_fin:
        qs = qs.filter(fecha__date__lte=fecha_fin)

    # -------------------------
    # 3. FILTROS PRODUCTO / CATEGORÍA
    # -------------------------
    if producto_id:
        qs = qs.filter(detalles__producto_id=producto_id)

    if subcategoria_id:
        qs = qs.filter(detalles__producto__subcategoria_id=subcategoria_id)

    if categoria_id:
        qs = qs.filter(detalles__producto__subcategoria__categoria_id=categoria_id)

    # -------------------------
    # 4. DEFINIR SI AGRUPAR DÍA O MES
    # -------------------------
    if fecha_inicio and fecha_fin:
        rango_dias = (
            datetime.strptime(fecha_fin, "%Y-%m-%d")
            - datetime.strptime(fecha_inicio, "%Y-%m-%d")
        ).days
        agrupar_por_dia = rango_dias <= 90
    else:
        agrupar_por_dia = False

    trunc = TruncDay("fecha") if agrupar_por_dia else TruncMonth("fecha")
    formato = "%Y-%m-%d" if agrupar_por_dia else "%Y-%m"

    # -------------------------
    # 5. CONSULTA AGRUPADA REAL
    # -------------------------
    qs = qs.annotate(periodo=trunc).values("periodo").annotate(
        total_ventas=Sum("total"),
        numero_ventas=Count("id")
    ).order_by("periodo")

    ventas_dict = {
        item["periodo"].strftime(formato): {
            "total_vendido": float(item["total_ventas"]),
            "numero_ventas": item["numero_ventas"]
        }
        for item in qs
    }

    # -------------------------
    # 6. RELLENAR MESES / DÍAS VACÍOS
    # -------------------------
    resultado = []

    inicio = datetime.strptime(fecha_inicio, "%Y-%m-%d")
    fin = datetime.strptime(fecha_fin, "%Y-%m-%d")

    cursor = inicio

    while cursor <= fin:
        clave = cursor.strftime(formato)

        resultado.append({
            "periodo": clave,
            "total_vendido": ventas_dict.get(clave, {}).get("total_vendido", 0),
            "numero_ventas": ventas_dict.get(clave, {}).get("numero_ventas", 0)
        })

        # avanzar día o mes
        if agrupar_por_dia:
            cursor += timedelta(days=1)
        else:
            # sumar 1 mes correctamente
            if cursor.month == 12:
                cursor = cursor.replace(year=cursor.year + 1, month=1)
            else:
                cursor = cursor.replace(month=cursor.month + 1)

    return Response(resultado)

# def get_historical_sales_summary(request):
#     empresa = request.user.empresa

#     fecha_inicio = request.query_params.get("fecha_inicio")
#     fecha_fin = request.query_params.get("fecha_fin")
#     producto_id = request.query_params.get("producto_id")
#     subcategoria_id = request.query_params.get("subcategoria_id")

#     qs = Venta.objects.filter(
#         empresa=empresa,
#         estado="entregado",
#     )

#     # ----- Filtros -----
#     if fecha_inicio:
#         qs = qs.filter(fecha__date__gte=fecha_inicio)
#     if fecha_fin:
#         qs = qs.filter(fecha__date__lte=fecha_fin)
#     if producto_id:
#         qs = qs.filter(detalles__producto_id=producto_id)
#     if subcategoria_id:
#         qs = qs.filter(detalles__producto__subcategoria_id=subcategoria_id)

#     # ----- Agrupación automática -----
#     if fecha_inicio and fecha_fin:
#         rango_dias = (
#             datetime.strptime(fecha_fin, "%Y-%m-%d") -
#             datetime.strptime(fecha_inicio, "%Y-%m-%d")
#         ).days
#         agrupar_por_dia = rango_dias <= 90
#     else:
#         agrupar_por_dia = False

#     from django.db.models.functions import TruncMonth, TruncDay

#     trunc = TruncDay("fecha") if agrupar_por_dia else TruncMonth("fecha")
#     formato = "%Y-%m-%d" if agrupar_por_dia else "%Y-%m"

#     qs = qs.annotate(periodo=trunc).values("periodo").annotate(
#         total_ventas=Sum("total"),
#         numero_ventas=Count("id")
#     ).order_by("periodo")

#     data = [
#         {
#             "periodo": item["periodo"].strftime(formato),
#             "total_vendido": float(item["total_ventas"]),
#             "numero_ventas": item["numero_ventas"]
#         }
#         for item in qs
#     ]

#     return Response(data)

# ============================================================
# ░█▀█░█▀▀░█▀█░█▀█░█▀█░█▀█░█▄█░▀█▀░█▀█░█▀█░█▀▄░█▀▀
# =============== BAJA ROTACIÓN ===============================
# ============================================================

@api_view(["GET"])
# @permission_classes([IsAdminOrVendedor])
# @api_view(["GET"])
def get_productos_baja_rotacion(request):
    empresa = request.user.empresa

    limite = int(request.query_params.get("limite", 10))
    periodo_dias = int(request.query_params.get("periodo", 90))

    fecha_inicio = timezone.now() - timedelta(days=periodo_dias)

    categoria = request.query_params.get("categoria")
    producto = request.query_params.get("producto")

    productos = Producto.objects.filter(
        empresa=empresa,
        esta_activo=True
    )

    if categoria:
        productos = productos.filter(subcategoria__categoria_id=categoria)

    if producto:
        productos = productos.filter(id=producto)

    productos = productos.annotate(
        total_vendido=Sum(
            "detalles_venta__cantidad",
            filter=Q(
                detalles_venta__venta__empresa=empresa,
                detalles_venta__venta__estado="entregado",
                detalles_venta__venta__fecha__gte=fecha_inicio
            )
        )
    ).order_by("total_vendido", "id")[:limite]

    data = []
    for p in productos:
        imagen = p.imagenes.first().url.url if p.imagenes.exists() else ""

        data.append({
            "id": p.id,
            "nombre": p.nombre,
            "marca": p.marca.nombre if p.marca else "",
            "stock": p.detalles_venta.count(),
            "imagen_url": imagen,
            "total_vendido": p.total_vendido or 0
        })

    return Response(data)


@api_view(["GET"])
def get_sales_predictions(request):
    empresa = request.user.empresa

    print("🔍 REQ PARAMS:", dict(request.query_params))

    # ===========================
    # 1️⃣ CAPTURA DE PARÁMETROS
    # ===========================
    try:
        dias = int(request.query_params.get("dias", 30))
    except:
        return Response({"error": "El parámetro 'dias' debe ser numérico."}, 400)

    categoria_id = request.query_params.get("categoria") or None
    producto_id = request.query_params.get("producto") or None

    # Normalizar valores vacíos
    if categoria_id == "" or categoria_id == "null":
        categoria_id = None
    if producto_id == "" or producto_id == "null":
        producto_id = None

    print(f"➡ Filtros aplicados: dias={dias}, categoria={categoria_id}, producto={producto_id}")

    # ===========================
    # 2️⃣ OBTENER PREDICCIONES
    # ===========================
    predictions, metadata = get_sales_prediction(empresa, dias)

    if metadata is None:
        print("⚠ No hay modelo entrenado. Entrenando...")
        trained = train_sales_model(empresa)
        if not trained:
            return Response({"error": "No hay datos suficientes para entrenar el modelo."}, 404)

        predictions, metadata = get_sales_prediction(empresa, dias)

    # ===========================
    # 3️⃣ FILTRAR PREDICCIONES SEGÚN HISTÓRICO
    # ===========================
    from ventas.models import Venta

    ventas_qs = Venta.objects.filter(
        empresa=empresa,
        estado="entregado"
    )

    if producto_id:
        ventas_qs = ventas_qs.filter(detalles__producto_id=producto_id)

    if categoria_id:
        ventas_qs = ventas_qs.filter(detalles__producto__subcategoria__categoria_id=categoria_id)

    fechas_ventas = list(ventas_qs.values_list("fecha__date", flat=True))

    print("📌 Fechas históricas detectadas:", fechas_ventas[:5], "...")

    # ===========================
    # 4️⃣ APLICAR FILTRO AVANZADO A PREDICCIONES
    # ===========================
    if producto_id or categoria_id:
        pred_filtrado = []

        for item in predictions:
            fecha_pred = datetime.strptime(item["fecha"], "%Y-%m-%d").date()

            if fecha_pred in fechas_ventas:
                pred_filtrado.append(item)
            else:
                pred_filtrado.append({
                    "fecha": item["fecha"],
                    "prediccion_total_bs": 0
                })

        predictions = pred_filtrado

    # ===========================
    # 5️⃣ METADATA FINAL
    # ===========================
    rmse = round(metadata.get("rmse", 0), 2)

    metadata["interpretacion"] = (
        f"El modelo tiene un error promedio de ± {rmse} Bs. "
        "El filtrado adicional ajusta predicciones según ventas históricas."
    )

    # ===========================
    # 6️⃣ RESPUESTA
    # ===========================
    return Response({
        "predicciones": predictions,
        "metadata": metadata
    })



@api_view(["GET"])
def get_product_prediction_view(request):
    empresa = request.user.empresa
    producto_id = request.query_params.get("producto")

    if not producto_id:
        return Response({"error": "Debe enviar ?producto=ID"}, 400)

    try:
        producto = Producto.objects.get(id=producto_id, empresa=empresa)
    except Producto.DoesNotExist:
        return Response({"error": "Producto no encontrado"}, 404)

    data = get_product_prediction(empresa, producto)

    if data is None:
        return Response({"error": "No hay datos suficientes."}, 404)

    return Response(data)

@api_view(["GET"])
def get_trends_view(request):
    empresa = request.user.empresa
    dias = int(request.query_params.get("dias", 60))

    # ========= PREDICCIÓN IA =========
    pred, meta = get_sales_prediction(empresa, dias)

    if pred is None:
        train_sales_model(empresa)
        pred, meta = get_sales_prediction(empresa, dias)

    tendencias = get_global_trends(pred)

    # ========= RANKING PRODUCTOS =========
    desde = timezone.now() - timedelta(days=dias)

    ranking_qs = (
        DetalleVenta.objects
        .filter(
            empresa=empresa,
            venta__estado="entregado",
            venta__fecha__gte=desde
        )
        .values("producto__nombre")
        .annotate(total_vendido=Sum("cantidad"))
        .order_by("-total_vendido")[:10]
    )

    ranking = [
        {
            "producto": item["producto__nombre"],
            "fuerza": item["total_vendido"] or 0
        }
        for item in ranking_qs
    ]

    tendencias["ranking"] = ranking  # <- 🔥 AÑADIDO

    return Response({
        "predicciones": pred,
        "tendencias": tendencias,
        "metadata": meta
    })

@api_view(["GET"])
def get_sales_prediction_range_view(request):
    empresa = request.user.empresa
    fecha_inicio = request.query_params.get("inicio")
    fecha_fin = request.query_params.get("fin")

    if not fecha_inicio or not fecha_fin:
        return Response({"error": "Debe enviar parametros ?inicio=YYYY-MM-DD&fin=YYYY-MM-DD"}, 400)

    resultados, metadata = get_sales_prediction_range(empresa, fecha_inicio, fecha_fin)

    if resultados is None:
        train_sales_model(empresa)
        resultados, metadata = get_sales_prediction_range(empresa, fecha_inicio, fecha_fin)

    return Response({
        "predicciones": resultados,
        "metadata": metadata
    })

@api_view(["GET"])
def get_ia_insights(request):
    empresa = request.user.empresa

    df = prepare_data(empresa)
    if df is None:
        return Response({"error": "No hay datos suficientes."}, 404)

    weekly_avg = df.groupby("dia_de_la_semana")["total"].mean().round(2)
    monthly_avg = df.groupby("mes")["total"].mean().round(2)

    # Día fuerte / débil
    dia_fuerte = weekly_avg.idxmax()
    dia_debil = weekly_avg.idxmin()

    # Mes fuerte / débil
    mes_fuerte = monthly_avg.idxmax()
    mes_debil = monthly_avg.idxmin()

    # Variabilidad
    var_total = df["total"].var()
    var_mes = monthly_avg.var()

    porcentaje_estacionalidad = round((var_mes / var_total) * 100, 2) if var_total > 0 else 0

    return Response({
        "dia_fuerte": {
            "nombre": DAY_MAP[dia_fuerte],
            "promedio_bs": float(weekly_avg[dia_fuerte])
        },
        "dia_debil": {
            "nombre": DAY_MAP[dia_debil],
            "promedio_bs": float(weekly_avg[dia_debil])
        },
        "mes_fuerte": {
            "nombre": MONTH_MAP[mes_fuerte],
            "promedio_bs": float(monthly_avg[mes_fuerte])
        },
        "mes_debil": {
            "nombre": MONTH_MAP[mes_debil],
            "promedio_bs": float(monthly_avg[mes_debil])
        },
        "estacionalidad": porcentaje_estacionalidad,
    })

# ============================================================
# 🔮 INSIGHTS GLOBALES (ESTACIONALIDAD, DIA FUERTE, MES FUERTE)
# ============================================================
@api_view(["GET"])
def get_insights(request):
    from django.db.models.functions import ExtractWeekDay, ExtractMonth
    empresa = request.user.empresa

    # Obtener todas las ventas "entregadas"
    ventas = Venta.objects.filter(
        empresa=empresa,
        estado="entregado"
    )

    if not ventas.exists():
        return Response({"error": "No hay ventas suficientes"}, 404)

    # ------------------------------------------------------------
    # 1) Promedio por día de la semana
    # ------------------------------------------------------------
    dias_semana = ventas.annotate(
        dia=ExtractWeekDay("fecha")  # 1 Domingo ... 7 Sábado
    ).values("dia").annotate(
        promedio=Sum("total") / Count("id")
    ).order_by("dia")

    # Formatear nombres
    DIAS = {
        1: "Domingo", 2: "Lunes", 3: "Martes", 4: "Miércoles",
        5: "Jueves", 6: "Viernes", 7: "Sábado"
    }

    dias_format = [
        {"dia": d["dia"], "nombre": DIAS[d["dia"]], "promedio_bs": float(d["promedio"])}
        for d in dias_semana
    ]

    dia_fuerte = max(dias_format, key=lambda x: x["promedio_bs"])
    dia_debil = min(dias_format, key=lambda x: x["promedio_bs"])

    # ------------------------------------------------------------
    # 2) Promedio por mes
    # ------------------------------------------------------------
    meses = ventas.annotate(
        mes=ExtractMonth("fecha")
    ).values("mes").annotate(
        promedio=Sum("total") / Count("id")
    ).order_by("mes")

    MESES = {
        1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
        5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
        9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
    }

    meses_format = [
        {"mes": m["mes"], "nombre": MESES[m["mes"]], "promedio_bs": float(m["promedio"])}
        for m in meses
    ]

    mes_fuerte = max(meses_format, key=lambda x: x["promedio_bs"])
    mes_debil = min(meses_format, key=lambda x: x["promedio_bs"])

    # ------------------------------------------------------------
    # 3) Estacionalidad (qué % explican día + mes)
    # ------------------------------------------------------------
    promedio_dias = [d["promedio_bs"] for d in dias_format]
    promedio_meses = [m["promedio_bs"] for m in meses_format]

    var_dias = max(promedio_dias) - min(promedio_dias)
    var_meses = max(promedio_meses) - min(promedio_meses)

    estacionalidad = round((var_dias + var_meses) / 2, 2)

    return Response({
        "dia_fuerte": dia_fuerte,
        "dia_debil": dia_debil,
        "mes_fuerte": mes_fuerte,
        "mes_debil": mes_debil,
        "estacionalidad": estacionalidad
    })

@api_view(["POST"])
def retrain_model(request):
    empresa = request.user.empresa
    ok = train_sales_model(empresa)

    if not ok:
        return Response({"error": "No hay datos suficientes"}, 400)

    return Response({"status": "Modelo reentrenado correctamente"})
