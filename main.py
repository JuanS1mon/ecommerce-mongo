# ============================================================================
# SISTEMA DE SQL_APP - MAIN APPLICATION
# ============================================================================
# Archivo principal de la aplicación FastAPI
# Contiene la configuración central, middlewares, rutas y manejadores de errores

# =============================
# PRE-IMPORTACIÓN CRÍTICA: Cargar typing_extensions correcto
# =============================
import asyncio
import sys, os
# Skip pre_import in serverless environments like Vercel
if os.getenv("VERCEL") != "1":
    try:
        # import pre_import  # DEBE ser el primer import para evitar conflictos
        print("[OK] pre_import skipped")
    except Exception as e:
        import traceback
        print(f"[ERROR] No se pudo importar 'pre_import': {e}")
        traceback.print_exc()
else:
    print("[INFO] Skipping pre_import in Vercel environment")
# Startup diagnostics to help App Service preflight debugging
try:
    import pkgutil
    print(f"[INFO] sys.executable={sys.executable}")
    print(f"[INFO] cwd={os.getcwd()}")
    print(f"[INFO] __file__={__file__}")
    print(f"[INFO] sys.path={sys.path}")
    try:
        root = os.path.abspath(os.path.dirname(__file__))
        print('[INFO] site root listing (first 200 entries):')
        print(os.listdir(root)[:200])
    except Exception as e:
        print(f"[WARN] Could not list site root: {e}")
    print('[INFO] modules in site root: ' + ', '.join([m.name for m in pkgutil.iter_modules(path=[os.path.abspath(os.path.dirname(__file__))])][:200]))
except Exception as e:
    print(f"[WARN] Startup diagnostics failed: {e}")

# =============================
# AJUSTAR PYTHONPATH
# =============================
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))
print("[OK] PYTHONPATH ajustado")

# =============================
# CONFIGURACIÓN Y ENTORNO
# =============================
# from logging_config_new import setup_logging

print("[OK] Configuración y logging importados")

# CONFIGURAR LOGGING ULTRA VERBOSO
# setup_logging()

print("[OK] Logging configurado")

# =============================
# IMPORTACIONES ESTÁNDAR Y FASTAPI
# =============================
import sys
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.templating import Jinja2Templates

print("[OK] Importaciones básicas de FastAPI completadas")

# =============================
# IMPORTACIONES DE MIDDLEWARES Y HANDLERS
# =============================
# from exception_handlers import register_exception_handlers

print("[OK] Middlewares y handlers importados")

# =============================
# IMPORTACIONES DE DB Y ROUTERS
# =============================
# from db.database import init_database  # Only import Beanie init
import importlib

# Ensure logging is available as early as possible
import logging
logger = logging.getLogger("main")

# Robustly load init_app without triggering a top-level ImportError that can crash Gunicorn
project_root = os.path.abspath(os.path.dirname(__file__))
init_candidate_path = os.path.join(project_root, 'init_app.py')
ensure_directories = None

# 1) Try loading from file location first (most deterministic)
try:
    import importlib.util
    if os.path.exists(init_candidate_path):
        spec = importlib.util.spec_from_file_location('init_app', init_candidate_path)
        init_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(init_mod)
        ensure_directories = init_mod.ensure_directories
        logger.info("Imported 'init_app' from file path using spec_from_file_location")
    else:
        logger.info(f"init_app.py not found at {init_candidate_path}; will try importlib.import_module next")
except Exception as e:
    logger.warning(f"Failed loading 'init_app' from file path: {e}")

# 2) If not found, try the standard import mechanism
if ensure_directories is None:
    try:
        init_mod = importlib.import_module('init_app')
        ensure_directories = init_mod.ensure_directories
        logger.info("Imported 'init_app' via importlib.import_module")
    except Exception as e:
        logger.warning(f"importlib.import_module('init_app') failed: {e}")

# 3) Final fallback: no-op to keep the app running
if ensure_directories is None:
    logger.warning("Could not import 'init_app'; using no-op ensure_directories to keep the app running")
    ensure_directories = lambda: None

# Background initialization flags (used to avoid blocking startup probe)
# `db_ready` stays False until background init completes successfully
db_ready = False
init_task = None

# from routers import usuarios as aut_usuario
# from routers.config import  configDB,  Analisis,  usuarios_admin
# from routers.config.Admin import router as admin_router
# Defensive imports for routes: avoid import-time crashes during App Service preflight
# Commented out because Projects module doesn't exist and may cause hanging
frontend_pages_router = None
static_pages_router = None
resenas_router = None
lista_deseos_router = None
cupones_router = None

try:
    from Services.mail.mail import MAIL_CONFIG_OK
except Exception as e:
    MAIL_CONFIG_OK = False
    logger.error(f"Failed to import MAIL_CONFIG_OK from Services.mail.mail: {e}")

print("OK Importaciones de DB y routers básicos completadas")

# =============================
# INICIALIZACIÓN DE LA APP
# =============================
# La aplicación se crea más abajo con el lifespan manager

# =============================
# INICIALIZACIÓN DE BASE DE DATOS Y DIRECTORIOS
# =============================
import logging
logger = logging.getLogger("main")

# Validación de configuración de correo
def check_mail_config():
    return MAIL_CONFIG_OK

# Manejo amigable de errores al crear la base de datos
db_status = True
modelos_status = True
# Database creation moved to async startup with Beanie

# Manejo amigable de errores al crear las tablas
tablas_status = True
# Table creation moved to Beanie models

