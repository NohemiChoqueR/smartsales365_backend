# reports/views.py

from django.http import HttpResponse
from rest_framework.generics import ListAPIView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from django.db.models import Sum, Count
from django_filters.rest_framework import DjangoFilterBackend
import json
from django.db.models import Sum
import datetime
from django.utils import timezone

# ¡Importamos la "Fábrica" y el "Intérprete"!
from . import generators
from .nlp_utils import parse_natural_query, analyze_data_with_gemini

# Importamos los modelos y filtros para las vistas
from ventas.models import Venta, Pago, DetalleVenta
from .filters import ReporteVentaFilter, ReportePagoFilter

# --- CLASE BASE PARA OBTENER FECHAS ---
# Esto es para no repetir el código de fechas en cada vista
class BaseReporteView(ListAPIView):
    permission_classes = [IsAdminUser]
    
    def get_fechas(self, request):
            """
            Obtiene las fechas de la URL o establece un default (últimos 30 días).
            Devuelve (fecha_inicio, fecha_fin) como objetos 'datetime' CONSCIENTES.
            """
            fecha_inicio_str = request.query_params.get('fecha_inicio', None)
            fecha_fin_str = request.query_params.get('fecha_fin', None)

            try:
                if not fecha_inicio_str or not fecha_fin_str:
                    # Caso 1: Default (últimos 30 días)
                    fecha_fin_dt = timezone.now() # <-- Ya es consciente
                    fecha_inicio_dt = fecha_fin_dt - datetime.timedelta(days=30)
                else:
                    # Caso 2: Fechas de la URL
                    
                    # Convertimos string a 'datetime' ingenuo
                    fecha_inicio_naive = datetime.datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
                    fecha_fin_naive = datetime.datetime.strptime(fecha_fin_str, '%Y-%m-%d')
                    
                    # ¡LA MAGIA! Los hacemos "conscientes"
                    fecha_inicio_dt = timezone.make_aware(fecha_inicio_naive)
                    
                    # Para la fecha final, queremos incluir el DÍA COMPLETO
                    # Así que la ponemos al final del día (23:59:59)
                    fecha_fin_dt = timezone.make_aware(
                        datetime.datetime.combine(fecha_fin_naive.date(), datetime.time.max)
                    )

                return fecha_inicio_dt, fecha_fin_dt
                
            except ValueError:
                # Si el formato es malo, usa el default
                fecha_fin_dt = timezone.now()
                fecha_inicio_dt = fecha_fin_dt - datetime.timedelta(days=30)
                return fecha_inicio_dt, fecha_fin_dt

# --- VISTAS DE REPORTES (Ahora súper limpias) ---

class ReporteVentasPorProducto(BaseReporteView):
    queryset = Venta.objects.all()
    filterset_class = ReporteVentaFilter
    
    def get(self, request, *args, **kwargs):
        # 1. Cambiamos default a 'json'
        formato = request.query_params.get('formato', 'json').lower()
        fecha_inicio, fecha_fin = self.get_fechas(request)

        if formato in ['excel', 'pdf', 'csv']:
            return generators.generar_reporte_producto(request, formato, fecha_inicio, fecha_fin)

        base_query = Venta.objects.filter(
            estado='Completado',
            empresa=request.user.empresa
        )
        ventas_filtradas = base_query.filter(
            fecha__range=[fecha_inicio, fecha_fin]
        )
        if not ventas_filtradas.exists():
             return Response({"error": "No se encontraron ventas para este rango."}, status=404)

        ventas_ids = ventas_filtradas.values_list('id', flat=True)
        datos_agregados = DetalleVenta.objects.filter(
            venta__id__in=ventas_ids
        ).values(
            'producto__nombre', 'producto__sku'
        ).annotate(
            cantidad_total=Sum('cantidad'),
            ingresos_totales=Sum('subtotal')
        ).order_by('-ingresos_totales')

        if not datos_agregados:
            return Response({"error": "Sin datos de detalle de venta."}, status=404)
        datos_para_grafico = [
            {
                'name': item['producto__nombre'] or 'Sin Producto',
                'total': item['ingresos_totales'],  
                'cantidad': item['cantidad_total'], 
                'sku': item['producto__sku']  
            }
            for item in datos_agregados[:10] 
        ]
        return Response(datos_para_grafico)

