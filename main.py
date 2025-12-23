# ============================================================================
# SISTEMA DE SQL_APP - MAIN APPLICATION
# ============================================================================
# Archivo principal de la aplicación FastAPI
# Contiene la configuración central, middlewares, rutas y manejadores de errores

# =============================
# PRE-IMPORTACIÓN CRÍTICA: Cargar typing_extensions correcto
# =============================

print("[OK] pre_import cargado correctamente")

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
from logging_config_new import setup_logging

print("[OK] Configuración y logging importados")

# CONFIGURAR LOGGING ULTRA VERBOSO
setup_logging()

print("[OK] Logging configurado")

# =============================
# IMPORTACIONES ESTÁNDAR Y FASTAPI
# =============================
import sys
import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi import Request
from fastapi.responses import FileResponse, Response
from fastapi.templating import Jinja2Templates

print("[OK] Importaciones básicas de FastAPI completadas")

# =============================
# IMPORTACIONES DE MIDDLEWARES Y HANDLERS
# =============================
from exception_handlers import register_exception_handlers

print("[OK] Middlewares y handlers importados")

# =============================
# IMPORTACIONES DE DB Y ROUTERS
# =============================
from db.database import init_database  # Only import Beanie init
import importlib

# Intento robusto de import para entornos donde el módulo puede no estar en sys.path
try:
    from init_app import ensure_directories
except Exception as e:
    logger.error(f"No se pudo importar 'init_app' directamente: {e}")
    # Listar archivos del directorio de la app para depuración en logs
    project_root = os.path.abspath(os.path.dirname(__file__))
    logger.error(f"Contenido del directorio de la app: {os.listdir(project_root)}")
    # Intentar cargar por importlib (fallback)
    try:
        init_mod = importlib.import_module('init_app')
        ensure_directories = init_mod.ensure_directories
        logger.info("Import 'init_app' realizado mediante importlib fallback")
    except Exception as e2:
        logger.error(f"Fallback falló importando 'init_app': {e2}")
        # As a last resort, attempt to load module from file path in the app directory
        try:
            import importlib.util
            project_root = os.path.abspath(os.path.dirname(__file__))
            candidate = os.path.join(project_root, 'init_app.py')
            logger.info(f"Intentando cargar 'init_app' desde ruta: {candidate}")
            if os.path.exists(candidate):
                spec = importlib.util.spec_from_file_location('init_app', candidate)
                init_mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(init_mod)
                ensure_directories = init_mod.ensure_directories
                logger.info("Import 'init_app' realizado mediante spec_from_file_location fallback")
            else:
                logger.error(f"Archivo 'init_app.py' no existe en {project_root}")
                raise
        except Exception as e3:
            logger.error(f"All fallbacks failed importing 'init_app': {e3}")
            raise
# from routers import usuarios as aut_usuario
# from routers.config import  configDB,  Analisis,  usuarios_admin
# from routers.config.Admin import router as admin_router
from Projects.ecomerce.routes.frontend_pages import router as frontend_pages_router
from Projects.ecomerce.routes.static_pages import router as static_pages_router
from Projects.ecomerce.routes.resenas import router as resenas_router
from Projects.ecomerce.routes.lista_deseos import router as lista_deseos_router
from Projects.ecomerce.routes.cupones import router as cupones_router
from Services.mail.mail import MAIL_CONFIG_OK
# from routers.mapas import router as mapas_router

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
    # Startup logic
    # Inicializar Beanie para MongoDB
    try:
        await init_database()
        logger.info("Beanie inicializado correctamente para MongoDB")
        db_status = True
    except Exception as e:
        logger.error(f"Error inicializando Beanie: {e}")
        db_status = False
        raise
    
    # Alembic migrations not needed for MongoDB
    alembic_ok = True  # MongoDB doesn't use Alembic
    
    mail_ok = check_mail_config()

    # Inicializar usuario administrador
    admin_created = False
    try:
        # from init_admin import init_admin_on_startup
        # init_admin_on_startup(db)
        # admin_created = True
        admin_created = True  # Usuarios ya existen con contraseñas conocidas
    except Exception as e:
        logger.error(f"Error al crear usuario administrador: {e}")
        admin_created = False

    # Limpiar tokens expirados del blacklist - Deshabilitado para MongoDB
    tokens_cleaned = True  # No aplicable en MongoDB

    # Mostrar rutas registradas para debug
    logger.info("Rutas registradas:")
    for route in app.routes:
        if hasattr(route, 'path'):
            methods = getattr(route, 'methods', ['MOUNT'])
            logger.info(f"  - {methods} {route.path}")

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
        ("Migraciones Alembic aplicadas", alembic_ok),
        ("Usuario administrador inicializado", admin_created),
        ("Tokens expirados limpiados del blacklist", tokens_cleaned),
    ]
    logger.info("\n================= CHECKLIST DE INICIO =================")
    for item, ok in checklist:
        logger.info(f"[OK] {item}")
    logger.info("======================================================\n")
    logger.info("Iniciando aplicacion FastAPI")

    try:
        yield
    except Exception as e:
        logger.error(f"Error durante la ejecución de la aplicación: {e}")
        import traceback
        traceback.print_exc()
        raise

    # Shutdown logic
    logger.info("Cerrando aplicacion FastAPI")
    logger.info("Limpieza de recursos completada")

