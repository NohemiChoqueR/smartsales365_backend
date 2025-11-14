import logging
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import connection

# Desactivar los logs ruidosos de 'django.db.backends' durante el TRUNCATE
db_logger = logging.getLogger('django.db.backends')
db_logger.setLevel(logging.WARNING)

class Command(BaseCommand):
    help = "⚠️ Elimina TODOS los datos de TODAS las tablas del proyecto, en orden inverso de dependencias."

    def add_arguments(self, parser):
        parser.add_argument(
            '--no-input',
            action='store_true',
            help='Ejecuta el reset sin pedir confirmación.',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("🚨 RESETEO TOTAL DE LA BASE DE DATOS..."))

        if not options['no_input']:
            confirm = input("¿Seguro? Esto es irreversible (escribe 'yes'): ")
            if confirm.lower() != "yes":
                self.stdout.write(self.style.ERROR("❌ Cancelado."))
                return

        try:
            with connection.cursor() as cursor:
                # Obtener todos los modelos
                all_models = apps.get_models()
                
                # --- LA CLAVE ESTÁ AQUÍ ---
                # Revertimos la lista. Esto hace que las tablas creadas
                # al final (como DetalleVenta) se borren PRIMERO,
                # y las tablas base (como User, Empresa) se borren AL FINAL.
                # Esto respeta las Foreign Keys.
                
                tables_truncated = []
                tables_failed = []
                
                # Iterar en orden inverso
                for model in reversed(all_models):
                    table = model._meta.db_table
                    try:
                        # Usar CASCADE para manejar dependencias que Django no gestiona
                        cursor.execute(f'TRUNCATE TABLE "{table}" RESTART IDENTITY CASCADE;')
                        tables_truncated.append(table)
                    except Exception as e:
                        # Si falla, probablemente sea una tabla que no se puede truncar
                        # (como las de sistema o las de tenants que están protegidas)
                        tables_failed.append((table, str(e)))

                self.stdout.write(self.style.SUCCESS("\n--- Tablas Truncadas Exitosamente ---"))
                for table in tables_truncated:
                    self.stdout.write(f"  ✅ {table}")

                if tables_failed:
                    self.stdout.write(self.style.WARNING("\n--- Tablas Omitidas o Fallidas (Normalmente OK) ---"))
                    for table, e in tables_failed:
                        self.stdout.write(f"  ⚠️ {table} (Error: {e})")

                self.stdout.write(self.style.SUCCESS("\n🎉 RESET COMPLETADO"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Error catastrófico durante el reset: {e}"))