class ReporteVentasPorSucursal(BaseReporteView):
    queryset = Venta.objects.all()
    filterset_class = ReporteVentaFilter
    
    def get(self, request, *args, **kwargs):
        formato = request.query_params.get('formato', 'json').lower()
        fecha_inicio, fecha_fin = self.get_fechas(request)
        if formato == 'excel' or formato == 'pdf' or formato == 'csv':
            return generators.generar_reporte_sucursal(request, formato, fecha_inicio, fecha_fin)

        base_query = Venta.objects.filter(
            estado='Completado',
            empresa=request.user.empresa,
            fecha__range=[fecha_inicio, fecha_fin]
        )
        
        datos_agregados = base_query.values(
            'sucursal__nombre'  
        ).annotate(
            numero_ventas=Count('id'),
            ingresos_totales=Sum('total') # Asumo que es 'total', igual que tu generador
        ).order_by('-ingresos_totales')

        datos_para_grafico = [
            {
                'name': item['sucursal__nombre'] or 'Sin Sucursal',
                'total': item['ingresos_totales'],
                'cantidad': item['numero_ventas'] # Enviamos también la cantidad
            }
            for item in datos_agregados
        ]

        return Response(datos_para_grafico)

class ReporteVentasPorVendedor(BaseReporteView):
    queryset = Venta.objects.all()
    filterset_class = ReporteVentaFilter
    
    def get(self, request, *args, **kwargs):
        formato = request.query_params.get('formato', 'excel').lower()
        fecha_inicio, fecha_fin = self.get_fechas(request)
        return generators.generar_reporte_vendedor(request, formato, fecha_inicio, fecha_fin)

class ReporteIngresosPorMetodoPago(BaseReporteView):
    queryset = Pago.objects.all()
    filterset_class = ReportePagoFilter
    
    def get(self, request, *args, **kwargs):
        formato = request.query_params.get('formato', 'excel').lower()
        fecha_inicio, fecha_fin = self.get_fechas(request)
        return generators.generar_reporte_metodo_pago(request, formato, fecha_inicio, fecha_fin)


# --- ¡LA NUEVA VISTA DE NLP! ---

class GenerarReporteNLPView(APIView):
    """
    Recibe un prompt de texto, lo interpreta con Gemini,
    y genera el reporte correspondiente.
    """
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        
        prompt = request.data.get('prompt', '')
        if not prompt:
            return Response({"error": "No se proporcionó un 'prompt' de texto."}, status=400)

        # 1. Llamar al "Intérprete" (NLP)
        parsed_json = parse_natural_query(prompt)
        
        if "error" in parsed_json:
            return Response(parsed_json, status=500)

        # 2. Extraer parámetros del JSON de Gemini
        reporte = parsed_json.get('reporte_a_generar')
        formato = parsed_json.get('formato', 'pdf') # Default 'pdf'
        fecha_inicio_str = parsed_json.get('fecha_inicio')
        fecha_fin_str = parsed_json.get('fecha_fin')

        if not reporte:
            return Response({"error": "No se pudo identificar qué reporte generar. Intenta ser más específico."}, status=400)

        # 3. Preparar Fechas
        try:
            if fecha_inicio_str and fecha_fin_str:
                # Convertir a 'datetime' ingenuo
                fecha_inicio_naive = datetime.datetime.strptime(fecha_inicio_str, '%Y-%m-%d')
                fecha_fin_naive = datetime.datetime.strptime(fecha_fin_str, '%Y-%m-%d')
                
                # ¡Hacerlos conscientes!
                fecha_inicio = timezone.make_aware(fecha_inicio_naive)
                fecha_fin = timezone.make_aware(
                    datetime.datetime.combine(fecha_fin_naive.date(), datetime.time.max)
                )
            else:
                # Default de 30 días (ya es consciente)
                fecha_fin = timezone.now()
                fecha_inicio = fecha_fin - datetime.timedelta(days=30)
        except ValueError:
            return Response({"error": "Gemini devolvió un formato de fecha inválido."}, status=500)

        # 4. Ser el "Operador" y llamar a la "Fábrica"
        
        if reporte == "ventas_producto":
            return generators.generar_reporte_producto(request, formato, fecha_inicio, fecha_fin)
            
        elif reporte == "ventas_sucursal":
            return generators.generar_reporte_sucursal(request, formato, fecha_inicio, fecha_fin)
            
        elif reporte == "ventas_vendedor":
            return generators.generar_reporte_vendedor(request, formato, fecha_inicio, fecha_fin)
            
        elif reporte == "ingresos_metodo_pago":
            return generators.generar_reporte_metodo_pago(request, formato, fecha_inicio, fecha_fin)
            
        else:
            return Response({"error": f"El reporte '{reporte}' no es un tipo de reporte válido."}, status=400)
    