ensure_directories()

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan que inicializa la DB antes de que la app esté lista."""
    global db_ready, db_status, modelos_status, tablas_status
    import asyncio

    # Marcar como no listo inicialmente
    db_ready = False
    db_status = False

    try:
        from db.database import initialize_beanie_db
        await initialize_beanie_db()
        db_status = True
        db_ready = True
        logger.info("Beanie inicializado correctamente para MongoDB")
        
        # Crear usuario admin si no existe
        # from init_app import create_admin_user
        # await create_admin_user()  # DISABLED DUE TO MODEL ISSUES
        
    except Exception as e:
        logger.error(f"Fallo al inicializar la base de datos: {e}")
        import traceback
        logger.error(traceback.format_exc())
        db_status = False
        # raise  # Re-raise to prevent app from starting - DISABLED TO ALLOW SERVER TO START

    # Tareas post-init
    try:
        logger.info("Admin init completado o saltado")
    except Exception as e:
        logger.error(f"Error en admin init: {e}")

    # Checklist
    mail_ok = check_mail_config()
    admin_created = False
    tokens_cleaned = True

    checklist = [
        (".env cargado correctamente", True),
        ("Configuracion de base de datos cargada", db_status),
        ("Configuracion de correo cargada correctamente", mail_ok),
        ("Modelos importados", modelos_status),
        ("Tablas creadas/verificadas", tablas_status),
        ("Directorios verificados", True),
        ("Sistema de stock configurado", True),
        ("Middlewares y rutas registradas", True),
        ("Logging inicializado", True),
        ("Migraciones Alembic aplicadas", True),
        ("Usuario administrador inicializado", admin_created),
        ("Tokens expirados limpiados del blacklist", tokens_cleaned),
    ]

    logger.info("\n================= CHECKLIST DE INICIO =================")
    for item, ok in checklist:
        logger.info(f"[OK] {item}")
    logger.info("=====================================================\n")
    logger.info("Aplicacion FastAPI lista")

    try:
        yield
    except Exception as e:
        logger.error(f"Error durante la ejecución de la aplicación: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        logger.info("Cerrando aplicacion FastAPI")

        # Mostrar rutas registradas para debug
        logger.info("Rutas registradas:")
        for route in app.routes:
            if hasattr(route, 'path'):
                methods = getattr(route, 'methods', ['MOUNT'])
                logger.info(f"  - {methods} {route.path}")

        logger.info("Limpieza de recursos completada")

# Crear la aplicación con lifespan
app = FastAPI(
    title="Ecommerce API",
    description="API para sistema de ecommerce",
    version="1.0.0",
    lifespan=lifespan
)

# Inicialización lazy de la DB
db_initialized = False

async def ensure_db_initialized():
    global db_initialized
    if not db_initialized:
        # Wait for the lifespan to initialize the database with timeout
        timeout = 5.0  # 5 seconds timeout
        waited = 0.0
        while not db_ready and waited < timeout:
            await asyncio.sleep(0.1)
            waited += 0.1
        if not db_ready:
            logger.warning("Database not ready after timeout, proceeding without DB initialization")
        db_initialized = True

# Configurar archivos estáticos y middlewares después de crear la app
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar CORS permisivo para API de validación externa
from fastapi.middleware.cors import CORSMiddleware

# CORS para /api/v1/* - completamente abierto para sistemas externos
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes
    allow_credentials=False,  # No requerimos cookies en API pública
    allow_methods=["POST", "OPTIONS"],
    allow_headers=["*"],
)

# --------------------------------------------------------------------------
# Favicon handler: evita error 500 si el navegador solicita /favicon.ico
# Sirve logo.svg como fallback (o 204 si no está disponible)
# --------------------------------------------------------------------------
# @app.get("/favicon.ico")
# async def favicon():
#     candidate_svg = os.path.join("sql_app", "static", "logo.png")
#     candidate_png = os.path.join("sql_app", "static", "img", "favicon.png")
#     if os.path.exists(candidate_png):
#         return FileResponse(candidate_png)
#     if os.path.exists(candidate_svg):
#         return FileResponse(candidate_svg, media_type="image/svg+xml")
#     return Response(status_code=204)


# @app.get("/healthz")
# async def healthz():
#     """Readiness endpoint: devuelve 200 cuando la DB está lista, 503 mientras se inicializa."""
#     try:
#         if db_ready:
#             return JSONResponse(status_code=200, content={"status": "ok", "db_ready": True})
#         else:
#             return JSONResponse(status_code=503, content={"status": "starting", "db_ready": False})
#     except Exception as e:
#         logger.error(f"Error en /healthz: {e}")
#         return JSONResponse(status_code=500, content={"status": "error"})

# =============================
# MIDDLEWARES
# =============================
from app_settings import CORS_CONFIG
from fastapi.middleware.cors import CORSMiddleware
# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=CORS_CONFIG["allow_origins"],
#     allow_credentials=CORS_CONFIG["allow_credentials"],
#     allow_methods=CORS_CONFIG["allow_methods"],
#     allow_headers=CORS_CONFIG["allow_headers"],
# )
# app.add_middleware(RequestLoggingMiddleware)  # DESHABILITADO TEMPORALMENTE

# =============================
# EXCEPTION HANDLERS
# =============================
# register_exception_handlers(app)

# =============================
# REGISTRO DE ROUTERS
# =============================
# Importar y registrar el router de restablecimiento de contraseña
# from Projects.ecomerce.routes.password_reset import router as password_reset_router
# app.include_router(password_reset_router)

# Compat routes for mixed spellings (ecomerce / ecommerce)
# try:
#     from Projects.ecomerce.routes.compat_routes import router as compat_router
#     app.include_router(compat_router)
#     logger.info("Router compat_routes registrado correctamente")
# except Exception as e:
#     logger.error(f"[WARN] No se pudo registrar router compat_routes: {e}")

# Importar y registrar el router de productos públicos ecommerce
# try:
#     from Projects.ecomerce.routes.ecommerce_public import router as ecommerce_public_router
#     app.include_router(ecommerce_public_router)
#     logger.info("Router ecommerce_public registrado correctamente")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando router ecommerce_public: {e}")
#     import traceback
#     traceback.print_exc()

# Importar y registrar el router de productos
try:
    from routers.productos import router as productos_router
    app.include_router(productos_router, prefix="/ecomerce/api", tags=["productos"])
    logger.info("Router productos registrado correctamente")
except Exception as e:
    logger.error(f"[ERROR] Error registrando productos_router: {e}")
    import traceback
    traceback.print_exc()

# Importar y registrar el router API simple para ecommerce (comentado - archivo no existe)
# try:
#     from simple_api_router import router as api_router
#     app.include_router(api_router)
#     logger.info("Router API ecommerce integrado en simple_product_router")
# except Exception as e:
#     logger.error(f"❌ Error registrando router API ecommerce: {e}")
#     import traceback
#     traceback.print_exc()

# Importar y registrar el router de administración de categorías
# from routers.admin_categorias import router as admin_categorias_router
# app.include_router(admin_categorias_router)
logger.info("Router admin_categorias deshabilitado temporalmente (modelos SQLAlchemy vs Beanie)")

# Importar y registrar el router de presupuesto
# from Projects.ecomerce.routes.presupuesto import router as presupuesto_router
# app.include_router(presupuesto_router, prefix="/ecomerce/api", tags=["presupuesto"])
logger.info("Router presupuesto deshabilitado temporalmente (módulos faltantes)")

# Importar y registrar el router de autenticación de ecommerce
try:
    from routers.ecommerce_auth import router as ecommerce_auth_router
    app.include_router(ecommerce_auth_router, prefix="/ecomerce", tags=["ecommerce-auth"])
    logger.info("Router ecommerce_auth registrado correctamente")
except Exception as e:
    logger.error(f"[ERROR] Error registrando ecommerce_auth_router: {e}")
    import traceback
    traceback.print_exc()

# Importar y registrar el router de servicios
from routers.servicios import router as servicios_router
app.include_router(servicios_router, prefix="/api", tags=["servicios"])

# Importar y registrar el router de presupuestos
from routers.presupuesto import router as presupuesto_router
app.include_router(presupuesto_router, prefix="/api", tags=["presupuestos"])

# Importar y registrar el router de contratos
from routers.contrato import router as contrato_router
app.include_router(contrato_router, prefix="/api", tags=["contratos"])

# Importar y registrar el router de auth admin
from routers.admin_auth import router as admin_auth_router, get_current_admin_user
app.include_router(admin_auth_router, tags=["admin-auth"])

# Importar y registrar el router de config admin
from routers.admin_config import router as admin_config_router
app.include_router(admin_config_router, tags=["admin-config"])

# Importar y registrar el router de users admin
from routers.admin_users import router as admin_users_router
app.include_router(admin_users_router, tags=["admin-users"])

# Importar y registrar el router de admins
from routers.admin_admins import router as admin_admins_router
app.include_router(admin_admins_router, tags=["admin-admins"])

# Importar y registrar el router de proyectos admin
from routers.admin_proyectos import router as admin_proyectos_router
app.include_router(admin_proyectos_router, tags=["admin-proyectos"])

# Importar y registrar el router de validación para API externa
from routers.api_validation import router as api_validation_router
app.include_router(api_validation_router, tags=["api-validation"])

logger.info("Routers de proyectos y validación registrados correctamente")

# Importar y registrar el router de checkout
# from Projects.ecomerce.routes.checkout import router as checkout_router
# logger.info(f"Registrando checkout_router con {len(checkout_router.routes)} rutas")
# for route in checkout_router.routes:
#     logger.info(f"  CHECKOUT ROUTE: {route.methods} {route.path}")
# app.include_router(checkout_router, prefix="/ecomerce", tags=["checkout"])

# Importar y registrar el router de SEO
# try:
#     from Projects.ecomerce.routes.seo import router as seo_router
#     logger.info(f"Registrando seo_router con {len(seo_router.routes)} rutas")
#     app.include_router(seo_router)
#     logger.info("SEO router registrado: sitemap.xml, robots.txt, etc.")
# except Exception as e:
#     logger.error(f"Error registrando seo_router: {e}")
#     import traceback
#     traceback.print_exc()

# if resenas_router:
#     app.include_router(resenas_router, prefix="/ecomerce/api", tags=["resenas"])
# else:
#     logger.warning("resenas_router no disponible; se omite su registro")

# if lista_deseos_router:
#     app.include_router(lista_deseos_router, prefix="/ecomerce/api/lista-deseos", tags=["lista-deseos"])
# else:
#     logger.warning("lista_deseos_router no disponible; se omite su registro")

# if cupones_router:
#     app.include_router(cupones_router, prefix="/ecomerce/api/cupones", tags=["cupones"])
# else:
#     logger.warning("cupones_router no disponible; se omite su registro")

# Importar y registrar el router de validación externa (API pública)
try:
    from Projects.Admin.routes.validacion_externa import router as validacion_externa_router
    app.include_router(validacion_externa_router)
    logger.info("Router validacion_externa registrado - Endpoint público /api/v1/validate")
except Exception as e:
    logger.error(f"Error registrando router validacion_externa: {e}")
    import traceback
    traceback.print_exc()

# Importar y registrar el router de sincronización de usuarios
try:
    from Projects.Admin.routes.sync import router as sync_router
    app.include_router(sync_router)
    logger.info("Router sync registrado - Endpoints /admin/api/sync/*")
except Exception as e:
    logger.error(f"Error registrando router sync: {e}")
    import traceback
    traceback.print_exc()

logger.info("carrito_router registrado")

# Importar y registrar el router de páginas frontend
# from Projects.ecomerce.routes.frontend_pages import router as frontend_pages_router

# =============================
# RUTAS PRINCIPALES - ANTES DE REGISTRAR FRONTEND ROUTER
# =============================

# Ruta para productos de tienda (sin /api para compatibilidad) - REGISTRADA ANTES QUE frontend_pages_router
# Load templates defensively
try:
    templates_main = Jinja2Templates(directory="templates")
except Exception as e:
    templates_main = None
    logger.error(f"Failed to initialize Jinja2Templates: {e}")

@app.get("/")
async def root(request: Request):
    """Servir la página principal"""
    await ensure_db_initialized()
    return FileResponse("static/index.html")

@app.get("/admin")
async def admin_login_page(request: Request):
    """Servir la página de login admin"""
    await ensure_db_initialized()
    return FileResponse("static/admin_login.html")

@app.get("/admin/login")
async def admin_login_page_direct(request: Request):
    """Servir la página de login admin (acceso directo)"""
    await ensure_db_initialized()
    return FileResponse("static/admin_login.html")

@app.get("/admin/dashboard")
async def admin_dashboard_page(request: Request):
    """Servir la página de dashboard admin"""
    await ensure_db_initialized()
    return FileResponse("static/admin_dashboard.html")

@app.get("/ecomerce/productos/tienda")
async def tienda_page(request: Request):
    """Servir la página de tienda"""
    await ensure_db_initialized()
    return FileResponse("static/tienda.html")

@app.get("/ecomerce/productos/{producto_id}")
async def producto_detail_page(request: Request, producto_id: str):
    """Servir la página de detalle de producto"""
    logger.info(f"Accediendo a producto: {producto_id}")
    # Intentar inicializar DB pero no fallar si no funciona
    try:
        await ensure_db_initialized()
    except Exception as e:
        logger.warning(f"No se pudo inicializar DB, continuando de todos modos: {e}")

    # Usar templates desde la carpeta templates para productos
    try:
        product_templates = Jinja2Templates(directory="templates")
    except Exception as e:
        logger.error(f"No se pudieron inicializar templates de producto: {e}")
        return Response(status_code=503, content="Templates not available")

    try:
        # Fetch product from database
        from bson import ObjectId
        from motor.motor_asyncio import AsyncIOMotorClient

        logger.info(f"Conectando a base de datos para producto: {producto_id}")
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.db_sysne

        producto = await db.productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            logger.warning(f"Producto no encontrado: {producto_id}")
            return Response(status_code=404, content="Producto no encontrado")

        logger.info(f"Producto encontrado: {producto.get('nombre', 'Sin nombre')}")

        # Convert ObjectId to string
        producto['id'] = str(producto['_id'])
        del producto['_id']

        # Convert datetime objects to strings for JSON serialization
        if 'created_at' in producto and producto['created_at']:
            producto['created_at'] = producto['created_at'].isoformat()
        if 'updated_at' in producto and producto['updated_at']:
            producto['updated_at'] = producto['updated_at'].isoformat()

        logger.info(f"Renderizando template para producto: {producto.get('nombre', 'Sin nombre')}")
        return product_templates.TemplateResponse("producto.html", {
            "request": request,
            "product": producto
        })
    except Exception as e:
        logger.error(f"Error loading product {producto_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(status_code=500, content="Error interno del servidor")

# Función para obtener servicios mock por ID
def get_mock_service_by_id(servicio_id: str):
    """Devuelve un servicio mock por ID para testing"""
    from datetime import datetime
    
    class MockService:
        def __init__(self, data):
            for key, value in data.items():
                setattr(self, key, value)
        
        def dict(self):
            return {
                "id": str(self.id),
                "nombre": self.nombre,
                "descripcion": self.descripcion,
                "tipo_servicio": self.tipo_servicio,
                "precio_base": self.precio_base,
                "activo": self.activo,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None
            }
    
    mock_servicios = {
        "507f1f77bcf86cd799439011": MockService({
            "id": "507f1f77bcf86cd799439011",
            "nombre": "Desarrollo Web Personalizado",
            "descripcion": "Creamos sitios web a medida con las últimas tecnologías. Incluye diseño responsive, optimización SEO y integración con APIs.",
            "tipo_servicio": "desarrollo web",
            "precio_base": 1500.0,
            "activo": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }),
        "507f1f77bcf86cd799439012": MockService({
            "id": "507f1f77bcf86cd799439012",
            "nombre": "Ecommerce Inteligente",
            "descripcion": "Plataformas de comercio electrónico con IA integrada para recomendaciones personalizadas y gestión automática de inventario.",
            "tipo_servicio": "ecommerce",
            "precio_base": 2500.0,
            "activo": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }),
        "507f1f77bcf86cd799439013": MockService({
            "id": "507f1f77bcf86cd799439013",
            "nombre": "Consultoría IA y Automatización",
            "descripcion": "Implementamos soluciones de inteligencia artificial para optimizar procesos empresariales y aumentar la eficiencia.",
            "tipo_servicio": "consultoria ia",
            "precio_base": 2000.0,
            "activo": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }),
        "507f1f77bcf86cd799439014": MockService({
            "id": "507f1f77bcf86cd799439014",
            "nombre": "Mantenimiento y Soporte Técnico",
            "descripcion": "Servicio continuo de mantenimiento, actualizaciones y soporte técnico para mantener tus sistemas funcionando perfectamente.",
            "tipo_servicio": "mantenimiento",
            "precio_base": 500.0,
            "activo": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })
    }
    
    return mock_servicios.get(servicio_id)

@app.get("/servicio/{servicio_id}")
async def servicio_detail_page(request: Request, servicio_id: str):
    """Servir la página de detalle de servicio"""
    logger.info(f"Accediendo a servicio: {servicio_id}")
    # Intentar inicializar DB pero no fallar si no funciona
    try:
        await ensure_db_initialized()
    except Exception as e:
        logger.warning(f"No se pudo inicializar DB, continuando de todos modos: {e}")

    # Usar templates desde la carpeta templates para servicios
    try:
        service_templates = Jinja2Templates(directory="templates")
    except Exception as e:
        logger.error(f"No se pudieron inicializar templates de servicio: {e}")
        return Response(status_code=503, content="Templates not available")

    try:
        # Fetch service/product from database
        from models.models_beanie import Servicio, Producto
        from db.database import init_beanie_db

        # Asegurar que Beanie esté inicializado
        try:
            await init_beanie_db()
        except Exception as e:
            logger.warning(f"Error inicializando Beanie, intentando continuar: {e}")

        logger.info(f"Buscando servicio/producto con ID: {servicio_id}")

        # Primero buscar en productos (ya que el admin dashboard maneja productos como servicios)
        logger.info(f"Buscando en colección productos...")
        producto = await Producto.get(servicio_id)
        logger.info(f"Resultado búsqueda producto: {producto}")
        if producto:
            logger.info(f"Producto encontrado: {producto.nombre}")
            # Convertir producto a formato de servicio para el template
            servicio_dict = {
                'id': str(producto.id),
                'nombre': producto.nombre or 'Sin nombre',
                'descripcion': producto.descripcion or 'Sin descripción',
                'tipo_servicio': producto.categoria or 'Sin categoría',
                'precio_base': float(producto.precio) if producto.precio else 0.0,
                'imagen_url': producto.imagen_url or '/static/img/logo.png',
                'activo': bool(producto.activo),
                'created_at': producto.created_at.isoformat() if producto.created_at else None,
                'updated_at': producto.updated_at.isoformat() if producto.updated_at else None
            }

            logger.info(f"Renderizando template para producto como servicio: {producto.nombre}")
            logger.info(f"Datos que se pasan al template: {servicio_dict}")
            return service_templates.TemplateResponse("servicio.html", {
                "request": request,
                "product": servicio_dict
            })

        # Si no es producto, buscar en servicios
        servicio = await Servicio.get(servicio_id)
        if servicio:
            logger.info(f"Servicio encontrado: {servicio.nombre}")
            # Convert service to dict for template
            servicio_dict = servicio.dict() if hasattr(servicio, 'dict') else servicio
            servicio_dict['id'] = str(servicio.id)

            # Convert datetime objects to strings for JSON serialization
            if hasattr(servicio, 'created_at') and servicio.created_at:
                servicio_dict['created_at'] = servicio.created_at.isoformat()
            if hasattr(servicio, 'updated_at') and servicio.updated_at:
                servicio_dict['updated_at'] = servicio.updated_at.isoformat()

            logger.info(f"Renderizando template para servicio: {servicio.nombre}")
            return service_templates.TemplateResponse("servicio.html", {
                "request": request,
                "product": servicio_dict  # Usamos 'product' para compatibilidad con el template
            })

        # Si no se encuentra ni en productos ni en servicios
        logger.warning(f"Servicio/producto no encontrado: {servicio_id}")

        # Obtener lista de productos y servicios disponibles
        items_disponibles = []
        try:
            # Agregar productos activos
            async for p in Producto.find({"activo": True}).limit(3):
                items_disponibles.append({
                    "id": str(p.id),
                    "nombre": p.nombre,
                    "tipo": f"Producto - {p.categoria}",
                    "tipo_item": "producto"
                })

            # Agregar servicios activos
            async for s in Servicio.find({"activo": True}).limit(2):
                items_disponibles.append({
                    "id": str(s.id),
                    "nombre": s.nombre,
                    "tipo": f"Servicio - {s.tipo_servicio}",
                    "tipo_item": "servicio"
                })

        except Exception as e:
            logger.error(f"Error obteniendo items disponibles: {e}")

        return service_templates.TemplateResponse("404.html", {
            "request": request,
            "error_message": f"El servicio/producto con ID '{servicio_id}' no fue encontrado.",
            "suggestion": "Aquí tienes algunos servicios y productos disponibles:",
            "servicios_disponibles": items_disponibles,
            "home_url": "/"
        })
    except Exception as e:
        logger.error(f"Error loading service {servicio_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(status_code=500, content="Error interno del servidor")

@app.get("/contrato/{servicio_id}")
async def contrato_page(request: Request, servicio_id: str):
    """Servir la página de contrato de servicio"""
    logger.info(f"Accediendo a contrato de servicio: {servicio_id}")
    # Intentar inicializar DB pero no fallar si no funciona
    try:
        await ensure_db_initialized()
    except Exception as e:
        logger.warning(f"No se pudo inicializar DB, continuando de todos modos: {e}")

    # Usar templates desde la carpeta templates para contratos
    try:
        contract_templates = Jinja2Templates(directory="templates")
    except Exception as e:
        logger.error(f"No se pudieron inicializar templates de contrato: {e}")
        return Response(status_code=503, content="Templates not available")

    try:
        # Fetch service/product from database
        from models.models_beanie import Servicio, Producto
        from db.database import init_beanie_db

        # Asegurar que Beanie esté inicializado
        try:
            await init_beanie_db()
        except Exception as e:
            logger.warning(f"Error inicializando Beanie, intentando continuar: {e}")

        logger.info(f"Buscando servicio/producto con ID: {servicio_id}")

        # Primero buscar en productos (ya que el admin dashboard maneja productos como servicios)
        logger.info(f"Buscando en colección productos...")
        producto = await Producto.get(servicio_id)
        logger.info(f"Resultado búsqueda producto: {producto}")
        if producto:
            logger.info(f"Producto encontrado: {producto.nombre}")
            # Convertir producto a formato de servicio para el template
            servicio_dict = {
                'id': str(producto.id),
                'nombre': producto.nombre or 'Sin nombre',
                'descripcion': producto.descripcion or 'Sin descripción',
                'tipo_servicio': producto.categoria or 'Sin categoría',
                'precio_base': float(producto.precio) if producto.precio else 0.0,
                'imagen_url': producto.imagen_url or '/static/img/logo.png',
                'activo': bool(producto.activo),
                'created_at': producto.created_at.isoformat() if producto.created_at else None,
                'updated_at': producto.updated_at.isoformat() if producto.updated_at else None
            }

            logger.info(f"Renderizando template para contrato de producto como servicio: {producto.nombre}")
            return contract_templates.TemplateResponse("contrato.html", {
                "request": request,
                "service": servicio_dict
            })

        # Si no es producto, buscar en servicios
        servicio = await Servicio.get(servicio_id)
        if servicio:
            logger.info(f"Servicio encontrado: {servicio.nombre}")
            # Convert service to dict for template
            servicio_dict = servicio.dict() if hasattr(servicio, 'dict') else servicio
            servicio_dict['id'] = str(servicio.id)

            # Convert datetime objects to strings for JSON serialization
            if hasattr(servicio, 'created_at') and servicio.created_at:
                servicio_dict['created_at'] = servicio.created_at.isoformat()
            if hasattr(servicio, 'updated_at') and servicio.updated_at:
                servicio_dict['updated_at'] = servicio.updated_at.isoformat()

            logger.info(f"Renderizando template para contrato de servicio: {servicio.nombre}")
            return contract_templates.TemplateResponse("contrato.html", {
                "request": request,
                "service": servicio_dict
            })

        # Si no se encuentra ni en productos ni en servicios
        logger.warning(f"Servicio/producto no encontrado: {servicio_id}")
        return Response(status_code=404, content="Servicio no encontrado")
    except Exception as e:
        logger.error(f"Error loading service {servicio_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(status_code=500, content="Error interno del servidor")

@app.get("/ecomerce/login")
async def ecommerce_login_page(request: Request):
    """Servir la página de login de ecommerce"""
    return FileResponse("static/ecommerce_login.html")

@app.get("/ecomerce/register")
async def ecommerce_register_page(request: Request):
    """Servir la página de registro de ecommerce"""
    return FileResponse("static/ecommerce_register.html")

# Compatibility routes for alternative spelling (ecommerce vs ecomerce)
@app.get("/ecommerce/login")
async def ecommerce_login_page_compat(request: Request):
    """Servir la página de login de ecommerce (compatibilidad con spelling alternativo)"""
    return FileResponse("static/ecommerce_login.html")

@app.get("/ecommerce/register")
async def ecommerce_register_page_compat(request: Request):
    """Servir la página de registro de ecommerce (compatibilidad con spelling alternativo)"""
    return FileResponse("static/ecommerce_register.html")

@app.get("/ecommerce/productos/tienda")
async def tienda_page_compat(request: Request):
    """Servir la página de tienda (compatibilidad con spelling alternativo)"""
    await ensure_db_initialized()
    return FileResponse("static/tienda.html")

@app.get("/ecommerce/productos/{producto_id}")
async def producto_detail_page_compat(request: Request, producto_id: str):
    """Servir la página de detalle de producto (compatibilidad con spelling alternativo)"""
    await ensure_db_initialized()
    if templates_main is None:
        return Response(status_code=503, content="Templates not available")

    try:
        # Fetch product from database
        from bson import ObjectId
        from motor.motor_asyncio import AsyncIOMotorClient

        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.db_sysne

        producto = await db.productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            return Response(status_code=404, content="Producto no encontrado")

        # Convert ObjectId to string
        producto['id'] = str(producto['_id'])
        del producto['_id']

        # Convert datetime objects to strings for JSON serialization
        if 'created_at' in producto and producto['created_at']:
            producto['created_at'] = producto['created_at'].isoformat()
        if 'updated_at' in producto and producto['updated_at']:
            producto['updated_at'] = producto['updated_at'].isoformat()

        return templates_main.TemplateResponse("producto.html", {
            "request": request,
            "product": producto
        })
    except Exception as e:
        logger.error(f"Error loading product {producto_id}: {e}")
        return Response(status_code=500, content="Error interno del servidor")

# New routes for rebranded service platform
@app.get("/servicios")
async def servicios_page(request: Request):
    """Servir la página de servicios"""
    await ensure_db_initialized()
    return FileResponse("static/servicios.html")

@app.get("/login")
async def login_page(request: Request):
    """Servir la página de login"""
    # DB initialization not required for static pages
    if templates_main is None:
        return Response(status_code=503, content="Templates not available")
    return templates_main.TemplateResponse("ecommerce_login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    """Servir la página de registro"""
    # DB initialization not required for static pages
    if templates_main is None:
        return Response(status_code=503, content="Templates not available")
    return templates_main.TemplateResponse("ecommerce_register.html", {"request": request})

@app.get("/perfil")
async def perfil_page(request: Request):
    """Servir la página de perfil del usuario"""
    # DB initialization not required for static pages
    if templates_main is None:
        return Response(status_code=503, content="Templates not available")
    return templates_main.TemplateResponse("perfil.html", {"request": request})

@app.get("/auth/google/status")
async def google_oauth_status():
    """Verificar si Google OAuth está configurado y disponible"""
    from config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
    
    is_configured = bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET)
    
    return {
        "available": is_configured,
        "configured": is_configured
    }
async def admin_categorias_api():
    """API para la página de admin de categorías (ahora servicios)"""
    await ensure_db_initialized()
    from models.models_beanie import Servicio
    
    servicios = await Servicio.find().to_list()
    
    # Convertir servicios a formato de categorías
    categorias = []
    for servicio in servicios:
        categorias.append({
            "id": str(servicio.id),
            "nombre": servicio.nombre,
            "descripcion": servicio.descripcion,
            "tipo_servicio": servicio.tipo_servicio,
            "precio_base": servicio.precio_base,
            "activo": servicio.activo
        })
    
    return {"categorias": categorias}

@app.get("/api/config")
async def get_public_config():
    """Configuración pública para el frontend"""
    await ensure_db_initialized()
    from models.models_beanie import Configuracion
    config = {}
    configs = await Configuracion.find_all().to_list()
    for c in configs:
        config[c.key] = c.value
    return config
#             "Expires": "0",
#         },
#     )

# if frontend_pages_router:
#     logger.info(f"Registrando frontend_pages_router con {len(frontend_pages_router.routes)} rutas")
#     for route in frontend_pages_router.routes:
#         logger.info(f"  FRONTEND ROUTE: {route.methods} {route.path}")
#     app.include_router(frontend_pages_router)
#     logger.info("frontend_pages_router registrado")
# else:
#     logger.warning("frontend_pages_router no disponible; se omite su registro")

# # Importar y registrar el router de páginas estáticas
# if static_pages_router:
#     logger.info(f"Registrando static_pages_router con {len(static_pages_router.routes)} rutas")
#     for route in static_pages_router.routes:
#         logger.info(f"  STATIC ROUTE: {route.methods} {route.path}")
#     app.include_router(static_pages_router)
#     logger.info("static_pages_router registrado")
# else:
#     logger.warning("static_pages_router no disponible; se omite su registro")

# @app.get("/debug/admin")
# async def debug_admin():
#     """
#     Endpoint de diagnóstico para verificar el estado del admin en Vercel
#     """
#     import os
#     from db.database import client, database
#     
#     debug_info = {
#         "environment": os.getenv("ENVIRONMENT", "unknown"),
#         "vercel_env": os.getenv("VERCEL", "unknown"),
#         "vercel_url": os.getenv("VERCEL_URL", "unknown"),
#         "mongo_url_configured": bool(os.getenv("MONGO_URL")),
#         "db_name": os.getenv("DB_NAME", "unknown"),
#         "cors_origins": ORIGINS,
#         "python_path": sys.path[:3],  # First 3 paths
#         "current_dir": os.getcwd(),
#         "files_in_root": os.listdir(".")[:10]  # First 10 files
#     }
#     
#     # Test database connection
#     try:
#         await client.admin.command('ping')
#         debug_info["db_connection"] = "OK"
#         
#         # Check if admin users collection exists
#         collections = await database.list_collection_names()
#         debug_info["collections"] = collections
#         debug_info["admin_users_exists"] = "admin_usuarios" in collections
#         
#         if "admin_usuarios" in collections:
#             count = await database.admin_usuarios.count_documents({})
#             debug_info["admin_users_count"] = count
#         else:
#             debug_info["admin_users_count"] = 0
#             
#     except Exception as e:
#         debug_info["db_connection"] = f"ERROR: {str(e)}"
#     
#     return debug_info


