from django.core.management.base import BaseCommand
from users.models import Role, Module, Permission, User
from tenants.models import Empresa, Plan
from sucursales.models import Sucursal, Direccion, Departamento


class Command(BaseCommand):
    help = "🌱 Configura datos base multiempresa de SmartSales365 (SaaS)"

    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.MIGRATE_HEADING("=== 🌱 Configurando datos base multiempresa SmartSales365 ==="))

        # ====== PLAN ======
        plan, _ = Plan.objects.get_or_create(
            nombre="PREMIUM",
            defaults={
                "descripcion": "Plan con todas las funcionalidades",
                "max_usuarios": 50,
                "max_productos": 500,
                "precio_mensual": 99.99,
                "permite_reportes_ia": True,
                "permite_exportar_excel": True,
                "permite_notificaciones_push": True,
                "soporte_prioritario": True,
                "esta_activo": True,
            },
        )

        # ====== EMPRESAS (MODIFICADO) ======
        empresas = [
            {"nombre": "SmartSales S.R.L.", "nit": "987654321"},
            # {"nombre": "TechWorld S.A.", "nit": "123456789"}, # <--- Comentado para trabajar solo con la Empresa 1
        ]
        empresas_creadas = []
        for e in empresas:
            emp, _ = Empresa.objects.get_or_create(
                nombre=e["nombre"],
                defaults={"nit": e["nit"], "plan": plan, "esta_activo": True},
            )
            empresas_creadas.append(emp)
            self.stdout.write(self.style.SUCCESS(f"🏢 Empresa asegurada: {emp.nombre}"))

        # ====== DEPARTAMENTOS PARA TODAS LAS EMPRESAS EXISTENTES ======
        departamentos_data = ["Santa Cruz", "La Paz", "Cochabamba"]
        # NOTA: Esto ahora solo se ejecutará para las empresas en la lista de arriba (solo 1)
        empresas_existentes = Empresa.objects.filter(id__in=[e.id for e in empresas_creadas])

        # Diccionario para guardar referencias de departamentos por empresa
        departamentos_por_empresa = {}

        for empresa in empresas_existentes:
            self.stdout.write(f"📝 Poblando departamentos para: {empresa.nombre}")
            departamentos_empresa = {}
            for depto_nombre in departamentos_data:
                dep, created = Departamento.objects.get_or_create(
                    nombre=depto_nombre,
                    empresa=empresa,
                    defaults={}
                )
                departamentos_empresa[depto_nombre] = dep
                status = self.style.SUCCESS("✅ CREADO") if created else self.style.NOTICE("⚠️ YA EXISTÍA")
                self.stdout.write(f"    {status} Departamento: {depto_nombre}")
            
            departamentos_por_empresa[empresa.id] = departamentos_empresa

        # ====== ROLES (MODIFICADO) ======
        self.stdout.write(self.style.MIGRATE_HEADING("--- 🧑‍💼 Creando Roles ---"))

        # 1. Rol SUPER_ADMIN (Global)
        super_admin_role, _ = Role.objects.get_or_create(
            name="SUPER_ADMIN", 
            defaults={"description": "Administrador global del sistema", "empresa": None} 
        )
        self.stdout.write(self.style.SUCCESS(f"✅ Rol global asegurado: {super_admin_role.name}"))

        # Diccionario para guardar roles por empresa: roles_por_empresa[empresa_id][role_name]
        roles_por_empresa = {}
        
        roles_data_tenant = [
            {"name": "ADMIN", "description": "Administrador de empresa"},
            {"name": "SALES_AGENT", "description": "Agente de ventas"},
            {"name": "CUSTOMER", "description": "Cliente final"},
        ]

        # 2. Roles por Empresa (ADMIN, SALES_AGENT, CUSTOMER)
        # NOTA: Este bucle ahora solo se ejecutará una vez
        for emp in empresas_creadas:
            self.stdout.write(f"🧑‍💼 Creando roles para: {emp.nombre}")
            roles_empresa = {}
            
            for r in roles_data_tenant:
                role, created = Role.objects.get_or_create(
                    name=r["name"], 
                    empresa=emp,  
                    defaults={"description": r["description"]}
                )
                roles_empresa[r["name"]] = role
                status = self.style.SUCCESS("✅ CREADO") if created else self.style.NOTICE("⚠️ YA EXISTÍA")
                self.stdout.write(f"    {status} Rol: {role.name}")
            
            roles_por_empresa[emp.id] = roles_empresa


        # ====== SUPER ADMIN GLOBAL (MODIFICADO) ======
        superadmin, created = User.objects.get_or_create(
            email="owner@smartsales365.com",
            defaults={
                "nombre": "SaaS Owner",
                "apellido": "Global",
                "telefono": "00000000",
                "is_superuser": True,
                "is_staff": True,
                "empresa": None,
                "role": super_admin_role, 
            },
        )
        if created:
            superadmin.set_password("owner123")
            superadmin.save()
        self.stdout.write(self.style.SUCCESS("🌍 SUPER ADMIN global listo (owner@smartsales365.com / owner123)"))


        # ====== ADMIN POR EMPRESA (MODIFICADO) ======
        admins = [
            {"email": "admin1@smartsales.com", "empresa": empresas_creadas[0]},
            # {"email": "admin2@techworld.com", "empresa": empresas_creadas[1]}, # <--- Comentado
        ]
        for adm in admins:
            empresa_adm = adm["empresa"]
            role_admin_tenant = roles_por_empresa[empresa_adm.id]["ADMIN"] 
            
            user, created = User.objects.get_or_create(
                email=adm["email"],
                defaults={
                    "nombre": "Admin",
                    "apellido": empresa_adm.nombre,
                    "telefono": "70000000",
                    "empresa": empresa_adm,
                    "role": role_admin_tenant, 
                    "is_staff": True,
                },
            )
            if created:
                user.set_password("admin123")
                user.save()
            self.stdout.write(self.style.SUCCESS(f"👑 Admin listo: {adm['email']} / admin123"))


        # ====== 👥 AGENTES DE VENTA Y 🙍 CLIENTES POR EMPRESA (MODIFICADO) ======
        
        self.stdout.write(self.style.MIGRATE_HEADING("--- 👥 Creando 5 Agentes y 10 Clientes por Empresa ---"))

        # --- 1. CREACIÓN DE 5 AGENTES DE VENTA POR EMPRESA ---
        self.stdout.write(self.style.MIGRATE_HEADING("... 👥 Creando Agentes de Venta ..."))
        
        # NOTA: Este bucle ahora solo se ejecutará una vez
        for emp in empresas_creadas:
            role_agente = roles_por_empresa[emp.id].get("SALES_AGENT")
            
            if not role_agente:
                self.stdout.write(self.style.ERROR(f"El rol 'SALES_AGENT' no se encontró para {emp.nombre}. Saltando."))
                continue

            domain_part = emp.nombre.split()[0].lower().replace('.', '').replace(',', '') + ".com"
            self.stdout.write(f"🏢 Creando 5 agentes para {emp.nombre} (@{domain_part})")
            
            for i in range(1, 6): # Loop del 1 al 5
                email = f"agent{i}@{domain_part}"
                user_agente, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "nombre": f"Agente {i}",
                        "apellido": emp.nombre,
                        "telefono": f"610000{i:02d}", 
                        "empresa": emp,
                        "role": role_agente, 
                        "is_staff": False,
                        "status": "ACTIVE",
                    },
                )
                
                if created:
                    user_agente.set_password("agent123") 
                    user_agente.save()
                    self.stdout.write(self.style.SUCCESS(f"    ✅ Creado agente: {email} / agent123"))
                else:
                    self.stdout.write(self.style.NOTICE(f"    ⚠️ Agente ya existía: {email}"))

        # --- 2. CREACIÓN DE 10 CLIENTES POR EMPRESA ---
        self.stdout.write(self.style.MIGRATE_HEADING("... 🙍 Creando Clientes ..."))

        # NOTA: Este bucle ahora solo se ejecutará una vez
        for emp in empresas_creadas:
            role_cliente = roles_por_empresa[emp.id].get("CUSTOMER")

            if not role_cliente:
                self.stdout.write(self.style.ERROR(f"El rol 'CUSTOMER' no se encontró para {emp.nombre}. Saltando."))
                continue

            domain_part = emp.nombre.split()[0].lower().replace('.', '').replace(',', '') + ".com"
            self.stdout.write(f"🏢 Creando 10 clientes para {emp.nombre} (@{domain_part})")
            
            for i in range(1, 11): # Loop del 1 al 10
                email = f"customer{i}@{domain_part}"
                user_cliente, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        "nombre": f"Cliente {i}",
                        "apellido": f"Comprador {i}", 
                        "telefono": f"720000{i:02d}",
                        "empresa": emp,
                        "role": role_cliente, 
                        "is_staff": False,
                        "status": "ACTIVE",
                    },
                )
                
                if created:
                    user_cliente.set_password("customer123") 
                    user_cliente.save()
                    self.stdout.write(self.style.SUCCESS(f"    ✅ Creado cliente: {email} / customer123"))
                else:
                    self.stdout.write(self.style.NOTICE(f"    ⚠️ Cliente ya existía: {email}"))    

        # ====== MÓDULOS ======
        modules_data = [
            {"name": "User", "description": "Gestión de usuarios"},
            {"name": "Role", "description": "Gestión de roles"},
            {"name": "Module", "description": "Gestión de módulos"},
            {"name": "Permission", "description": "Gestión de permisos"},
            {"name": "Marca", "description": "Gestión de marcas"},
            {"name": "Categoria", "description": "Gestión de categorías"},
            {"name": "SubCategoria", "description": "Gestión de subcategorías"},
            {"name": "Producto", "description": "Gestión de productos"},
            {"name": "DetalleProducto", "description": "Gestión de detalles"},
            {"name": "ImagenProducto", "description": "Gestión de imágenes"},
            {"name": "Campania", "description": "Gestión de campañas"},
            {"name": "Descuento", "description": "Gestión de descuentos"},
            {"name": "Sucursal", "description": "Gestión de sucursales"},
            {"name": "StockSucursal", "description": "Gestión de stock"},
            {"name": "Bitacora", "description": "Registro de acciones"},
            {"name": "Empresa", "description": "Gestión de empresas"},
            {"name": "Plan", "description": "Gestión de planes"},
            {"name": "Metodo_pago", "description": "Gestión de métodos de pago"},
            {"name": "Pago", "description": "Gestión de pagos"},
            {"name": "Venta", "description": "Gestión de ventas"},
            {"name": "DetalleVenta", "description": "Gestión de detalles de venta"},
            {"name": "Agencia", "description": "Gestión de agencias de envío"},
            {"name": "Envio", "description": "Gestión de envíos"},
            {"name": "Direccion", "description": "Gestión de direcciones"},
            {"name": "Departamento", "description": "Gestión de departamentos"},
            {"name": "Notificacion", "description": "Gestión de notificaciones"},
            {"name": "Reporte", "description": "Gestión de reportes"},
            {"name": "IAReport", "description": "Generación de reportes con IA"},

        ]
        modules = {}
        for m in modules_data:
            mod, _ = Module.objects.get_or_create(name=m["name"], defaults={"description": m["description"]})
            modules[m["name"]] = mod

        # ====== PERMISOS (MODIFICADO) ======
        self.stdout.write(self.style.MIGRATE_HEADING("--- 🔐 Asignando Permisos ---"))

        # 1. Permisos para SUPER_ADMIN (Global)
        self.stdout.write(f"🔐 Asignando permisos globales para: {super_admin_role.name}")
        for mod in modules.values():
            Permission.objects.get_or_create(
                role=super_admin_role,
                module=mod,
                empresa=None, 
                defaults={
                    "can_view": 1, "can_create": 1, "can_update": 1, "can_delete": 1,
                },
            )

        # 2. Permisos para ADMIN (por Empresa)
        # NOTA: Este bucle ahora solo se ejecutará una vez
        for emp in empresas_creadas:
            role_admin_tenant = roles_por_empresa[emp.id]["ADMIN"] 
            self.stdout.write(f"🔐 Asignando permisos para ADMIN de: {emp.nombre}")
            
            for mod in modules.values():
                Permission.objects.get_or_create(
                    role=role_admin_tenant,
                    module=mod,
                    empresa=emp, 
                    defaults={
                        "can_view": 1, "can_create": 1, "can_update": 1, "can_delete": 1,
                    },
                )
        
        # ====== SUCURSALES POR EMPRESA ======
        # NOTA: Este bucle ahora solo se ejecutará una vez
        for emp in empresas_creadas:
            depto_santa_cruz = departamentos_por_empresa[emp.id]["Santa Cruz"]
            depto_la_paz = departamentos_por_empresa[emp.id]["La Paz"]
            
            # Sucursal Central (Santa Cruz)
            direccion_central, _ = Direccion.objects.get_or_create(
                empresa=emp,
                pais="Bolivia",
                ciudad="Santa Cruz de la Sierra", 
                zona="Centro",
                calle=f"Av. {emp.nombre.split()[0]} Central",
                numero="101",
                departamento=depto_santa_cruz,
            )
            Sucursal.objects.get_or_create(
                empresa=emp,
                nombre=f"Sucursal Central - {emp.nombre.split()[0]}",
                direccion=direccion_central,
                defaults={"esta_activo": True},
            )
            
            # Sucursal La Paz (La Paz)
            direccion_lp, _ = Direccion.objects.get_or_create(
                empresa=emp,
                pais="Bolivia",
                ciudad="La Paz", 
                zona="Zona Norte",
                calle=f"Av. {emp.nombre.split()[0]} La Paz",
                numero="202",
                departamento=depto_la_paz,
            )
            Sucursal.objects.get_or_create(
                empresa=emp,
                nombre=f"Sucursal La Paz - {emp.nombre.split()[0]}",
                direccion=direccion_lp,
                defaults={"esta_activo": True},
            )
            
            # Sucursal Norte (Santa Cruz - otra zona)
            direccion_norte, _ = Direccion.objects.get_or_create(
                empresa=emp,
                pais="Bolivia",
                ciudad="Santa Cruz de la Sierra", 
                zona="Equipetrol",
                calle=f"Av. {emp.nombre.split()[0]} Norte",
                numero="303",
                departamento=depto_santa_cruz,
            )
            Sucursal.objects.get_or_create(
                empresa=emp,
                nombre=f"Sucursal Norte - {emp.nombre.split()[0]}",
                direccion=direccion_norte,
                defaults={"esta_activo": True},
            )
            
            self.stdout.write(self.style.SUCCESS(f"🏪 3 Sucursales creadas para {emp.nombre}"))

        self.stdout.write(self.style.SUCCESS("\n🎉 Configuración de múltiples empresas completada ✅"))
        self.stdout.write(self.style.SUCCESS("📊 Tablas pobladas: Departamento, Plan, Empresa, Role, User, Module, Permission, Direccion, Sucursal"))