"""
Panel de Administración del Ecommerce
Gestión completa de productos, pedidos, presupuestos, carritos y usuarios
"""
from .routes.landing import router as landing_router
from .routes.auth import router as auth_router
# Dashboard migrado a MongoDB - HABILITADO
from .routes.dashboard import router as dashboard_router
# TODO MIGRACIÓN MONGO: Comentado temporalmente hasta completar migración
# from .routes.productos import router as productos_router
# from .routes.pedidos import router as pedidos_router
# from .routes.presupuestos import router as presupuestos_router
# from .routes.carritos import router as carritos_router
from .routes.usuarios import router as usuarios_admin_router

__all__ = [
    'landing_router',
    'auth_router',
    'dashboard_router',  # HABILITADO - Migrado a MongoDB
    # 'productos_router',  # TODO MIGRACIÓN MONGO
    # 'pedidos_router',  # TODO MIGRACIÓN MONGO
    # 'presupuestos_router',  # TODO MIGRACIÓN MONGO
    # 'carritos_router',  # TODO MIGRACIÓN MONGO
    'usuarios_admin_router'
]
