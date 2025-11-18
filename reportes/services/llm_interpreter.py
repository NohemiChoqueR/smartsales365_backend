import re
from datetime import datetime, timedelta

# ===========================================
# 🔵 Helper: Normalizar texto (evita espacios raros)
# ===========================================
def normalize_text(text: str):
    text = text.lower()
    text = text.replace("\xa0", " ")   # quita espacios raros
    text = " ".join(text.split())      # colapsa espacios múltiples
    return text


# ===========================================
# 🔵 Interpretador basado en reglas (VERSIÓN A+)
# ===========================================
def interpretar_prompt(prompt: str):
    prompt_low = normalize_text(prompt)

    filtros = {}
    agrupacion = []
    calculos = {}
    orden = []

    # ===========================================
    # 1️⃣ DETECTAR TIPO DE REPORTE (PRIORIDAD)
    # ===========================================
    is_ventas = bool(re.search(r"\bventa(s)?\b", prompt_low))
    is_productos = bool(re.search(r"\bproducto(s)?\b", prompt_low))
    is_usuarios = bool(re.search(r"\busuario(s)?\b", prompt_low))

    # PRIORIDAD CORRECTA:
    # ventas > productos > usuarios
    if is_ventas:
        tipo = "ventas"
    elif is_productos:
        tipo = "productos"
    elif is_usuarios:
        tipo = "usuarios"
    else:
        return {"error": "No se pudo determinar el tipo de reporte. Use ventas, productos o usuarios."}

    # ===========================================
    # 2️⃣ DETECTAR FORMATO
    # ===========================================
    formato = "json"
    if "pdf" in prompt_low:
        formato = "pdf"
    if "excel" in prompt_low or "xlsx" in prompt_low or "hoja" in prompt_low:
        formato = "excel"

    # ===========================================
    # 3️⃣ FECHAS (YYYY-MM-DD)
    # ===========================================
    fechas = re.findall(r"\d{4}-\d{2}-\d{2}", prompt_low)
    if len(fechas) == 1:
        filtros["fecha__date"] = fechas[0]
    if len(fechas) >= 2:
        filtros["fecha__date__range"] = fechas[:2]

    # == Filtros naturales de tiempo ==
    hoy = datetime.now().date()

    if "último mes" in prompt_low or "ultimo mes" in prompt_low:
        fecha_fin = hoy
        fecha_inicio = hoy - timedelta(days=30)
        filtros["fecha__date__range"] = [str(fecha_inicio), str(fecha_fin)]

    if "última semana" in prompt_low or "ultima semana" in prompt_low:
        fecha_fin = hoy
        fecha_inicio = hoy - timedelta(days=7)
        filtros["fecha__date__range"] = [str(fecha_inicio), str(fecha_fin)]

    if "hoy" in prompt_low:
        filtros["fecha__date"] = str(hoy)

    if "ayer" in prompt_low:
        filtros["fecha__date"] = str(hoy - timedelta(days=1))

    # ===========================================
    # 4️⃣ REGLAS PARA PRODUCTOS
    # ===========================================
    if tipo == "productos":
        clean = prompt_low

        # precio > X
        m = re.search(r"precio_venta.*mayor( a| de)? (\d+)", clean)
        if m:
            filtros["precio_venta__gt"] = int(m.group(2))

        # precio < X
        m = re.search(r"precio_venta.*menor( a| de)? (\d+)", clean)
        if m:
            filtros["precio_venta__lt"] = int(m.group(2))

        # precio entre X y Y
        m = re.search(r"precio.*entre (\d+) y (\d+)", clean)
        if m:
            filtros["precio_venta__range"] = [int(m.group(1)), int(m.group(2))]

        # ordenar por precio DESC
        if "descendente" in clean or "de mayor a menor" in clean:
            orden.append("-precio_venta")

        # ordenar por precio ASC
        if "ascendente" in clean or "de menor a mayor" in clean:
            orden.append("precio_venta")

        # ordenar por nombre
        if "ordenar por nombre" in clean:
            orden.append("nombre")

    # ===========================================
    # 5️⃣ REGLAS PARA VENTAS
    # ===========================================
    if tipo == "ventas":

        # estado
        if "entregado" in prompt_low:
            filtros["estado"] = "entregado"

        if "anulado" in prompt_low or "anulada" in prompt_low:
            filtros["estado"] = "anulado"

        # AGRUPACIONES
        if "agrupado por usuario" in prompt_low:
            agrupacion.append("usuario__email")

        if "agrupado por sucursal" in prompt_low:
            agrupacion.append("sucursal__nombre")

        # TOTAL VENDIDO
        if "total vendido" in prompt_low or "sumar" in prompt_low or "suma" in prompt_low:
            calculos["total_vendido"] = {"funcion": "Sum", "campo": "total"}

        # orden por fecha descendente
        if "reciente" in prompt_low:
            orden.append("-fecha")

    # ===========================================
    # 6️⃣ REGLAS PARA USUARIOS
    # ===========================================
    if tipo == "usuarios":
        if "activo" in prompt_low:
            filtros["esta_activo"] = True

        if "rol" in prompt_low:
            m = re.search(r"rol (\w+)", prompt_low)
            if m:
                filtros["role__name__icontains"] = m.group(1)

    # ===========================================
    # 7️⃣ ORDEN DEFAULT
    # ===========================================
    if not orden:
        if tipo == "ventas":
            orden = ["-fecha"]
        else:
            orden = ["nombre"]

    # ===========================================
    # 8️⃣ RESPUESTA FINAL
    # ===========================================
    return {
        "tipo_reporte": tipo,
        "filtros": filtros,
        "agrupacion": agrupacion,
        "calculos": calculos,
        "orden": orden,
        "formato": formato,
        "prompt": prompt
    }