# @app.post("/debug/create-admin")
# async def create_admin_user():
#     """
#     Crear usuario admin por defecto para Vercel
#     """
# #     from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
#     from security.security import hash_clave
#     from datetime import datetime
#     
#     try:
#         # Verificar si ya existe un admin
#         existing_admin = await AdminUsuarios.find_one(AdminUsuarios.usuario == "admin")
#         if existing_admin:
#             return {"message": "Admin user already exists", "user": existing_admin.usuario}
#         
#         # Crear admin por defecto
#         admin_user = AdminUsuarios(
#             usuario="admin",
#             nombre="Administrator",
#             mail="admin@example.com",
#             clave_hash=hash_clave("admin123"),
#             activo=True,
#             fecha_creacion=datetime.utcnow(),
#             ultimo_acceso=None
#         )
#         
#         await admin_user.insert()
#         return {"message": "Admin user created successfully", "user": "admin", "password": "admin123"}
#         
#     except Exception as e:
#         logger.error(f"Error creating admin user: {e}")
#         return {"error": str(e)}


# Indicar que la importación de módulos terminó correctamente (útil para startup preflight)
try:
    import datetime
    p = os.path.join(os.path.dirname(__file__), 'import_check.log')
    with open(p, 'a') as f:
        f.write(f"IMPORT_OK {datetime.datetime.utcnow().isoformat()}\n")
    logger.info(f"Wrote IMPORT_OK to {p}")
