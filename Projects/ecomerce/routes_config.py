"""
Configuración de rutas para el proyecto ecomerce
"""

from fastapi import FastAPI
from .routes import (
    usuarios_router,
    categorias_router,
    productos_router,
    stock_router,
    carritos_router,
    carrito_items_router,
    pedidos_router,
    presupuesto_router,
    checkout_router,
    resenas_router,
    lista_deseos_router,
    cupones_router,
    auth_router,
    password_reset_router,
    google_oauth_router,
    ecommerce_public_router,
    frontend_pages_router,
    static_pages_router,
    ping_router,
    mapas_router,
    compat_routes_router,
    admin_categorias_router,
    Blog_router,
)


def configure_routes(app: FastAPI):
    """
    Configura todas las rutas del proyecto ecomerce

    Args:
        app: Instancia de FastAPI
    """
    app.include_router(usuarios_router, prefix="/ecomerce/usuarios", tags=["usuarios"])
    app.include_router(categorias_router, prefix="/ecomerce/categorias", tags=["categorias"])
    app.include_router(productos_router, prefix="/ecomerce/productos", tags=["productos"])
    app.include_router(stock_router, prefix="/ecomerce/stock", tags=["stock"])
    app.include_router(carritos_router, prefix="/ecomerce/carritos", tags=["carritos"])
    app.include_router(carrito_items_router, prefix="/ecomerce/carrito_items", tags=["carrito_items"])
    app.include_router(pedidos_router, prefix="/ecomerce/pedidos", tags=["pedidos"])
    app.include_router(presupuesto_router, prefix="/ecomerce/api", tags=["presupuesto"])
    app.include_router(checkout_router, prefix="/ecomerce/checkout", tags=["checkout"])
    app.include_router(resenas_router, prefix="/ecomerce/resenas", tags=["resenas"])
    app.include_router(lista_deseos_router, prefix="/ecomerce/lista_deseos", tags=["lista_deseos"])
    app.include_router(cupones_router, prefix="/ecomerce/cupones", tags=["cupones"])
    app.include_router(auth_router, prefix="/ecomerce/auth", tags=["auth"])
    app.include_router(password_reset_router, prefix="/ecomerce/auth", tags=["auth"])
    app.include_router(google_oauth_router, prefix="/ecomerce/auth", tags=["auth"])
    app.include_router(ecommerce_public_router, prefix="/ecomerce/public", tags=["public"])
    app.include_router(frontend_pages_router, prefix="/ecomerce", tags=["frontend"])
    app.include_router(static_pages_router, prefix="/ecomerce", tags=["static"])
    app.include_router(ping_router, prefix="/ecomerce", tags=["ping"])
    app.include_router(mapas_router, prefix="/ecomerce/mapas", tags=["mapas"])
    app.include_router(compat_routes_router, prefix="/ecomerce", tags=["compat"])
    app.include_router(admin_categorias_router, prefix="/ecomerce/admin", tags=["admin"])
    app.include_router(Blog_router, prefix="/ecomerce/blog", tags=["blog"])

    return app
