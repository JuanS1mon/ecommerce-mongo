"""
Proyecto ecomerce - Generado desde Editor Visual
Archivo principal de inicialización del proyecto.
"""

# Importaciones de modelos (con prefijo)
from .models.usuarios import EcomerceUsuarios
from .models.categorias_beanie import EcomerceCategorias
from .models.productos_beanie import EcomerceProductos
from .models.carritos_beanie import EcomerceCarritos
from .models.resenas_beanie import EcomerceResenas
from .models.lista_deseos_beanie import EcomerceListaDeseos
from .models.cupones_beanie import EcomerceCupones

# Importaciones de rutas
# TODO: Re-enable when migrated to Beanie
# from .routes.usuarios import router as usuarios_router
# from .routes.categorias import router as categorias_router
# from .routes.productos import router as productos_router
# from .routes.stock import router as stock_router
# from .routes.carritos import router as carritos_router
# from .routes.carrito_items import router as carrito_items_router
# from .routes.pedidos import router as pedidos_router
# from .routes.presupuesto import router as presupuesto_router
# from .routes.checkout import router as checkout_router

# Lista de todos los componentes disponibles
__all__ = [
    # Modelos
    "EcomerceUsuarios", "EcomerceCategorias", "EcomerceProductos", "EcomerceStock", "EcomerceCarritos", "EcomerceCarrito_items", "EcomercePedidos", "EcomerceResenas", "EcomerceListaDeseos", "EcomerceCupones",
    # Schemas
    "UsuariosCreate", "UsuariosUpdate", "UsuariosRead", "CategoriasCreate", "CategoriasUpdate", "CategoriasRead", "ProductosCreate", "ProductosUpdate", "ProductosRead", "StockCreate", "StockUpdate", "StockRead", "CarritosCreate", "CarritosUpdate", "CarritosRead", "Carrito_itemsCreate", "Carrito_itemsUpdate", "Carrito_itemsRead", "PedidosCreate", "PedidosUpdate", "PedidosRead",
    # Controladores
    "create_usuarios", "get_usuarios", "gets_usuarios", "update_usuarios", "delete_usuarios", "create_categorias", "get_categorias", "gets_categorias", "update_categorias", "delete_categorias", "create_productos", "get_productos", "gets_productos", "update_productos", "delete_productos", "create_stock", "get_stock", "gets_stock", "update_stock", "delete_stock", "create_carritos", "get_carritos", "gets_carritos", "update_carritos", "delete_carritos", "create_carrito_items", "get_carrito_items", "gets_carrito_items", "update_carrito_items", "delete_carrito_items", "create_pedidos", "get_pedidos", "gets_pedidos", "update_pedidos", "delete_pedidos",
    # Rutas
    "usuarios_router", "categorias_router", "productos_router", "stock_router", "carritos_router", "carrito_items_router", "pedidos_router", "presupuesto_router", "checkout_router",
]