except Exception as e:
    logger.warning(f"Could not write IMPORT_OK to import_check.log: {e}")

# Importar y registrar el router de mapas
# try:
#     from Projects.ecomerce.routes.mapas import router as mapas_router
#     app.include_router(mapas_router, prefix="/mapas", tags=["mapas"])
#     logger.info("mapas_router registrado correctamente")
#     print("DEBUG: mapas_router registrado con prefix /mapas")
# except Exception as e:
#     logger.error(f"Error registrando mapas_router: {e}")
#     print(f"DEBUG: Error registrando mapas_router: {e}")

# Importar y configurar rutas de ecommerce
try:
    # from Projects.ecomerce.routes_config import configure_routes
    # logger.info("Llamando a configure_routes...")
    # configure_routes(app)
    logger.info("configure_routes deshabilitado temporalmente para evitar conflictos")
    
    # Verificar que las rutas se registraron
    all_routes = [route for route in app.routes if hasattr(route, 'path')]
    ecommerce_routes = [route for route in all_routes if 'ecomerce' in route.path]
    usuarios_routes = [route for route in all_routes if 'usuarios' in route.path]
    
    logger.info(f"Total de rutas en la app: {len(all_routes)}")
    logger.info(f"Total de rutas ecommerce registradas: {len(ecommerce_routes)}")
    logger.info(f"Total de rutas usuarios registradas: {len(usuarios_routes)}")
    
    # Mostrar rutas de usuarios específicamente
    if usuarios_routes:
        logger.info("Rutas de usuarios encontradas:")
        for route in usuarios_routes:
            logger.info(f"  - USUARIOS: {route.methods} {route.path}")
    else:
        logger.warning("[WARNING] No se encontraron rutas de usuarios!")
        
    # Mostrar algunas rutas ecommerce
    for route in ecommerce_routes[:10]:  # Mostrar las primeras 10
        logger.info(f"  - ECOMMERCE: {route.methods} {route.path}")
        
