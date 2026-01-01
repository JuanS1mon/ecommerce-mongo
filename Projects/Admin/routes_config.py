"""
Configuración de rutas para el panel de administración
Registra todos los routers del módulo Admin
"""
from fastapi import FastAPI
import logging

from .routes import (
    landing_router,
    auth_router,
    dashboard_router,
    productos_router,
    pedidos_router,
    presupuestos_router,
    # carritos_router,  # TODO MIGRACIÓN MONGO
    usuarios_admin_router,
    # configuracion_router,  # TODO MIGRACIÓN MONGO
    # editor_index_router  # TODO MIGRACIÓN MONGO
)

logger = logging.getLogger(__name__)


def configure_admin_routes(app: FastAPI):
    """
    Configura todas las rutas del panel de administración
    
    Args:
        app: Instancia de FastAPI
    """
    try:
        # Registrar todos los routers del admin
        # Landing page y auth primero (sin autenticación)
        app.include_router(landing_router)
        app.include_router(auth_router)
        
        # Rutas protegidas con autenticación
        app.include_router(dashboard_router)
        app.include_router(productos_router)
        app.include_router(pedidos_router)
        app.include_router(presupuestos_router)
        # app.include_router(carritos_router)  # TODO MIGRACIÓN MONGO
        app.include_router(usuarios_admin_router)
        # app.include_router(configuracion_router)  # TODO MIGRACIÓN MONGO
        # app.include_router(editor_index_router)  # TODO MIGRACIÓN MONGO
        
        logger.info("✅ Rutas del panel de administración configuradas correctamente")
        logger.info("  - Landing: /admin")
        logger.info("  - Login: /admin/login")
        logger.info("  - Dashboard: /admin/dashboard")
        logger.info("  - Productos: /admin/productos")
        logger.info("  - Pedidos: /admin/pedidos")
        logger.info("  - Presupuestos: /admin/presupuestos")
        # logger.info("  - Carritos: /admin/carritos")  # TODO MIGRACIÓN MONGO
        logger.info("  - Usuarios: /admin/usuarios")
        # logger.info("  - Configuración: /admin/configuracion")  # TODO MIGRACIÓN MONGO
        # logger.info("  - Editor Index: /admin/editor-index")  # TODO MIGRACIÓN MONGO
        
    except Exception as e:
        logger.error(f"❌ Error configurando rutas del admin: {str(e)}")
        raise
    
    return app