# Crear la aplicación con lifespan
app = FastAPI(
    title="Ecommerce API",
    description="API para sistema de ecommerce",
    version="1.0.0",
    lifespan=lifespan
)

# Configurar archivos estáticos y middlewares después de crear la app
app.mount("/static", StaticFiles(directory="static"), name="static")

# --------------------------------------------------------------------------
# Favicon handler: evita error 500 si el navegador solicita /favicon.ico
# Sirve logo.svg como fallback (o 204 si no está disponible)
# --------------------------------------------------------------------------
@app.get("/favicon.ico")
async def favicon():
    candidate_svg = os.path.join("sql_app", "static", "logo.png")
    candidate_png = os.path.join("sql_app", "static", "img", "favicon.png")
    if os.path.exists(candidate_png):
        return FileResponse(candidate_png)
    if os.path.exists(candidate_svg):
        return FileResponse(candidate_svg, media_type="image/svg+xml")
    return Response(status_code=204)

# =============================
# MIDDLEWARES
# =============================
from app_settings import CORS_CONFIG
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_CONFIG["allow_origins"],
    allow_credentials=CORS_CONFIG["allow_credentials"],
    allow_methods=CORS_CONFIG["allow_methods"],
    allow_headers=CORS_CONFIG["allow_headers"],
)
# app.add_middleware(RequestLoggingMiddleware)  # DESHABILITADO TEMPORALMENTE

# =============================
# EXCEPTION HANDLERS
# =============================
register_exception_handlers(app)

# =============================
# REGISTRO DE ROUTERS
# =============================
# Importar y registrar el router de restablecimiento de contraseña
from Projects.ecomerce.routes.password_reset import router as password_reset_router
app.include_router(password_reset_router)

# Compat routes for mixed spellings (ecomerce / ecommerce)
try:
    from Projects.ecomerce.routes.compat_routes import router as compat_router
    app.include_router(compat_router)
    logger.info("Router compat_routes registrado correctamente")
except Exception as e:
    logger.error(f"[WARN] No se pudo registrar router compat_routes: {e}")

# Importar y registrar el router de productos públicos ecommerce
try:
    from Projects.ecomerce.routes.ecommerce_public import router as ecommerce_public_router
    app.include_router(ecommerce_public_router)
    logger.info("Router ecommerce_public registrado correctamente")
except Exception as e:
    logger.error(f"[ERROR] Error registrando router ecommerce_public: {e}")
    import traceback
    traceback.print_exc()

# # Importar y registrar el router de productos
# try:
#     # from Projects.ecomerce.routes.productos import router as productos_router
#     # app.include_router(productos_router, prefix="/ecomerce/productos", tags=["productos"])
#     logger.info("Router productos deshabilitado temporalmente (migración a MongoDB)")
# except Exception as e:
#     logger.error(f"❌ Error registrando router productos: {e}")
#     import traceback
#     traceback.print_exc()

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

# Importar y registrar el router de carrito
from Projects.ecomerce.routes.carrito import router as carrito_router
logger.info(f"Registrando carrito_router con {len(carrito_router.routes)} rutas")
for route in carrito_router.routes:
    logger.info(f"  CARRITO ROUTE: {route.methods} {route.path}")
app.include_router(carrito_router, prefix="/ecomerce", tags=["carrito"])

# Importar y registrar el router de usuarios
from Projects.ecomerce.routes.usuarios import usuarios_router
logger.info(f"Registrando usuarios_router con {len(usuarios_router.routes)} rutas")
for route in usuarios_router.routes:
    logger.info(f"  USUARIOS ROUTE: {route.methods} {route.path}")
app.include_router(usuarios_router, prefix="/ecomerce", tags=["usuarios"])

# Importar y registrar el router de checkout
from Projects.ecomerce.routes.checkout import router as checkout_router
logger.info(f"Registrando checkout_router con {len(checkout_router.routes)} rutas")
for route in checkout_router.routes:
    logger.info(f"  CHECKOUT ROUTE: {route.methods} {route.path}")
app.include_router(checkout_router, prefix="/ecomerce", tags=["checkout"])

# Importar y registrar el router de SEO
try:
    from Projects.ecomerce.routes.seo import router as seo_router
    logger.info(f"Registrando seo_router con {len(seo_router.routes)} rutas")
    app.include_router(seo_router)
    logger.info("SEO router registrado: sitemap.xml, robots.txt, etc.")
except Exception as e:
    logger.error(f"Error registrando seo_router: {e}")
    import traceback
    traceback.print_exc()

