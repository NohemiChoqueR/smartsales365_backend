# prediccion/ml_service.py
import os
from django.conf import settings
from django.utils import timezone
from ventas.models import Venta
import pandas as pd
import joblib

# Carpetas y rutas
BASE_DIR = settings.BASE_DIR
MODEL_DIR = os.path.join(BASE_DIR, "ml_models")
MODEL_PATH = os.path.join(MODEL_DIR, "sales_model.joblib")
META_PATH = os.path.join(MODEL_DIR, "sales_metadata.joblib")

DAY_MAP = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}
MONTH_MAP = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 
    6: "Junio", 7: "Julio", 8: "Agosto", 9: "Septiembre",
    10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}


def prepare_data(empresa):
    print("[ML Service] Generando dataset por empresa...")

    ventas_qs = Venta.objects.filter(
        empresa=empresa,
        estado="entregado"
    ).values("fecha", "total")

    if not ventas_qs.exists():
        return None

    df = pd.DataFrame(list(ventas_qs))
    df["fecha"] = pd.to_datetime(df["fecha"])
    df["total"] = pd.to_numeric(df["total"], errors="coerce")
    df.set_index("fecha", inplace=True)

    df_diario = df.resample("D").agg({"total": "sum"}).fillna(0)

    df_diario["anio"] = df_diario.index.year
    df_diario["mes"] = df_diario.index.month
    df_diario["dia_del_mes"] = df_diario.index.day
    df_diario["dia_de_la_semana"] = df_diario.index.dayofweek
    df_diario["dia_del_anio"] = df_diario.index.dayofyear

    return df_diario


def train_sales_model(empresa):
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import mean_squared_error
    import numpy as np

    df = prepare_data(empresa)
    if df is None or len(df) < 10:
        print("[ML] No hay datos suficientes.")
        return False

    features = ["anio", "mes", "dia_del_mes", "dia_de_la_semana", "dia_del_anio"]
    X, y = df[features], df["total"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    model = RandomForestRegressor(n_estimators=100, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))

    # INSIGHTS
    weekly = df.groupby("dia_de_la_semana")["total"].mean()
    monthly = df.groupby("mes")["total"].mean()

    metadata = {
        "rmse": rmse,
        "fecha_entrenamiento": str(timezone.now()),
        "insights": {
            "weekly_trend": [
                {"dia": DAY_MAP[k], "promedio_bs": float(round(v, 2))}
                for k, v in weekly.items()
            ],
            "monthly_trend": [
                {"mes": MONTH_MAP[k], "promedio_bs": float(round(v, 2))}
                for k, v in monthly.items()
            ],
        }
    }

    os.makedirs(MODEL_DIR, exist_ok=True)

    joblib.dump(model, MODEL_PATH)        # SOLO MODELO
    joblib.dump(metadata, META_PATH)      # SOLO METADATA

    return True


def get_sales_prediction(empresa, dias_a_predecir=30):
    import pandas as pd

    # Cargar modelo
    if not os.path.exists(MODEL_PATH) or not os.path.exists(META_PATH):
        return None, None

    model = joblib.load(MODEL_PATH)
    metadata = joblib.load(META_PATH)

    fecha_base = timezone.now()
    future_dates = pd.date_range(start=fecha_base, periods=dias_a_predecir, freq="D")

    X_future = pd.DataFrame({
        "anio": future_dates.year,
        "mes": future_dates.month,
        "dia_del_mes": future_dates.day,
        "dia_de_la_semana": future_dates.dayofweek,
        "dia_del_anio": future_dates.dayofyear,
    })

    pred = model.predict(X_future)

    results = [
        {
            "fecha": str(future_dates[i].date()),
            "prediccion_total_bs": float(round(max(0, pred[i]), 2))
        }
        for i in range(len(pred))
    ]

    return results, metadata

# ============================================================
# ░█▀█░█▀▄░█▀█░▀█▀░█▀▀░█▀█░█▀▀
# ======== PREDICCIÓN AVANZADA POR RANGO =====================
# ============================================================

def get_sales_prediction_range(empresa, fecha_inicio, fecha_fin):
    import pandas as pd

    if not os.path.exists(MODEL_PATH) or not os.path.exists(META_PATH):
        return None, None

    model = joblib.load(MODEL_PATH)
    metadata = joblib.load(META_PATH)

    fechas = pd.date_range(start=fecha_inicio, end=fecha_fin, freq="D")

    df = pd.DataFrame({
        "anio": fechas.year,
        "mes": fechas.month,
        "dia_del_mes": fechas.day,
        "dia_de_la_semana": fechas.dayofweek,
        "dia_del_anio": fechas.dayofyear,
    })

    pred = model.predict(df)

    resultados = []
    for i, f in enumerate(fechas):
        resultados.append({
            "fecha": str(f.date()),
            "prediccion_total_bs": float(max(pred[i], 0))
        })

    return resultados, metadata


# ============================================================
# ░█▀█░█▀█░█▀▀░█▀▄░█▀▀░█▀█░█▀▄░█▀▀░█▀█
# ======== PREDICCIÓN AVANZADA POR PRODUCTO =================
# ============================================================

def get_product_prediction(empresa, producto):
    """
    Predicción basada en la tendencia histórica del producto.
    Modelo simple: promedios + descomposición básica.
    """
    from ventas.models import DetalleVenta
    import pandas as pd
    from django.db.models import Sum

    # Obtener ventas históricas del producto
    qs = DetalleVenta.objects.filter(
        empresa=empresa,
        producto=producto,
        venta__estado="entregado"
    ).values("venta__fecha", "cantidad")

    if not qs.exists():
        return None

    df = pd.DataFrame(list(qs))
    df["venta__fecha"] = pd.to_datetime(df["venta__fecha"])
    df = df.groupby(df["venta__fecha"].dt.date).agg({"cantidad": "sum"})
    df.index = pd.to_datetime(df.index)

    df_diario = df.resample("D").sum().fillna(0)

    tendencia = df_diario.rolling(window=7).mean().round(2)
    promedio = df_diario.mean().round(2)

    return {
        "historico": df_diario.reset_index().rename(columns={
            "venta__fecha": "fecha",
            "cantidad": "vendido"
        }).to_dict(orient="records"),
        "promedio_diario": float(promedio),
        "tendencia_7_dias": [
            {"fecha": str(idx.date()), "promedio": float(val)}
            for idx, val in tendencia["cantidad"].items()
        ]
    }


# ============================================================
# ░█▀▀░█▀█░█▀▄░█▀▀░█▀▀░█▀█░▀█▀░█▄█░█▀█
# ======== TENDENCIAS GLOBALES =================================
# ============================================================

def get_global_trends(predicciones):
    import pandas as pd

    df = pd.DataFrame(predicciones)

    df["fecha"] = pd.to_datetime(df["fecha"])
    df["mes"] = df["fecha"].dt.month

    # Agrupar por día
    daily = df[["fecha", "prediccion_total_bs"]]

    # Agrupar por semana
    weekly = df.groupby(df["fecha"].dt.isocalendar().week)["prediccion_total_bs"].sum().reset_index()

    # Agrupar por mes
    monthly = df.groupby("mes")["prediccion_total_bs"].sum().reset_index()

    return {
        "diaria": daily.to_dict(orient="records"),
        "semanal": weekly.to_dict(orient="records"),
        "mensual": monthly.to_dict(orient="records"),
        "mes_mayor_venta": int(monthly.loc[monthly["prediccion_total_bs"].idxmax()]["mes"]),
        "mes_menor_venta": int(monthly.loc[monthly["prediccion_total_bs"].idxmin()]["mes"])
    }
