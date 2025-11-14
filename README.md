# Sistema de Gestión Comercial Iteligente Smart Sales 365

## Descripción
Sistema de Gestión Comercial para venta de electrodomésticos con IA predictiva.

- Gestión de usuarios y clientes
- Catálogo de productos (electrodomésticos)
- Proceso de ventas completo
- Reportes y analytics
- Predicciones con Machine Learning
- Sistema de autenticación con JWT y control de accesos por permisos.

## Tecnologías
- Python 3.13
- Django 5.2.5
- Django REST Framework
- SimpleJWT
- PostgreSQL
- Swagger (drf_yasg)

## Instalación y Levantamiento del Backend

1. Crear y activar el entorno virtual:
python -m venv venv
venv\Scripts\activate # Windows
source venv/bin/activate # Linux/Mac

2. Instalar dependencias:
pip install -r requirements.txt


3. Configurar variables de entorno (`.env`):
SECRET_KEY=...
DEBUG=True
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=...
DB_PORT=...
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000


4. Migrar base de datos:
python manage.py makemigrations
python manage.py migrate

## Seed de datos iniciales
Ejecutar el siguiente comando para crear usuarios base y permisos automáticamente:
python manage.py seed_users_data

5. Levantar servidor:
python manage.py runserver


## Swagger
- La documentación de la API se encuentra en `/swagger/`.
http://127.0.0.1:8000/api-docs/
http://127.0.0.1:8000/swagger/

- Usar Bearer token para rutas protegidas:
Authorization: Bearer <TOKEN>
- Permite probar endpoints directamente desde el navegador y ver respuestas JSON.

# Guía de Contribución

## Flujo de trabajo
1. Clonar el repositorio.
2. Crear una rama 
3. Hacer commits claros:
git commit -m "Tipo: Descripción corta y clara"

Para nueva funcionalidad:
feat: add user registration with email validation
feat: implement role-based permission system
feat: add CRUD operations for user management
feat: integrate Swagger documentation for API endpoints

Para arreglos:
fix: resolve authentication token expiration issue
fix: correct user permission validation logic
fix: patch security vulnerability in password reset

Para la documentación:
docs: add API endpoints documentation in Swagger
docs: update README with installation instructions
docs: add comments for permission middleware

Para refactor:
refactor: optimize database queries in user service
refactor: reorganize project folder structure
refactor: improve error handling in auth middleware

4. Subir cambios a tu rama:
git push origin rama/nombre-descriptivo

5. Crear Pull Request hacia `main` (o rama principal del proyecto).

## Recomendaciones
- Probar tus cambios en Swagger antes de subirlos.
- Usar nombres claros para ramas y commits.
- Evitar subir datos sensibles.
- Git status para ver que se está subiendo
- Mantener consistencia con las convenciones de código del proyecto.


from ventas.models import Venta, DetalleVenta, Pago
Venta.objects.all().delete()
DetalleVenta.objects.all().delete()
Pago.objects.all().delete()
print("✅ Todo borrado")

[text](bitacora) [text](cart) [text](ml_models) [text](notifications) [text](predictions) [text](products) [text](reports) [text](shipping) [text](smartsales) [text](sucursales) [text](tenants) [text](users) [text](utils) [text](ventas) [text](venv) [text](.env) [text](.gitignore) [text](manage.py) [text](README.md) [text](requirements.txt) [text](train_models.py)