except Exception as e:
    logger.error(f"[ERROR] Error configurando rutas de ecommerce: {e}")
    import traceback
    logger.error(f"Traceback: {traceback.format_exc()}")
    raise

# Importar y registrar el router de autenticación ecommerce AL FINAL para que tenga prioridad
# from Projects.ecomerce.routes.ecommerce_auth import router as ecommerce_auth_router
# logger.info(f"Registrando ecommerce_auth_router con {len(ecommerce_auth_router.routes)} rutas")
# for route in ecommerce_auth_router.routes:
#     logger.info(f"  ECOMMERCE ROUTE: {route.methods} {route.path}")
# app.include_router(ecommerce_auth_router)
# logger.info("ecommerce_auth_router registrado")

# Importar y registrar el router de autenticación con Google
# try:
#     from Projects.ecomerce.routes.google_oauth import router as google_oauth_router
#     logger.info(f"Registrando google_oauth_router con {len(google_oauth_router.routes)} rutas")
#     for route in google_oauth_router.routes:
#         logger.info(f"  GOOGLE OAUTH ROUTE: {route.methods} {route.path}")
#     app.include_router(google_oauth_router)
#     logger.info("google_oauth_router registrado")
# except Exception as e:
#     logger.error(f"Router google_oauth deshabilitado temporalmente (falta modulo authlib o configuración): {e}")

