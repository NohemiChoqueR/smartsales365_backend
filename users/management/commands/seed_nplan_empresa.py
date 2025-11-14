# users/management/commands/seed_plan_empresa.py
from django.core.management.base import BaseCommand
from tenants.models import Empresa, Plan
from users.models import Role, User
from django.utils import timezone

class Command(BaseCommand):
    help = 'Crea los planes y las empresas de ejemplo.'

    def handle(self, *args, **kwargs):
        # Crear el plan PREMIUM
        premium_plan = Plan.objects.create(
            nombre="PREMIUM",
            descripcion="Plan con todas las funcionalidades",
            max_usuarios=500,
            max_productos=500,
            max_ventas_mensuales=10000,
            almacenamiento_gb=1,
            precio_mensual=99.99,
            permite_reportes_ia=True,
            permite_exportar_excel=True,
            permite_notificaciones_push=True,
            soporte_prioritario=True,
            esta_activo=True,
            prediccion_ventas=True
        )

        # Crear las empresas
        empresa1 = Empresa.objects.create(
            nombre="SmartSales S.R.L.",
            nit="987654321",
            direccion="N/A",
            plan=premium_plan,
            logo="path/to/logo1.png",  # Modificar según corresponda
            esta_activo=True,
            fecha_registro=timezone.now()
        )

        empresa2 = Empresa.objects.create(
            nombre="TechWorld S.A.",
            nit="123456789",
            direccion="N/A",
            plan=premium_plan,
            logo="path/to/logo2.png",  # Modificar según corresponda
            esta_activo=True,
            fecha_registro=timezone.now()
        )

        # Verificar si el rol ADMIN ya existe para la empresa
        admin_role, created = Role.objects.get_or_create(
            name="ADMIN",
            empresa=empresa1,  # Asociado a la empresa 1
            defaults={'description': 'Administrador de empresa', 'esta_activo': True}
        )

        if created:
            self.stdout.write(self.style.SUCCESS("Rol ADMIN creado exitosamente."))
        else:
            self.stdout.write(self.style.WARNING("El rol ADMIN ya existe."))

        # Crear un usuario ADMIN asociado a la empresa
        user = User.objects.create_user(
            email="admin@empresa.com",
            password="admin1234",
            nombre="Admin",
            apellido="Empresa",
            role=admin_role,
            empresa=empresa1,  # Usuario asociado a empresa 1
            telefono="1234567890"
        )

        self.stdout.write(self.style.SUCCESS('Planes y empresas creados exitosamente.'))