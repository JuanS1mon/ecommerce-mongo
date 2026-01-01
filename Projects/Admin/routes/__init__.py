"""
Routers del panel de administración
"""
from .landing import router as landing_router
from .auth import router as auth_router
# Dashboard migrado a MongoDB - HABILITADO
from .dashboard import router as dashboard_router
from .productos import router as productos_router
from .pedidos import router as pedidos_router
from .presupuestos import router as presupuestos_router
# TODO MIGRACIÓN MONGO: Reactivar tras completar migración de estos routers
# from .carritos import router as carritos_router
from .usuarios import router as usuarios_admin_router
# from .configuracion import router as configuracion_router
# from .editor_index import router as editor_index_router

__all__ = [
    'landing_router',
    'auth_router',
    'dashboard_router',  # HABILITADO - Migrado a MongoDB
    'productos_router',
    'pedidos_router',
    'presupuestos_router',
    # 'carritos_router',  # TODO MIGRACIÓN MONGO
    'usuarios_admin_router',
    # 'configuracion_router',  # TODO MIGRACIÓN MONGO
    # 'editor_index_router'  # TODO MIGRACIÓN MONGO
]