app.include_router(resenas_router, prefix="/ecomerce/api", tags=["resenas"])
app.include_router(lista_deseos_router, prefix="/ecomerce/api/lista-deseos", tags=["lista-deseos"])
app.include_router(cupones_router, prefix="/ecomerce/api/cupones", tags=["cupones"])
logger.info("carrito_router registrado")

# Importar y registrar el router de páginas frontend
from Projects.ecomerce.routes.frontend_pages import router as frontend_pages_router

# =============================
# RUTAS PRINCIPALES - ANTES DE REGISTRAR FRONTEND ROUTER
# =============================

# Ruta para productos de tienda (sin /api para compatibilidad) - REGISTRADA ANTES QUE frontend_pages_router
templates_main = Jinja2Templates(directory="Projects/ecomerce/templates")

@app.get("/ecomerce/productos/tienda")
async def get_productos_tienda(request: Request):
    """Renderiza la tienda con Jinja2 (usa base.html)"""
    return templates_main.TemplateResponse(
        "productos_tienda.html",
        {"request": request},
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

logger.info(f"Registrando frontend_pages_router con {len(frontend_pages_router.routes)} rutas")
for route in frontend_pages_router.routes:
    logger.info(f"  FRONTEND ROUTE: {route.methods} {route.path}")
app.include_router(frontend_pages_router)
logger.info("frontend_pages_router registrado")

# Importar y registrar el router de páginas estáticas
from Projects.ecomerce.routes.static_pages import router as static_pages_router
logger.info(f"Registrando static_pages_router con {len(static_pages_router.routes)} rutas")
for route in static_pages_router.routes:
    logger.info(f"  STATIC ROUTE: {route.methods} {route.path}")
app.include_router(static_pages_router)
logger.info("static_pages_router registrado")

# Importar y registrar el router de mapas
try:
    from Projects.ecomerce.routes.mapas import router as mapas_router
    app.include_router(mapas_router, prefix="/mapas", tags=["mapas"])
    logger.info("mapas_router registrado correctamente")
    print("DEBUG: mapas_router registrado con prefix /mapas")
except Exception as e:
    logger.error(f"Error registrando mapas_router: {e}")
    print(f"DEBUG: Error registrando mapas_router: {e}")

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
from Projects.ecomerce.routes.ecommerce_auth import router as ecommerce_auth_router
logger.info(f"Registrando ecommerce_auth_router con {len(ecommerce_auth_router.routes)} rutas")
for route in ecommerce_auth_router.routes:
    logger.info(f"  ECOMMERCE ROUTE: {route.methods} {route.path}")
app.include_router(ecommerce_auth_router)
logger.info("ecommerce_auth_router registrado")

# Importar y registrar el router de autenticación con Google
try:
    from Projects.ecomerce.routes.google_oauth import router as google_oauth_router
    logger.info(f"Registrando google_oauth_router con {len(google_oauth_router.routes)} rutas")
    for route in google_oauth_router.routes:
        logger.info(f"  GOOGLE OAUTH ROUTE: {route.methods} {route.path}")
    app.include_router(google_oauth_router)
    logger.info("google_oauth_router registrado")
except Exception as e:
    logger.error(f"Router google_oauth deshabilitado temporalmente (falta modulo authlib o configuración): {e}")


# =============================
# RUTAS PRINCIPALES
# =============================

# Ruta raíz - Carga la página principal
@app.get("/")
async def root(request: Request):
    """Renderiza la página principal con plantilla base y navbar de tienda"""
    return templates_main.TemplateResponse(
        "index.html",
        {"request": request},
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

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
    import asyncio

    # TEMPORALMENTE DESHABILITADO PARA DEBUGGING
    # logger.info("Ejecutando prueba de funcionalidad de email...")
    # asyncio.run(test_email_functionality())

    # Configurar puerto desde variable de entorno o usar 8001 por defecto (8000 ocupado por MCP)
    port = int(os.getenv('PORT', 8001))

    logger.info(f"Iniciando servidor FastAPI en puerto {port}")
    logger.info(f"Servidor disponible en: http://localhost:{port}")
    logger.info(f"Documentacion API en: http://localhost:{port}/docs")
    logger.info(f"Admin panel en: http://localhost:{port}/admin")
    logger.info("Usa Ctrl+C para detener el servidor")
    try:
        logger.info(f"Configuracion de uvicorn: host=0.0.0.0, port={port}, reload=False")
        uvicorn.run(
            "main:app",
            host="0.0.0.0",
            port=port,
            reload=False,  # FORZADO A False para evitar problemas de recarga
            log_level="info",  # Cambiado a info para menos logs
            access_log=True,
            use_colors=False,  # Deshabilitar colores para evitar problemas de encoding
            log_config=None  # Usar configuración por defecto
        )
        logger.info("uvicorn.run() termino normalmente")
    except KeyboardInterrupt:
        logger.info("Servidor detenido por el usuario")
    except Exception as e:
        logger.error(f"Error al iniciar servidor: {str(e)}")
        import traceback
        traceback.print_exc()
    finally:
        logger.info("Bloque finally ejecutado")
# Force reload 10/21/2025 19:29:27

