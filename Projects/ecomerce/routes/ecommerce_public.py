"""
Router para productos públicos de ecommerce
Maneja la visualización de productos y categorías para usuarios no autenticados
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from Projects.ecomerce.models.productos_beanie import EcomerceProductos, EcomerceProductosVariantes
from Projects.ecomerce.models.categorias_beanie import EcomerceCategorias
from typing import List, Optional
from pydantic import BaseModel

# Pydantic models
class ProductoVariantePublico(BaseModel):
    id: str
    color: Optional[str] = None
    tipo: Optional[str] = None
    modelo: Optional[str] = None  # Campo dinámico agregado
    precio_adicional: int = 0
    stock: int = 0
    imagen_url: Optional[str] = None
    active: bool
    estado: Optional[str] = None  # Campo agregado para estado

class ProductoPublico(BaseModel):
    id: str
    codigo: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    id_categoria: str
    precio: Optional[int] = None
    imagen_url: Optional[str] = None
    active: bool
    variantes: List[ProductoVariantePublico] = []

class CategoriaPublica(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    active: bool

router = APIRouter(
    prefix="/ecomerce/api",
    tags=["ecommerce-public"],
)

@router.get("/productos/publicos", response_model=List[ProductoPublico])
async def get_productos_publicos(
    search: Optional[str] = Query(None, description="Término de búsqueda"),
    categoria: Optional[str] = Query(None, description="ID de categoría"),
    limit: int = Query(1000, description="Límite de resultados", ge=1, le=1000),
    offset: int = Query(0, description="Offset para paginación", ge=0)
):
    """
    Obtiene productos públicos con filtros opcionales
    """
    try:
        query = EcomerceProductos.find({"active": True})

        if search:
            # Búsqueda en nombre, descripción o código
            query = query.find({"$or": [
                {"nombre": {"$regex": search, "$options": "i"}},
                {"descripcion": {"$regex": search, "$options": "i"}},
                {"codigo": {"$regex": search, "$options": "i"}}
            ]})

        if categoria:
            from beanie import PydanticObjectId
            query = query.find({"id_categoria": PydanticObjectId(categoria)})

        productos = await query.skip(offset).limit(limit).to_list()

        # Obtener variantes para todos los productos
        producto_ids = [str(p.id) for p in productos]
        variantes = await EcomerceProductosVariantes.find(
            {"product_id": {"$in": producto_ids}}
        ).to_list()

        # Agrupar variantes por product_id
        variantes_por_producto = {}
        for v in variantes:
            if v.product_id not in variantes_por_producto:
                variantes_por_producto[v.product_id] = []
            variantes_por_producto[v.product_id].append(ProductoVariantePublico(
                id=str(v.id),
                color=v.color,
                tipo=v.tipo,
                modelo=getattr(v, 'modelo', None),  # Campo dinámico
                precio_adicional=v.precio_adicional,
                stock=v.stock,
                imagen_url=v.imagen_url,
                active=v.active,
                estado=getattr(v, 'estado', None)
            ))

        return [ProductoPublico(
            id=str(p.id),
            codigo=p.codigo,
            nombre=p.nombre,
            descripcion=p.descripcion,
            id_categoria=p.id_categoria,
            precio=p.precio,
            imagen_url=p.imagen_url,
            active=p.active,
            variantes=variantes_por_producto.get(str(p.id), [])
        ) for p in productos]

    except Exception as e:
        print(f"Error obteniendo productos públicos: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/categorias/publicas", response_model=List[CategoriaPublica])
async def get_categorias_publicas():
    """
    Obtiene todas las categorías activas para mostrar en la tienda
    """
    try:
        categorias = await EcomerceCategorias.find({"active": True}).to_list()

        return [CategoriaPublica(
            id=str(c.id),
            nombre=c.nombre,
            descripcion=c.descripcion,
            imagen_url=c.imagen_url,
            active=c.active
        ) for c in categorias]

    except Exception as e:
        print(f"Error obteniendo categorías públicas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/productos/tienda", response_model=List[ProductoPublico])
async def get_productos_tienda(
    search: Optional[str] = Query(None, description="Buscar productos por nombre, descripción o código"),
    categoria: Optional[str] = Query(None, description="Filtrar por ID de categoría"),
    limit: int = Query(20, description="Número máximo de productos a retornar"),
    offset: int = Query(0, description="Número de productos a saltar")
):
    """
    Obtiene productos para mostrar en la tienda (productos activos)
    """
    try:
        query = EcomerceProductos.find({"active": True})

        if search:
            query = query.find({"$or": [
                {"nombre": {"$regex": search, "$options": "i"}},
                {"descripcion": {"$regex": search, "$options": "i"}},
                {"codigo": {"$regex": search, "$options": "i"}}
            ]})

        if categoria:
            from beanie import PydanticObjectId
            query = query.find({"id_categoria": PydanticObjectId(categoria)})

        productos = await query.skip(offset).limit(limit).to_list()

        # Obtener variantes para todos los productos
        producto_ids = [str(p.id) for p in productos]
        variantes = await EcomerceProductosVariantes.find(
            {"product_id": {"$in": producto_ids}}
        ).to_list()

        # Agrupar variantes por product_id
        variantes_por_producto = {}
        for v in variantes:
            if v.product_id not in variantes_por_producto:
                variantes_por_producto[v.product_id] = []
            variantes_por_producto[v.product_id].append(ProductoVariantePublico(
                id=str(v.id),
                color=v.color,
                tipo=v.tipo,
                modelo=getattr(v, 'modelo', None),  # Campo dinámico
                precio_adicional=v.precio_adicional,
                stock=v.stock,
                imagen_url=v.imagen_url,
                active=v.active,
                estado=getattr(v, 'estado', None)
            ))

        return [ProductoPublico(
            id=str(p.id),
            codigo=p.codigo,
            nombre=p.nombre,
            descripcion=p.descripcion,
            id_categoria=p.id_categoria,
            precio=p.precio,
            imagen_url=p.imagen_url,
            active=p.active,
            variantes=variantes_por_producto.get(str(p.id), [])
        ) for p in productos]

    except Exception as e:
        print(f"Error obteniendo productos para tienda: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/productos/{producto_id}", response_model=ProductoPublico)
async def get_producto_publico(producto_id: str):
    """
    Obtiene un producto específico por ID
    """
    try:
        from beanie import PydanticObjectId

        producto = await EcomerceProductos.get(PydanticObjectId(producto_id))

        if not producto or not producto.active:
            raise HTTPException(
                status_code=404,
                detail="Producto no encontrado"
            )

        # Obtener variantes del producto
        variantes = await EcomerceProductosVariantes.find(
            EcomerceProductosVariantes.product_id == producto_id
        ).to_list()

        variantes_publicas = [
            ProductoVariantePublico(
                id=str(v.id),
                color=v.color,
                tipo=v.tipo,
                modelo=getattr(v, 'modelo', None),  # Campo dinámico
                precio_adicional=v.precio_adicional,
                stock=v.stock,
                imagen_url=v.imagen_url,
                active=v.active,
                estado=getattr(v, 'estado', None)
            ) for v in variantes
        ]

        return ProductoPublico(
            id=str(producto.id),
            codigo=producto.codigo,
            nombre=producto.nombre,
            descripcion=producto.descripcion,
            id_categoria=producto.id_categoria,
            precio=producto.precio,
            imagen_url=producto.imagen_url,
            active=producto.active,
            variantes=variantes_publicas
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo producto {producto_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.get("/productos/categoria/{categoria_id}", response_model=List[ProductoPublico])
async def get_productos_por_categoria(categoria_id: str):
    """
    Obtiene productos por categoría
    """
    try:
        from beanie import PydanticObjectId
        productos = await EcomerceProductos.find(
            {"id_categoria": PydanticObjectId(categoria_id), "active": True}
        ).to_list()

        # Obtener variantes para todos los productos
        producto_ids = [str(p.id) for p in productos]
        variantes = await EcomerceProductosVariantes.find(
            {"product_id": {"$in": producto_ids}}
        ).to_list()

        # Agrupar variantes por product_id
        variantes_por_producto = {}
        for v in variantes:
            if v.product_id not in variantes_por_producto:
                variantes_por_producto[v.product_id] = []
            variantes_por_producto[v.product_id].append(ProductoVariantePublico(
                id=str(v.id),
                color=v.color,
                tipo=v.tipo,
                modelo=getattr(v, 'modelo', None),  # Campo dinámico
                precio_adicional=v.precio_adicional,
                stock=v.stock,
                imagen_url=v.imagen_url,
                active=v.active,
                estado=getattr(v, 'estado', None)
            ))

        return [
            ProductoPublico(
                id=str(p.id),
                codigo=p.codigo,
                nombre=p.nombre,
                descripcion=p.descripcion,
                id_categoria=str(p.id_categoria),
                precio=p.precio,
                imagen_url=p.imagen_url,
                active=p.active,
                variantes=variantes_por_producto.get(str(p.id), [])
            )
            for p in productos
        ]

    except Exception as e:
        print(f"Error obteniendo productos por categoría {categoria_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

# Endpoint con integración MCP (Azure AI Search)
@router.get("/productos/search-mcp")
def search_productos_mcp(
    query: str = Query(..., description="Término de búsqueda"),
    limit: int = Query(10, description="Límite de resultados")
):
    """
    Busca productos usando Azure AI Search (MCP)
    """
    try:
        # Aquí se integraría con Azure AI Search
        # Usar azure-search-documents SDK
        # Placeholder para integración MCP
        return {
            "message": "Búsqueda con MCP integrada",
            "query": query,
            "results": []  # Resultados de Azure Search
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda MCP: {str(e)}")
