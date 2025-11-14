# products/management/commands/seed_productos.py
from django.core.management.base import BaseCommand
from products.models import Marca, Categoria, SubCategoria, Producto, DetalleProducto, ImagenProducto, Campania, Descuento
from sucursales.models import Sucursal, Direccion, Departamento, StockSucursal
from tenants.models import Empresa
import random

class Command(BaseCommand):
    help = 'Resetea las tablas y genera datos de ejemplo para productos, marcas, etc., asignados a empresa1.'

    def handle(self, *args, **options):
        # Obtener la empresa existente (empresa1)
        empresa1 = Empresa.objects.get(id=1)  # Asegúrate de que la empresa con id=1 existe

        # Eliminar todos los registros en las tablas relacionadas (para resetear)
        self.stdout.write(self.style.WARNING('Eliminando registros existentes...'))

        # Primero eliminamos los objetos de las tablas hijas
        Descuento.objects.filter(empresa=empresa1).delete()
        Sucursal.objects.filter(empresa=empresa1).delete()
        ImagenProducto.objects.filter(empresa=empresa1).delete()
        DetalleProducto.objects.filter(empresa=empresa1).delete()

        # Luego eliminamos las relaciones con subcategoría, categoría y marca (sin violar integridad referencial)
        Producto.objects.filter(empresa=empresa1).delete()
        SubCategoria.objects.filter(empresa=empresa1).delete()
        Categoria.objects.filter(empresa=empresa1).delete()
        Marca.objects.filter(empresa=empresa1).delete()
        Campania.objects.filter(empresa=empresa1).delete()

        # Finalmente eliminamos los objetos de las tablas relacionadas a la empresa
        Departamento.objects.filter(empresa=empresa1).delete()
        Direccion.objects.filter(empresa=empresa1).delete()

        self.stdout.write(self.style.SUCCESS('Registros eliminados exitosamente.'))

        # Crear marcas
        marcas = []
        for i in range(50):
            marcas.append(Marca.objects.create(
                empresa=empresa1,
                nombre=f"Marca {i+1}",
                descripcion=f"Descripción de Marca {i+1}",
                pais_origen="Corea del Sur"
            ))

        # Crear categorías
        categorias = []
        for i in range(50):
            categorias.append(Categoria.objects.create(
                empresa=empresa1,
                nombre=f"Categoria {i+1}",
                descripcion=f"Descripción de Categoria {i+1}",
                esta_activo=True
            ))

        # Crear subcategorías
        subcategorias = []
        for i in range(50):
            subcategorias.append(SubCategoria.objects.create(
                empresa=empresa1,
                categoria=random.choice(categorias),  # Asociamos una categoría aleatoria
                nombre=f"SubCategoria {i+1}",
                descripcion=f"Descripción de SubCategoria {i+1}",
                esta_activo=True
            ))

        # Crear sucursales para empresa1
        departamento1 = Departamento.objects.create(empresa=empresa1, nombre="Santa Cruz")
        departamento2 = Departamento.objects.create(empresa=empresa1, nombre="La Paz")

        direccion1 = Direccion.objects.create(
            empresa=empresa1,
            pais="Bolivia",
            ciudad="Santa Cruz",
            zona="Zona 1",
            calle="Calle 1",
            numero="123",
            departamento=departamento1
        )
        direccion2 = Direccion.objects.create(
            empresa=empresa1,
            pais="Bolivia",
            ciudad="La Paz",
            zona="Zona 2",
            calle="Calle 2",
            numero="456",
            departamento=departamento2
        )

        # Crear las sucursales después de crear las direcciones
        sucursal1 = Sucursal.objects.create(empresa=empresa1, nombre="Sucursal Santa Cruz", direccion=direccion1, esta_activo=True)
        sucursal2 = Sucursal.objects.create(empresa=empresa1, nombre="Sucursal La Paz", direccion=direccion2, esta_activo=True)

        # Crear productos
        productos = []
        for i in range(50):
            producto = Producto.objects.create(
                empresa=empresa1,
                nombre=f"Producto {i+1}",
                precio_venta=random.uniform(100, 10000),  # Precio aleatorio entre 100 y 10000
                descripcion=f"Descripción del Producto {i+1}",
                marca=random.choice(marcas),  # Asociamos una marca aleatoria
                subcategoria=random.choice(subcategorias)  # Asociamos una subcategoría aleatoria
            )
            productos.append(producto)

            # Crear detalle de producto
            DetalleProducto.objects.create(
                producto=producto, 
                empresa=empresa1,
                potencia=f"{random.randint(100, 2000)}W", 
                velocidades=str(random.randint(1, 5)), 
                voltaje=f"{random.randint(110, 240)}V", 
                aire_frio=random.choice(["Sí", "No"]), 
                tecnologias=f"Tecnología {random.randint(1, 5)}", 
                largo_cable=f"{random.randint(1, 5)}m"
            )
            # image_url = f"https://via.placeholder.com/300x200.png?text=Producto+{producto.id}"  # URL de marcador de posición
            # # Crear imágenes de productos
            # ImagenProducto.objects.create(
            #     producto=producto, 
            #     empresa=empresa1, 
            #     url=f"path/to/image{producto.id}.jpg", 
            #     descripcion=f"Imagen del producto {i+1}", 
            #     esta_activo=True
            # )

            # Crear stock en sucursales
            stock_sucursal_1 = StockSucursal.objects.create(
                empresa=empresa1,
                producto=producto,
                sucursal=sucursal1,
                stock=random.randint(0, 100)  # Stock aleatorio entre 0 y 100
            )

            stock_sucursal_2 = StockSucursal.objects.create(
                empresa=empresa1,
                producto=producto,
                sucursal=sucursal2,
                stock=random.randint(0, 100)  # Stock aleatorio entre 0 y 100
            )

        # Crear campañas
        campania1 = Campania.objects.create(
            empresa=empresa1, 
            nombre="Rebajas de fin de año", 
            descripcion="Descuentos especiales", 
            fecha_inicio="2025-12-01", 
            fecha_fin="2025-12-31", 
            esta_activo=True
        )

        # Asignar sucursales a los descuentos
        # Crear descuentos solo para empresa1
        for i in range(50):
            # Para evitar duplicados, usamos get_or_create
            descuento, created = Descuento.objects.get_or_create(
                empresa=empresa1, 
                producto=random.choice(productos),  # Selecciona un producto aleatorio
                sucursal=random.choice([sucursal1, sucursal2]),  # Selecciona una sucursal aleatoria
                defaults={
                    'nombre': f"{random.randint(5, 30)}% de descuento", 
                    'tipo': "PORCENTAJE", 
                    'porcentaje': random.uniform(5, 30),  # Descuento aleatorio entre 5% y 30%
                    'campania': campania1,
                    'esta_activo': True
                }
            )

        self.stdout.write(self.style.SUCCESS('¡50 datos de ejemplo creados exitosamente para empresa1!'))
