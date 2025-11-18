# users/management/commands/seed_analytics_data.py

import random
import datetime
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from django.utils.timezone import make_aware

from tenants.models import Empresa
from users.models import User
from products.models import Producto
from sucursales.models import Sucursal, StockSucursal
from ventas.models import Metodo_pago, Pago, Venta, DetalleVenta


class Command(BaseCommand):
    help = "🌱 Seed especial para ANALÍTICA: genera ventas históricas reales por empresa"

    def handle(self, *args, **kwargs):

        empresas = Empresa.objects.all()

        for empresa in empresas:
            self.stdout.write(self.style.HTTP_INFO(f"\n🏢 Generando ventas históricas para: {empresa.nombre}"))

            usuarios = list(User.objects.filter(empresa=empresa))
            sucursales = list(Sucursal.objects.filter(empresa=empresa))
            productos = list(Producto.objects.filter(empresa=empresa))
            metodos_pago = list(Metodo_pago.objects.filter(empresa=empresa))

            if not usuarios or not sucursales or not productos or not metodos_pago:
                self.stdout.write(self.style.ERROR("⚠ No hay suficientes datos para generar ventas."))
                continue

            # 🔵 CONFIGURACIÓN DEL SEED
            DIAS_HISTORICOS = 180     # 6 meses atrás
            VENTAS_POR_DIA = (1, 4)
            DETALLES_POR_VENTA = (1, 3)

            # Para mantener correlatividad
            venta_counter = Venta.objects.filter(empresa=empresa).count()

            # Iniciar generación
            for dias_atras in range(DIAS_HISTORICOS, 0, -1):

                # ==========================
                # 🔧 CORRECCIÓN TIMEZONE
                # ==========================
                fecha_venta = timezone.now() - datetime.timedelta(days=dias_atras)

                # Garantizar datetime aware siempre
                if timezone.is_naive(fecha_venta):
                    fecha_venta = make_aware(fecha_venta)

                ventas_hoy = random.randint(*VENTAS_POR_DIA)

                for _ in range(ventas_hoy):

                    with transaction.atomic():
                        venta_counter += 1
                        numero_nota = f"NV-{venta_counter:05d}"

                        usuario = random.choice(usuarios)
                        sucursal = random.choice(sucursales)
                        metodo = random.choice(metodos_pago)

                        # Crear Pago
                        pago = Pago.objects.create(
                            empresa=empresa,
                            metodo=metodo,
                            monto=0,
                            estado="completado",
                            fecha=fecha_venta,
                            referencia=f"PAY-{empresa.id}-{numero_nota}",
                        )

                        # Crear Venta
                        venta = Venta.objects.create(
                            empresa=empresa,
                            numero_nota=numero_nota,
                            usuario=usuario,
                            sucursal=sucursal,
                            canal="POS",
                            pago=pago,
                            fecha=fecha_venta,
                            total=0,
                            estado="entregado",
                        )

                        total_venta = 0
                        detalles_count = random.randint(*DETALLES_POR_VENTA)

                        productos_usados = set()

                        for _ in range(detalles_count):

                            producto = random.choice(productos)

                            # Prevenir duplicados
                            intentos = 0
                            while producto.id in productos_usados and intentos < 5:
                                producto = random.choice(productos)
                                intentos += 1

                            if producto.id in productos_usados:
                                continue

                            productos_usados.add(producto.id)

                            # Obtener stock
                            try:
                                stock_item = StockSucursal.objects.get(
                                    empresa=empresa,
                                    sucursal=sucursal,
                                    producto=producto
                                )
                            except StockSucursal.DoesNotExist:
                                continue

                            if stock_item.stock <= 0:
                                continue

                            cantidad = random.randint(1, min(5, stock_item.stock))
                            precio_unitario = producto.precio_venta
                            subtotal = precio_unitario * cantidad
                            total_venta += subtotal

                            DetalleVenta.objects.create(
                                empresa=empresa,
                                venta=venta,
                                producto=producto,
                                cantidad=cantidad,
                                precio_unitario=precio_unitario,
                                subtotal=subtotal,
                            )

                            stock_item.stock -= cantidad
                            stock_item.save()

                        # Si no se agregaron detalles, eliminar venta
                        if total_venta == 0:
                            venta.delete()
                            pago.delete()
                            venta_counter -= 1
                            continue

                        # Guardar totales
                        venta.total = total_venta
                        venta.save()
                        pago.monto = total_venta
                        pago.save()

                # Mostrar progreso
                if dias_atras % 20 == 0:
                    self.stdout.write(f"⏳ Progreso: faltan {dias_atras} días...")

            self.stdout.write(self.style.SUCCESS(
                f"✅ Ventas históricas generadas exitosamente para {empresa.nombre}"
            ))

        self.stdout.write(self.style.SUCCESS("\n🎉 SEED ANALÍTICA COMPLETADO.\n"))
