import random, datetime
from django.core.management.base import BaseCommand
from faker import Faker
from tenants.models import Empresa
from products.models import (
    Marca, Categoria, SubCategoria, Producto, DetalleProducto,
    ImagenProducto, Campania, Descuento
)
from ventas.models import Metodo_pago
from shipping.models import Agencia
from sucursales.models import Sucursal, StockSucursal

# --- 1. Definición centralizada de datos ---

MARCAS_DATA = {
    "Samsung": "SAM", "LG": "LG", "Sony": "SON", "Xiaomi": "XIA", "Apple": "APP",
    "HP": "HP", "Dell": "DEL", "Logitech": "LOG", "Razer": "RAZ",
    "Oster": "OST", "Mabe": "MAB", "Philips": "PHI",
    "JBL": "JBL", "Bose": "BOS"
}

CATEGORIAS_DATA = {
    "Dispositivos Móviles": {"prefix": "DIS", "subs": ["Smartphones", "Tablets", "Celulares Básicos"]},
    "Laptops":               {"prefix": "LAP", "subs": ["Notebooks", "Ultrabooks", "Gaming Laptops"]},
    "Accesorios":            {"prefix": "ACC", "subs": ["Mouses", "Teclados", "Cases", "Cargadores"]},
    "Audio":                 {"prefix": "AUD", "subs": ["Auriculares", "Parlantes Bluetooth"]},
    "Televisores":           {"prefix": "TEL", "subs": ["Smart TV", "OLED", "QLED"]},
    "Electrohogar":          {"prefix": "ELE", "subs": ["Licuadoras", "Batidoras", "Microondas"]},
}

LOGICA_PRODUCTOS = {
    "Dispositivos Móviles": ["Samsung", "Xiaomi", "Apple", "LG"],
    "Laptops": ["HP", "Dell", "Apple", "Razer", "Samsung"],
    "Accesorios": ["Logitech", "Razer", "HP", "Dell", "Apple", "Samsung"],
    "Audio": ["Sony", "JBL", "Bose", "Xiaomi", "Apple", "Samsung"],
    "Televisores": ["LG", "Samsung", "Sony", "Philips"],
    "Electrohogar": ["Oster", "Mabe", "Philips", "LG", "Samsung"],
}

# --- Fin de la definición de datos ---