class AnalizarVentasProductoView(APIView):
    """
    Toma un rango de fechas, consulta las ventas por producto,
    y le pide a Gemini que analice esos datos.
    """
    permission_classes = [IsAdminUser]

    # El prompt de "Analista" que le daremos a Gemini
    PROMPT_ANALISTA = """
    Eres un analista de negocios experto en retail de electrodomésticos.
    He extraído un reporte de ventas por producto de mi base de datos.
    Tu tarea es analizar este JSON y darme recomendaciones accionables.

    Por favor, dame:
    1.  Un resumen muy corto (una frase) del producto estrella.
    2.  Una lista de 2 o 3 "Insights Clave" (ej: "El producto X genera muchos ingresos pero pocas ventas", "El producto Y se vende mucho pero da poca ganancia").
    3.  Una "Recomendación Accionable" (ej: "Considera hacer un 'bundle' del Producto X con el Producto Z", "Sube el precio del Producto Y").

    Responde en un formato de texto simple y amigable.
    """

    def get(self, request, *args, **kwargs):
        
        # --- 1. Obtener Fechas (Lógica de tus otras vistas) ---
        fecha_inicio_str = request.query_params.get('fecha_inicio', None)
        fecha_fin_str = request.query_params.get('fecha_fin', None)
        
        if not fecha_inicio_str or not fecha_fin_str:
            fecha_fin = timezone.now().date()
            fecha_inicio = fecha_fin - datetime.timedelta(days=30)
        else:
            try:
                fecha_inicio = datetime.datetime.strptime(fecha_inicio_str, '%Y-%m-%d').date()
                fecha_fin = datetime.datetime.strptime(fecha_fin_str, '%Y-%m-%d').date()
            except ValueError:
                fecha_fin = timezone.now().date()
                fecha_inicio = fecha_fin - datetime.timedelta(days=30)

        # --- 2. Hacer la Consulta (Copiado de tu generador) ---
        base_query = Venta.objects.filter(
            estado='Completado',
            empresa=request.user.empresa
        )
        ventas_filtradas = base_query.filter(fecha__range=[fecha_inicio, fecha_fin])
        
        if not ventas_filtradas.exists():
            return Response({"error": "No se encontraron ventas para este rango."}, status=404)

        ventas_ids = ventas_filtradas.values_list('id', flat=True)
        datos_reporte = DetalleVenta.objects.filter(
            venta__id__in=ventas_ids
        ).values(
            'producto__nombre', 'producto__sku'
        ).annotate(
            cantidad_total=Sum('cantidad'),
            ingresos_totales=Sum('subtotal')
        ).order_by('-ingresos_totales')

        if not datos_reporte:
            return Response({"error": "Sin datos de detalle de venta para analizar."}, status=404)

        # --- 3. Convertir Datos a JSON ---
        # ¡Importante! Convertimos el QuerySet (que no es JSON) a una lista
        # y luego a un string de JSON.
        lista_datos = list(datos_reporte)
        datos_json_str = json.dumps(lista_datos, default=str) # default=str por si hay decimales

        # --- 4. Llamar al "Cerebro Analista" ---
        resultado = analyze_data_with_gemini(datos_json_str, self.PROMPT_ANALISTA)
        
        # --- 5. Devolver el Análisis ---
        if "error" in resultado:
            return Response(resultado, status=500)
            
        return Response(resultado)