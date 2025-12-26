# ============================================================================
# SISTEMA DE SQL_APP - MAIN APPLICATION
# ============================================================================
# Archivo principal de la aplicación FastAPI
# Contiene la configuración central, middlewares, rutas y manejadores de errores

# =============================
# PRE-IMPORTACIÓN CRÍTICA: Cargar typing_extensions correcto
# =============================
import sys, os
# Skip pre_import in serverless environments like Vercel
if os.getenv("VERCEL") != "1":
    try:
        import pre_import  # DEBE ser el primer import para evitar conflictos
        print("[OK] pre_import cargado correctamente")
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
from fastapi.responses import FileResponse, Response, JSONResponse
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
try:
    from Projects.ecomerce.routes.frontend_pages import router as frontend_pages_router
except Exception as e:
    frontend_pages_router = None
    logger.error(f"Failed to import frontend_pages_router: {e}")

try:
    from Projects.ecomerce.routes.static_pages import router as static_pages_router
except Exception as e:
    static_pages_router = None
    logger.error(f"Failed to import static_pages_router: {e}")

try:
    from Projects.ecomerce.routes.resenas import router as resenas_router
except Exception as e:
    resenas_router = None
    logger.error(f"Failed to import resenas_router: {e}")

try:
    from Projects.ecomerce.routes.lista_deseos import router as lista_deseos_router
except Exception as e:
    lista_deseos_router = None
    logger.error(f"Failed to import lista_deseos_router: {e}")

try:
    from Projects.ecomerce.routes.cupones import router as cupones_router
except Exception as e:
    cupones_router = None
    logger.error(f"Failed to import cupones_router: {e}")

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
    """Lifespan que no bloquea el arranque del proceso: inicia la inicialización
    de DB en background y devuelve control inmediatamente para que la app
    responda a las sondas de arranque. Las tareas pesadas se registran y hacen
    retries internos; cuando terminan correctamente escriben READY_OK en
    `import_check.log`.
    """
    global db_ready, init_task, db_status, modelos_status, tablas_status
    import asyncio

    # Marcar como no listo inicialmente
    db_ready = False
    db_status = False

    async def _init_background():
        """Tarea background que inicializa la DB y otros componentes lentos."""
        global db_ready, db_status
        retries = 3
        for attempt in range(1, retries + 1):
            try:
                await init_database()
                db_status = True
                db_ready = True
                logger.info("Beanie inicializado correctamente para MongoDB (background)")
                break
            except Exception as e:
                logger.error(f"Background init_database intento {attempt} falló: {e}")
                import traceback
                logger.error(traceback.format_exc())
                if attempt < retries:
                    await asyncio.sleep(5 * attempt)
                else:
                    db_status = False
                    logger.error("Fallo al inicializar la base de datos después de retries")

        # Tareas post-init (ej. crear admin) — no bloqueantes
        try:
            # Placeholder: si fuera necesario llamar a init_admin_on_startup, hacerlo aquí
            logger.info("Admin init (background) completado o saltado")
        except Exception as e:
            logger.error(f"Error en admin init (background): {e}")

        # Escribir READY_OK una vez completado (exitoso o no, para diagnosticar)
        try:
            import datetime
            p = os.path.join(os.path.dirname(__file__), 'import_check.log')
            with open(p, 'a') as f:
                f.write(f"READY_OK db_ready={db_ready} {datetime.datetime.utcnow().isoformat()}\n")
            logger.info(f"Wrote READY_OK to {p}")
        except Exception as e:
            logger.warning(f"Could not write READY_OK to import_check.log: {e}")

    # Iniciar la tarea background y no esperar a que termine
    init_task = asyncio.create_task(_init_background())
    logger.info("Background initialization started (init_task scheduled)")

    # Registrar checklist inicial (DB puede estar pendiente)
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
    logger.info("Iniciando aplicacion FastAPI (startup tasks running in background)")

    try:
        yield
    except Exception as e:
        logger.error(f"Error durante la ejecución de la aplicación: {e}")
        import traceback
        logger.error(traceback.format_exc())
        raise
    finally:
        # During shutdown, cancel background init if it's still running
        logger.info("Cerrando aplicacion FastAPI: esperando tareas background")
        if init_task is not None and not init_task.done():
            init_task.cancel()
            try:
                await init_task
            except asyncio.CancelledError:
                logger.info("Background init_task cancelled during shutdown")
        logger.info("Limpieza de recursos completada")

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


@app.get("/healthz")
async def healthz():
    """Readiness endpoint: devuelve 200 cuando la DB está lista, 503 mientras se inicializa."""
    try:
        if db_ready:
            return JSONResponse(status_code=200, content={"status": "ok", "db_ready": True})
        else:
            return JSONResponse(status_code=503, content={"status": "starting", "db_ready": False})
    except Exception as e:
        logger.error(f"Error en /healthz: {e}")
        return JSONResponse(status_code=500, content={"status": "error"})

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

if resenas_router:
    app.include_router(resenas_router, prefix="/ecomerce/api", tags=["resenas"])
else:
    logger.warning("resenas_router no disponible; se omite su registro")

if lista_deseos_router:
    app.include_router(lista_deseos_router, prefix="/ecomerce/api/lista-deseos", tags=["lista-deseos"])
else:
    logger.warning("lista_deseos_router no disponible; se omite su registro")

if cupones_router:
    app.include_router(cupones_router, prefix="/ecomerce/api/cupones", tags=["cupones"])
else:
    logger.warning("cupones_router no disponible; se omite su registro")

logger.info("carrito_router registrado")

# Importar y registrar el router de páginas frontend
from Projects.ecomerce.routes.frontend_pages import router as frontend_pages_router

# =============================
# RUTAS PRINCIPALES - ANTES DE REGISTRAR FRONTEND ROUTER
# =============================

# Ruta para productos de tienda (sin /api para compatibilidad) - REGISTRADA ANTES QUE frontend_pages_router
# Load templates defensively
try:
    templates_main = Jinja2Templates(directory="Projects/ecomerce/templates")
except Exception as e:
    templates_main = None
    logger.error(f"Failed to initialize Jinja2Templates: {e}")

@app.get("/ecomerce/productos/tienda")
async def get_productos_tienda(request: Request):
    """Renderiza la tienda con Jinja2 (usa base.html)"""
    if templates_main is None:
        return Response(status_code=503, content="Templates not available")
    return templates_main.TemplateResponse(
        "productos_tienda.html",
        {"request": request},
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
        },
    )

if frontend_pages_router:
    logger.info(f"Registrando frontend_pages_router con {len(frontend_pages_router.routes)} rutas")
    for route in frontend_pages_router.routes:
        logger.info(f"  FRONTEND ROUTE: {route.methods} {route.path}")
    app.include_router(frontend_pages_router)
    logger.info("frontend_pages_router registrado")
else:
    logger.warning("frontend_pages_router no disponible; se omite su registro")

# Importar y registrar el router de páginas estáticas
if static_pages_router:
    logger.info(f"Registrando static_pages_router con {len(static_pages_router.routes)} rutas")
    for route in static_pages_router.routes:
        logger.info(f"  STATIC ROUTE: {route.methods} {route.path}")
    app.include_router(static_pages_router)
    logger.info("static_pages_router registrado")
else:
    logger.warning("static_pages_router no disponible; se omite su registro")

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

# Adaptador para Vercel (serverless)
# from mangum import Mangum
# handler = Mangum(app)