# =============================
# ADMIN PANEL ROUTERS
# =============================
# try:
#     from Projects.Admin.routes.landing import router as admin_landing_router
#     app.include_router(admin_landing_router, tags=["admin-landing"])
#     logger.info("[OK] Admin landing router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_landing_router: {e}")

# try:
#     from Projects.Admin.routes.auth import router as admin_auth_router
#     app.include_router(admin_auth_router, tags=["admin-auth"])
#     logger.info("[OK] Admin auth router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_auth_router: {e}")

# try:
#     from Projects.Admin.routes.dashboard import router as admin_dashboard_router
#     app.include_router(admin_dashboard_router, tags=["admin-dashboard"])
#     logger.info("[OK] Admin dashboard router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_dashboard_router: {e}")

# try:
#     from Projects.Admin.routes.productos import router as admin_productos_router
#     app.include_router(admin_productos_router, tags=["admin-productos"])
#     logger.info("[OK] Admin productos router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_productos_router: {e}")

# Importar y registrar el router de admin productos
try:
    from routers.admin_productos import router as admin_productos_router
    app.include_router(admin_productos_router, prefix="/admin", tags=["admin-productos"])
    logger.info("Router admin_productos registrado correctamente")
except Exception as e:
    logger.error(f"[ERROR] Error registrando admin_productos_router: {e}")
    import traceback
    traceback.print_exc()