class Command(BaseCommand):
    help = "🌱 Pobla la app products con datos de ejemplo LÓGICOS para cada empresa"

    def handle(self, *args, **kwargs):
        fake = Faker("es_ES")
        
        # --- Solo se ejecuta para la Empresa 1 ("SmartSales S.R.L.") ---
        empresas = Empresa.objects.filter(nombre="SmartSales S.R.L.")

        if not empresas.exists():
            self.stdout.write(self.style.ERROR("❌ No se encontró la empresa 'SmartSales S.R.L.'."))
            self.stdout.write(self.style.ERROR("   Asegúrate de haberla creado con: python manage.py seed_users_data"))
            return

        # Este bucle 'for' ahora solo se ejecutará una vez
        for empresa in empresas:
            self.stdout.write(self.style.HTTP_INFO(f"\n🏢 Poblando datos para empresa: {empresa.nombre}"))
            
            product_counter = 1
            
            # --- 1. Marcas ---
            marcas_creadas = {} 
            for nombre_marca in MARCAS_DATA.keys():
                obj, _ = Marca.objects.get_or_create(nombre=nombre_marca, empresa=empresa, defaults={"esta_activo": True})
                marcas_creadas[nombre_marca] = obj
            self.stdout.write(f"    ✓ Marcas creadas/verificadas ({len(marcas_creadas)})")

            # --- 2. Categorías y Subcategorías ---
            subcategorias_creadas = {} 
            for cat_nombre, data in CATEGORIAS_DATA.items():
                c, _ = Categoria.objects.get_or_create(nombre=cat_nombre, empresa=empresa)
                for sub_nombre in data["subs"]:
                    s, _ = SubCategoria.objects.get_or_create(nombre=sub_nombre, categoria=c, empresa=empresa)
                    subcategorias_creadas[sub_nombre] = s
            self.stdout.write(f"    ✓ Categorías y Subcategorías creadas/verificadas")

            # --- 3. Campañas ---
            hoy = datetime.date.today()
            campanias_data = [
                {"nombre": "Campaña Verano", "desc": "Ofertas de verano", "inicio": hoy, "fin": hoy + datetime.timedelta(days=30)},
                {"nombre": "Cyber Monday", "desc": "Descuentos Tech", "inicio": hoy + datetime.timedelta(days=40), "fin": hoy + datetime.timedelta(days=47)},
                {"nombre": "Navidad 2025", "desc": "Especiales de Navidad", "inicio": hoy + datetime.timedelta(days=60), "fin": hoy + datetime.timedelta(days=90)},
            ]
            
            campanias_creadas = [] 
            
            for c in campanias_data:
                obj, _ = Campania.objects.get_or_create(
                    nombre=c["nombre"],
                    empresa=empresa,
                    defaults={
                        "descripcion": c["desc"],
                        "fecha_inicio": c["inicio"],
                        "fecha_fin": c["fin"],
                    },
                )
                campanias_creadas.append(obj)
                
            self.stdout.write(f"    ✓ Campañas creadas/verificadas ({len(campanias_creadas)})")

            # --- 4. Métodos de Pago y Agencias ---
            metodos_pago = [
                {"nombre": "Efectivo", "descripcion": "Pago en efectivo", "proveedor": "Sistema"},
                {"nombre": "Tarjeta Crédito", "descripcion": "Pago con tarjeta", "proveedor": "Visa/Mastercard"},
                {"nombre": "Stripe", "descripcion": "Pago vía Stripe", "proveedor": "Stripe"},
            ]
            for mp in metodos_pago:
                Metodo_pago.objects.get_or_create(nombre=mp["nombre"], empresa=empresa, defaults={**mp, "esta_activo": True})
            
            agencias = [
                {"nombre": "DHL Express", "contacto": "Juan Pérez", "telefono": "800-1234"},
                {"nombre": "Correo Bolivia", "contacto": "María López", "telefono": "800-9012"},
            ]
            for ag in agencias:
                Agencia.objects.get_or_create(nombre=ag["nombre"], empresa=empresa, defaults={**ag, "esta_activo": True})
            
            # --- 5. Productos y Stock (Sin Imágenes) ---
            self.stdout.write("    ⏳ Generando productos con lógica de marcas y SKUs...")
            sucursales = Sucursal.objects.filter(empresa=empresa)
            productos_creados_count = 0

            for cat_nombre, marcas_permitidas in LOGICA_PRODUCTOS.items():
                
                cat_data = CATEGORIAS_DATA[cat_nombre]
                cat_sku_prefix = cat_data["prefix"]
                subcategorias_de_esta_cat = [subcategorias_creadas[s] for s in cat_data["subs"]]

                if not subcategorias_de_esta_cat:
                    continue

                for marca_nombre in marcas_permitidas:
                    marca_obj = marcas_creadas[marca_nombre]
                    marca_sku_prefix = MARCAS_DATA[marca_nombre]
                    
                    for _ in range(random.randint(2, 3)):
                        sub_obj = random.choice(subcategorias_de_esta_cat)
                        
                        sku_num = f"{product_counter:04d}"
                        sku_final = f"{cat_sku_prefix}-{marca_sku_prefix}-{sku_num}"
                        product_counter += 1
                        
                        nombre_producto = f"{sub_obj.nombre} {marca_obj.nombre} {fake.word().capitalize()}"
                        
                        p, created = Producto.objects.get_or_create(
                            sku=sku_final,
                            empresa=empresa,
                            defaults={
                                "nombre": nombre_producto,
                                "precio_venta": round(random.uniform(50, 3000), 2),
                                "marca": marca_obj,
                                "subcategoria": sub_obj,
                            },
                        )
                        
                        if not created: 
                            continue 
                            
                        productos_creados_count += 1

                        DetalleProducto.objects.get_or_create(
                            producto=p,
                            empresa=empresa,
                            defaults={"potencia": "200W", "voltaje": "220V"},
                        )
                        
                        # Bloque de ImagenProducto quitado
                        
                        for sucursal in sucursales:
                            stock_final = random.randint(20, 100)
                            StockSucursal.objects.get_or_create(
                                producto=p,
                                sucursal=sucursal,
                                empresa=empresa,
                                defaults={"stock": stock_final},
                            )

            self.stdout.write(f"    ✓ {productos_creados_count} productos lógicos creados.")

            # --- 6. Descuentos (CORREGIDO) ---
            self.stdout.write("    ⏳ Creando descuentos ligados a campañas y productos...")
            productos = list(Producto.objects.filter(empresa=empresa))
            
            if productos and sucursales.exists() and campanias_creadas:
                
                # Creamos 5 descuentos aleatorios
                for _ in range(5):
                    p = random.choice(productos)
                    suc_choice = random.choice(sucursales)
                    campania_choice = random.choice(campanias_creadas)
                    
                    # --- INICIO DE CORRECCIÓN ---
                    # Los campos de la restricción 'uniq' (empresa, producto, sucursal)
                    # DEBEN ir fuera de 'defaults'.
                    Descuento.objects.get_or_create(
                        empresa=empresa,
                        producto=p,
                        sucursal=suc_choice,
                        
                        # 'defaults' son los valores que se usarán SOLO SI se crea
                        defaults={
                            "nombre": f"Desc. {p.nombre[:15]} - {campania_choice.nombre[:10]}",
                            "tipo": "PORCENTAJE",
                            "porcentaje": random.randint(5, 15),
                            "campania": campania_choice,
                            "esta_activo": True
                        },
                    )
                    # --- FIN DE CORRECCIÓN ---
                    
                self.stdout.write(f"    ✓ 5 descuentos aleatorios creados/verificados.")
            else:
                 self.stdout.write(self.style.WARNING("    ⚠️ No se pudieron crear descuentos (faltan productos, sucursales o campañas)."))


            self.stdout.write(self.style.SUCCESS(f"✅ Datos creados para empresa {empresa.nombre}"))
        self.stdout.write(self.style.SUCCESS("\n🎯 Seed de products LÓGICO completado ✅"))