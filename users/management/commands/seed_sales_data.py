# users/management/commands/seed_sales_data.py

import random
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from datetime import datetime, timedelta
from tenants.models import Empresa
from users.models import User
from products.models import Producto
from sucursales.models import Sucursal, StockSucursal
from ventas.models import Metodo_pago, Pago, Venta, DetalleVenta
from shipping.models import Agencia, Envio


class Command(BaseCommand):
    help = "🌱 Pobla la app ventas con datos REALISTAS desde 2024 hasta hoy"

    def handle(self, *args, **kwargs):

        # Rango grande de fechas: Enero 2024 → hoy
        fecha_inicio_global = datetime(2024, 1, 1)
        fecha_fin_global = timezone.now()

        empresas = Empresa.objects.all()

        for empresa in empresas:
            self.stdout.write(f"\n🏢 Poblando ventas para: {empresa.nombre}")

            # ------------------------------
            # 1. Crear Métodos de Pago
            # ------------------------------
            metodos_pago_data = [
                {"nombre": "Efectivo", "descripcion": "Pago en efectivo", "proveedor": "Sistema"},
                {"nombre": "Tarjeta Crédito", "descripcion": "Pago con tarjeta", "proveedor": "Visa/Mastercard"},
                {"nombre": "Transferencia", "descripcion": "Pago bancario", "proveedor": "Banco"},
                {"nombre": "Stripe", "descripcion": "Pago online", "proveedor": "Stripe"},
            ]

            for mp in metodos_pago_data:
                Metodo_pago.objects.get_or_create(
                    nombre=mp["nombre"],
                    empresa=empresa,
                    defaults={**mp, "esta_activo": True}
                )

            # ------------------------------
            # 2. Crear Agencias
            # ------------------------------
            agencias_data = [
                {"nombre": "DHL Express", "contacto": "Juan Pérez", "telefono": "800-1234"},
                {"nombre": "Correo Bolivia", "contacto": "María López", "telefono": "800-9012"},
            ]
            for ag in agencias_data:
                Agencia.objects.get_or_create(
                    nombre=ag["nombre"],
                    empresa=empresa,
                    defaults={**ag, "esta_activo": True}
                )

            # ------------------------------
            # 3. Obtener datos base
            # ------------------------------
            usuarios = list(User.objects.filter(empresa=empresa))
            sucursales = list(Sucursal.objects.filter(empresa=empresa))
            metodos = list(Metodo_pago.objects.filter(empresa=empresa))
            agencias_empresa = list(Agencia.objects.filter(empresa=empresa))
            productos = list(Producto.objects.filter(empresa=empresa))

            if not usuarios or not sucursales or not productos:
                self.stdout.write(f"⚠️ Datos insuficientes para {empresa.nombre}")
                continue

            # ------------------------------
            # 4. Preparar correlativo
            # ------------------------------
            ultima_venta = Venta.objects.filter(empresa=empresa).order_by('-id').first()
            ultimo_numero = int(ultima_venta.numero_nota.split('-')[1]) if ultima_venta else 0

            # ----------------------------------------------------
            # 🔥 5. Generar ventas MES A MES desde 2024 → hoy
            # ----------------------------------------------------
            fecha_cursor = fecha_inicio_global

            total_ventas = 0

            while fecha_cursor <= fecha_fin_global:
                self.stdout.write(f"   📅 Generando ventas para {fecha_cursor.strftime('%Y-%m')}")

                for sucursal in sucursales:

                    stocks = StockSucursal.objects.filter(
                        empresa=empresa,
                        sucursal=sucursal,
                        stock__gt=0
                    ).select_related('producto')

                    if not stocks.exists():
                        continue

                    # 15–30 ventas por mes por sucursal
                    num_ventas = random.randint(15, 30)

                    for i in range(num_ventas):

                        with transaction.atomic():

                            # Fecha aleatoria dentro del mes
                            dia = random.randint(1, 28)
                            fecha_venta = fecha_cursor.replace(day=dia)

                            ultimo_numero += 1
                            numero_nota = f"NV-{ultimo_numero:05d}"

                            usuario = random.choice(usuarios)
                            metodo = random.choice(metodos)

                            # Pago
                            pago = Pago.objects.create(
                                empresa=empresa,
                                metodo=metodo,
                                monto=0,
                                estado="completado",
                                fecha=fecha_venta,
                                referencia=f"PAY-{empresa.id}-S{sucursal.id}-{i:03d}"
                            )

                            # Venta
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
                            detalles_count = random.randint(1, 3)
                            usados = set()

                            for _ in range(detalles_count):
                                stock_item = random.choice(stocks)
                                producto = stock_item.producto

                                if producto.id in usados or stock_item.stock <= 0:
                                    continue

                                usados.add(producto.id)

                                cantidad = random.randint(1, min(5, stock_item.stock))
                                precio = producto.precio_venta
                                subtotal = cantidad * precio

                                total_venta += subtotal

                                DetalleVenta.objects.create(
                                    empresa=empresa,
                                    venta=venta,
                                    producto=producto,
                                    cantidad=cantidad,
                                    precio_unitario=precio,
                                    subtotal=subtotal,
                                )

                                stock_item.stock -= cantidad
                                stock_item.save()

                            if total_venta == 0:
                                venta.delete()
                                pago.delete()
                                ultimo_numero -= 1
                                continue

                            venta.total = total_venta
                            venta.save()

                            pago.monto = total_venta
                            pago.save()

                            total_ventas += 1

                # Avanzar al siguiente mes
                if fecha_cursor.month == 12:
                    fecha_cursor = fecha_cursor.replace(year=fecha_cursor.year + 1, month=1)
                else:
                    fecha_cursor = fecha_cursor.replace(month=fecha_cursor.month + 1)

            self.stdout.write(self.style.SUCCESS(
                f"✅ {total_ventas} ventas creadas para {empresa.nombre}"
            ))

        self.stdout.write(self.style.SUCCESS("\n🎉 SEED VENTAS COMPLETO DESDE 2024\n"))