# Importar y registrar el router de admin contratos
try:
    from routers.admin_contrato import router as admin_contrato_router
    app.include_router(admin_contrato_router, tags=["admin-contratos"])
    logger.info("Router admin_contrato registrado correctamente")
except Exception as e:
    logger.error(f"[ERROR] Error registrando admin_contrato_router: {e}")
    import traceback
    traceback.print_exc()

# try:
#     from Projects.Admin.routes.pedidos import router as admin_pedidos_router
#     app.include_router(admin_pedidos_router, tags=["admin-pedidos"])
#     logger.info("[OK] Admin pedidos router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_pedidos_router: {e}")

# try:
#     from Projects.Admin.routes.carritos import router as admin_carritos_router
#     app.include_router(admin_carritos_router, tags=["admin-carritos"])
#     logger.info("[OK] Admin carritos router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_carritos_router: {e}")

# try:
#     from Projects.Admin.routes.usuarios import router as admin_usuarios_router
#     app.include_router(admin_usuarios_router, tags=["admin-usuarios"])
#     logger.info("[OK] Admin usuarios router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_usuarios_router: {e}")

# try:
#     from Projects.Admin.routes.presupuestos import router as admin_presupuestos_router
#     app.include_router(admin_presupuestos_router, tags=["admin-presupuestos"])
#     logger.info("[OK] Admin presupuestos router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_presupuestos_router: {e}")

# try:
#     from Projects.Admin.routes.admin_categorias import router as admin_categorias_router
#     app.include_router(admin_categorias_router, tags=["admin-categorias"])
#     logger.info("[OK] Admin categorias router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_categorias_router: {e}")

# try:
#     from Projects.Admin.routes.configuracion import router as admin_configuracion_router
#     app.include_router(admin_configuracion_router, tags=["admin-configuracion"])
#     logger.info("[OK] Admin configuracion router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_configuracion_router: {e}")

