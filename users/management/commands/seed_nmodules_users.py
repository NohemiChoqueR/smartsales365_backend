# users/management/commands/seed_modules_users.py
from django.core.management.base import BaseCommand
from tenants.models import Empresa
from users.models import Role, User, Module, Permission
from django.utils import timezone

class Command(BaseCommand):
    help = 'Crea los módulos, roles, usuarios y permisos de ejemplo.'

    def handle(self, *args, **kwargs):
        # Asegurarse de que la empresa con id=1 exista
        empresa = Empresa.objects.get(id=1)

        # Crear los módulos
        module_names = [
            "Departamento", "Direccion", "Sucursal", "StockSucursal", "Plan", 
            "Empresa", "User", "Role", "Module", "Permission", "MetodoPago", 
            "Pago", "Venta", "DetalleVenta", "Agencia", "Envio", "Marca", 
            "Categoria", "SubCategoria", "Producto", "DetalleProducto", 
            "ImagenProducto", "Campania", "Descuento", "Cart", "CartItem", 
            "Bitacora", "Notificacion"
        ]

        modules = {}
        for name in module_names:
            module = Module.objects.create(
                name=name,
                description=f"Modulo para gestionar {name.lower()}",
                esta_activo=True
            )
            modules[name] = module

        self.stdout.write(self.style.SUCCESS("Módulos creados exitosamente."))

        # Crear Roles
        roles_data = [
            ('SUPER_ADMIN', 'Administrador global del sistema'),
            ('ADMIN', 'Administrador de empresa'),
            ('SALES_AGENT', 'Agente de ventas'),
            ('CUSTOMER', 'Cliente final')
        ]
        
        roles = {}
        for name, description in roles_data:
            # Verificar si el rol ya existe para la empresa (empresa_id=1)
            role, created = Role.objects.get_or_create(
                name=name,
                empresa=empresa,  # Asignar a la empresa con id=1
                defaults={'description': description, 'esta_activo': True}
            )
            roles[name] = role
            if created:
                self.stdout.write(self.style.SUCCESS(f"Rol {name} creado exitosamente."))
            else:
                self.stdout.write(self.style.WARNING(f"El rol {name} ya existe."))

        self.stdout.write(self.style.SUCCESS("Roles creados exitosamente."))

        # Crear permisos para cada rol en cada módulo
        for role_name, role in roles.items():
            for module_name, module in modules.items():
                if role_name == "SUPER_ADMIN" or role_name == "ADMIN":
                    # SUPER_ADMIN y ADMIN tienen todos los permisos
                    Permission.objects.create(
                        can_view=True,
                        can_create=True,
                        can_update=True,
                        can_delete=True,
                        module=module,
                        role=role,
                        empresa=empresa
                    )
                elif role_name == "SALES_AGENT":
                    # SALES_AGENT: permisos limitados
                    can_view = module_name in ["Venta", "DetalleVenta", "Producto", "Cart", "CartItem", "Cliente"]
                    can_create = module_name in ["Venta", "DetalleVenta", "Producto", "Cart", "CartItem"]
                    can_update = module_name in ["Venta", "DetalleVenta", "Producto", "Cart", "CartItem"]
                    can_delete = False  # No puede eliminar nada

                    Permission.objects.create(
                        can_view=can_view,
                        can_create=can_create,
                        can_update=can_update,
                        can_delete=can_delete,
                        module=module,
                        role=role,
                        empresa=empresa
                    )
                elif role_name == "CUSTOMER":
                    # CUSTOMER: permisos completos en Cart y CartItem
                    can_view = module_name in ["Producto", "DetalleProducto", "Cart", "CartItem"]
                    can_create = module_name in ["Cart", "CartItem"]
                    can_update = module_name in ["Cart", "CartItem"]
                    can_delete = module_name in ["Cart", "CartItem"]

                    Permission.objects.create(
                        can_view=can_view,
                        can_create=can_create,
                        can_update=can_update,
                        can_delete=can_delete,
                        module=module,
                        role=role,
                        empresa=empresa
                    )

        self.stdout.write(self.style.SUCCESS("Permisos asignados correctamente a los roles y módulos."))

        # Verificar si el usuario ADMIN ya existe antes de crearlo
        if not User.objects.filter(email="admin@empresa.com").exists():
            # Crear un usuario ADMIN (ejemplo)
            admin_role = roles["ADMIN"]
            user = User.objects.create_user(
                email="admin@empresa.com",
                password="admin1234",
                nombre="Admin",
                apellido="Empresa",
                role=admin_role,
                empresa=empresa,
                telefono="1234567890"
            )
            self.stdout.write(self.style.SUCCESS("Usuario ADMIN creado exitosamente."))
        else:
            self.stdout.write(self.style.WARNING("El usuario ADMIN ya existe."))
        
        # Verificar si el usuario CLIENTE ya existe antes de crearlo
        if not User.objects.filter(email="cliente1@gmail.com").exists():
            # Crear un usuario CUSTOMER (ejemplo)
            customer_role = roles["CUSTOMER"]  # Obtén el rol CUSTOMER creado anteriormente
            user = User.objects.create_user(
                email="cliente1@gmail.com",
                password="12345",
                nombre="Cliente",
                apellido="Ejemplo",
                role=customer_role,
                empresa=empresa,
                telefono="9876543210"
            )
            self.stdout.write(self.style.SUCCESS("Usuario CLIENTE creado exitosamente."))
        else:
            self.stdout.write(self.style.WARNING("El usuario CLIENTE ya existe."))

        self.stdout.write(self.style.SUCCESS("Seeds de modules, roles, users y permissions completados."))