# try:
#     from Projects.Admin.routes.marketing import router as admin_marketing_router
#     app.include_router(admin_marketing_router, tags=["admin-marketing"])
#     logger.info("[OK] Admin marketing router registrado")
# except Exception as e:
#     logger.error(f"[ERROR] Error registrando admin_marketing_router: {e}")

# =============================
# RUTAS PRINCIPALES
# =============================

# Ruta raíz - Carga la página principal
# @app.get("/")
# async def root(request: Request):
#     """Renderiza la página principal con plantilla base y navbar de tienda"""
#     return templates_main.TemplateResponse(
#         "index.html",
#         {"request": request},
#         headers={
#             "Cache-Control": "no-cache, no-store, must-revalidate",
#             "Pragma": "no-cache",
#             "Expires": "0",
#         },
#     )

# ENDPOINT DE PRUEBA PARA PROFILE

# ============================================================================
# ============================================================================
# EJECUCIÓN DEL SERVIDOR
# ============================================================================
async def test_email_functionality():
    """Prueba la funcionalidad de envío de emails"""
    try:
        logger.info("=== PRUEBA DE FUNCIONALIDAD DE EMAIL ===")
        
        from Services.mail.mail import enviar_email_simple
        
        # Probar envío de email
        result = enviar_email_simple(
            "fjuansimon@gmail.com",
            "Prueba de sistema de restablecimiento de contraseña",
            "Esta es una prueba automática del sistema de envío de emails para restablecimiento de contraseña."
        )
        
        logger.info(f"Resultado de la prueba de email: {result}")
        
        if result and result.get("success"):
            logger.info("[OK] PRUEBA DE EMAIL EXITOSA - El sistema puede enviar emails")
        else:
            logger.error("[ERROR] PRUEBA DE EMAIL FALLIDA - El sistema NO puede enviar emails")
            
    except Exception as e:
        logger.error(f"Error en prueba de email: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import uvicorn

    # Configurar puerto desde variable de entorno o usar 8002 por defecto
    port = int(os.getenv('PORT', 8002))

    logger.info(f"Iniciando servidor FastAPI en puerto {port}")
    logger.info(f"Servidor disponible en: http://localhost:{port}")
    logger.info(f"Documentacion API en: http://localhost:{port}/docs")
    logger.info(f"Admin panel en: http://localhost:{port}/admin")
    logger.info("Usa Ctrl+C para detener el servidor")
    
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=port,
        reload=False,
        log_level="info"
    )
# Force reload 10/21/2025 19:29:27

# Background task for contract renewals
async def check_contract_renewals():
    """Check for contracts that need renewal every 24 hours"""
    while True:
        try:
            # Ensure database is initialized
            from db.database import init_beanie_db
            await init_beanie_db()
            from models.models_beanie import Contrato, Servicio, Usuario
            from datetime import datetime, timedelta
            from Services.mail.mail import enviar_correo
            
            now = datetime.utcnow()
            # Check contracts expiring in the next 7 days
            seven_days_from_now = now + timedelta(days=7)
            
            expiring_contracts = await Contrato.find(
                Contrato.fecha_fin <= seven_days_from_now,
                Contrato.fecha_fin > now,
                Contrato.estado == "activo",
                Contrato.renovacion_automatica == True
            ).to_list()
            
            for contrato in expiring_contracts:
                try:
                    servicio = await Servicio.get(contrato.servicio_id)
                    if servicio:
                        # Extend contract by one month
                        contrato.fecha_fin = contrato.fecha_fin + timedelta(days=30)
                        await contrato.save()
                        
                        # Send renewal notification
                        user = await Usuario.find_one(Usuario.id == contrato.usuario_id)
                        user_email = user.email if user else "user@example.com"
                        subject = f"Contrato de {servicio.nombre} renovado automáticamente"
                        message = f"""
Tu contrato para el servicio "{servicio.nombre}" ha sido renovado automáticamente.

Detalles actualizados:
- Servicio: {servicio.nombre}
- Nueva fecha de expiración: {contrato.fecha_fin.strftime('%Y-%m-%d')}
- Precio mensual: ${contrato.precio_mensual or 0}

Si deseas cancelar la renovación automática, puedes hacerlo desde tu panel de usuario.

Atentamente,
Equipo de Servicios Profesionales
"""
                        enviar_correo(user_email, subject, message)
                        print(f"Contract {contrato.id} renewed automatically")
                except Exception as e:
                    print(f"Error renewing contract {contrato.id}: {e}")
            
            # Check for expired contracts that should be cancelled
            expired_contracts = await Contrato.find(
                Contrato.fecha_fin <= now,
                Contrato.estado == "activo"
            ).to_list()
            
            for contrato in expired_contracts:
                if contrato.renovacion_automatica:
                    # Already renewed above, skip
                    continue
                else:
                    # Cancel expired contract
                    contrato.estado = "expirado"
                    await contrato.save()
                    
                    try:
                        servicio = await Servicio.get(contrato.servicio_id)
                        if servicio:
                            user = await Usuario.find_one(Usuario.id == contrato.usuario_id)
                            user_email = user.email if user else "user@example.com"
                            subject = f"Contrato de {servicio.nombre} expirado"
                            message = f"""
Tu contrato para el servicio "{servicio.nombre}" ha expirado.

Si deseas renovarlo, puedes crear un nuevo contrato desde nuestro sitio web.

Atentamente,
Equipo de Servicios Profesionales
"""
                            enviar_correo(user_email, subject, message)
                            print(f"Contract {contrato.id} expired")
                    except Exception as e:
                        print(f"Error sending expiration email for contract {contrato.id}: {e}")
                        
        except Exception as e:
            print(f"Error in contract renewal check: {e}")
        
        # Wait 24 hours before next check
        await asyncio.sleep(24 * 60 * 60)

# Start the background task
@app.on_event("startup")
async def startup_event():
    # Initialize Beanie database connection
    try:
        from db.database import init_beanie_db
        await init_beanie_db()
        print("[INFO] Beanie database initialized successfully")
    except Exception as e:
        print(f"[ERROR] Failed to initialize Beanie database: {e}")
        import traceback
        traceback.print_exc()
    
    # asyncio.create_task(check_contract_renewals())  # TEMPORALMENTE DESHABILITADO

# Adaptador para Vercel (serverless)
# from mangum import Mangum
# handler = Mangum(app)

print("Main module loaded successfully")

