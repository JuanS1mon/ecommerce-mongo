"""
Router de Gestión de Productos para Admin (MongoDB/Beanie)
CRUD completo de productos del ecommerce
"""
import logging
import os
from typing import List, Optional
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, File, UploadFile, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from beanie.operators import Or, RegEx, In

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.ecomerce.models.productos_beanie import EcomerceProductos, EcomerceProductosVariantes
from Projects.ecomerce.models.categorias_beanie import EcomerceCategorias
from Projects.Admin.middleware.admin_auth import require_admin

logger = logging.getLogger(__name__)

# Modelos Pydantic
class ProductoCreate(BaseModel):
    codigo: Optional[str] = None
    nombre: str
    descripcion: Optional[str] = None
    id_categoria: Optional[str] = None
    precio: float
    imagen_url: Optional[str] = None
    active: bool = True

class ProductoUpdate(BaseModel):
    codigo: Optional[str] = None
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    id_categoria: Optional[str] = None
    precio: Optional[float] = None
    imagen_url: Optional[str] = None
    active: Optional[bool] = None

# Importar helper de templates
from Projects.Admin.utils.template_helpers import render_admin_template

router = APIRouter(
    prefix="/admin/productos",
    tags=["admin-productos"]
)


@router.get("/", response_class=HTMLResponse)
async def lista_productos_view(
    request: Request
):
    """Vista de lista de productos para el admin (autenticación en frontend)"""
    try:
        return render_admin_template(
            "productos.html",
            request,
            active_page="productos"
        )
    except Exception as e:
        logger.error(f"Error cargando productos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando productos"
        )


@router.get("/api/imagenes-disponibles")
async def listar_imagenes_disponibles(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """
    Lista todas las imágenes disponibles en la carpeta static/img
    """
    try:
        imagenes = []
        static_path = Path("static/img")
        
        if not static_path.exists():
            return {"imagenes": []}
        
        # Extensiones de imagen válidas
        extensiones_validas = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.svg'}
        
        # Recorrer recursivamente la carpeta static/img
        for root, dirs, files in os.walk(static_path):
            for file in files:
                file_path = Path(root) / file
                if file_path.suffix.lower() in extensiones_validas:
                    # Convertir la ruta a URL relativa
                    ruta_relativa = file_path.as_posix().replace('\\', '/')
                    url_imagen = f"/{ruta_relativa}"
                    
                    # Obtener información adicional
                    carpeta = Path(root).name
                    
                    imagenes.append({
                        "url": url_imagen,
                        "nombre": file,
                        "carpeta": carpeta,
                        "ruta_completa": str(file_path)
                    })
        
        # Ordenar por carpeta y nombre
        imagenes.sort(key=lambda x: (x['carpeta'], x['nombre']))
        
        logger.info(f"Se encontraron {len(imagenes)} imágenes en static/img")
        
        return {
            "imagenes": imagenes,
            "total": len(imagenes)
        }
    except Exception as e:
        logger.error(f"Error listando imágenes: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando imágenes disponibles"
        )


@router.get("/api/list")
async def listar_productos_api(
    admin_user: AdminUsuarios = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    categoria_id: Optional[str] = None,
    activo: Optional[bool] = None
):
    """
    API para listar productos con filtros (MongoDB/Beanie)
    
    Query params:
    - skip: Número de productos a saltar (paginación)
    - limit: Número máximo de productos a devolver
    - search: Buscar por nombre, código o descripción
    - categoria_id: Filtrar por categoría (ObjectId)
    - activo: Filtrar por estado (True/False)
    """
    try:
        # Construir filtros
        filters = []
        
        # Si hay búsqueda, buscar también por nombre de categoría
        categoria_ids_match = []
        if search:
            # Buscar categorías que coincidan con el término de búsqueda
            categorias_match = await EcomerceCategorias.find(
                RegEx(EcomerceCategorias.nombre, search, "i")
            ).to_list()
            categoria_ids_match = [str(c.id) for c in categorias_match]
            
            # Construir filtro de búsqueda incluyendo categorías
            search_filters = [
                RegEx(EcomerceProductos.nombre, search, "i"),
                RegEx(EcomerceProductos.codigo, search, "i"),
                RegEx(EcomerceProductos.descripcion, search, "i")
            ]
            
            # Si encontramos categorías que coinciden, agregarlas al filtro
            if categoria_ids_match:
                search_filters.append(In(EcomerceProductos.id_categoria, categoria_ids_match))
            
            filters.append(Or(*search_filters))
        
        if categoria_id:
            filters.append(EcomerceProductos.id_categoria == categoria_id)
        
        if activo is not None:
            filters.append(EcomerceProductos.active == activo)
        
        # Construir query
        if filters:
            query = EcomerceProductos.find(*filters)
        else:
            query = EcomerceProductos.find_all()
        
        # Obtener total y productos
        total = await query.count()
        productos = await query.sort("-_id").skip(skip).limit(limit).to_list()
        
        # Obtener categorías
        categorias = await EcomerceCategorias.find_all().to_list()
        
        # Obtener variantes para cada producto
        productos_con_variantes = []
        for p in productos:
            variantes = await EcomerceProductosVariantes.find(
                EcomerceProductosVariantes.product_id == str(p.id)
            ).to_list()
            
            productos_con_variantes.append({
                "id": str(p.id),
                "codigo": p.codigo,
                "nombre": p.nombre,
                "descripcion": p.descripcion,
                "id_categoria": p.id_categoria,
                "precio": float(p.precio) if p.precio else 0.0,
                "imagen_url": p.imagen_url,
                "active": p.active,
                "variantes": [
                    {
                        "id": str(v.id),
                        "color": v.color,
                        "tipo": v.tipo,
                        "stock": v.stock,
                        "precio_adicional": float(v.precio_adicional) if v.precio_adicional else 0.0,
                        "imagen_url": v.imagen_url,
                        "active": v.active
                    }
                    for v in variantes
                ]
            })
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "productos": productos_con_variantes,
            "categorias": [
                {
                    "id": str(c.id),
                    "nombre": c.nombre,
                    "descripcion": c.descripcion
                }
                for c in categorias
            ]
        }
    except Exception as e:
        logger.error(f"Error listando productos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando productos"
        )


@router.get("/api/{producto_id}")
async def obtener_producto(
    producto_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener detalles de un producto específico"""
    try:
        producto = await EcomerceProductos.get(producto_id)
        
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )
        
        # Obtener variantes del producto
        variantes = await EcomerceProductosVariantes.find(
            EcomerceProductosVariantes.product_id == str(producto.id)
        ).to_list()
        
        return {
            "id": str(producto.id),
            "codigo": producto.codigo,
            "nombre": producto.nombre,
            "descripcion": producto.descripcion,
            "id_categoria": producto.id_categoria,
            "precio": float(producto.precio) if producto.precio else 0.0,
            "imagen_url": producto.imagen_url,
            "active": producto.active,
            "variantes": [
                {
                    "id": str(v.id),
                    "color": v.color,
                    "tipo": v.tipo,
                    "precio_adicional": float(v.precio_adicional) if v.precio_adicional else 0.0,
                    "stock": v.stock,
                    "imagen_url": v.imagen_url,
                    "active": v.active
                }
                for v in variantes
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo producto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo producto"
        )


@router.post("/api/create")
async def crear_producto(
    producto_data: ProductoCreate,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Crear un nuevo producto"""
    try:
        # Verificar si el código ya existe (solo si se proporciona)
        if producto_data.codigo:
            existe = await EcomerceProductos.find_one(
                EcomerceProductos.codigo == producto_data.codigo
            )
            
            if existe:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Ya existe un producto con ese código"
                )
        
        # Crear nuevo producto
        nuevo_producto = EcomerceProductos(
            codigo=producto_data.codigo,
            nombre=producto_data.nombre,
            descripcion=producto_data.descripcion,
            id_categoria=producto_data.id_categoria if producto_data.id_categoria else "",
            precio=int(producto_data.precio),
            imagen_url=producto_data.imagen_url,
            active=producto_data.active
        )
        
        await nuevo_producto.insert()
        
        logger.info(f"Producto creado por admin {admin_user.usuario}: {nuevo_producto.id}")
        
        return {
            "message": "Producto creado exitosamente",
            "producto": {
                "id": str(nuevo_producto.id),
                "codigo": nuevo_producto.codigo,
                "nombre": nuevo_producto.nombre,
                "precio": nuevo_producto.precio
            }
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando producto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creando producto"
        )


@router.put("/api/{producto_id}")
async def actualizar_producto(
    producto_id: str,
    producto_data: ProductoUpdate,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Actualizar un producto existente"""
    try:
        producto = await EcomerceProductos.get(producto_id)
        
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )
        
        logger.info(f"Actualizando producto {producto_id}. Código actual: {producto.codigo}, Nuevo código: {producto_data.codigo}")
        
        # Actualizar campos proporcionados
        if producto_data.codigo is not None:
            # Solo validar si el código cambió
            if producto_data.codigo != producto.codigo:
                # Verificar que el código no esté en uso por otro producto
                existe = await EcomerceProductos.find_one(
                    EcomerceProductos.codigo == producto_data.codigo
                )
                if existe:
                    logger.warning(f"Conflicto: producto {existe.id} ya tiene el código {producto_data.codigo}")
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Ya existe otro producto con ese código"
                    )
            producto.codigo = producto_data.codigo
        
        if producto_data.nombre is not None:
            producto.nombre = producto_data.nombre
        if producto_data.descripcion is not None:
            producto.descripcion = producto_data.descripcion
        if producto_data.id_categoria is not None:
            producto.id_categoria = producto_data.id_categoria
        if producto_data.precio is not None:
            producto.precio = int(producto_data.precio)
        if producto_data.imagen_url is not None:
            producto.imagen_url = producto_data.imagen_url
        if producto_data.active is not None:
            producto.active = producto_data.active
        
        await producto.save()
        
        logger.info(f"Producto {producto_id} actualizado por admin {admin_user.usuario}")
        
        return {
            "message": "Producto actualizado exitosamente",
            "producto_id": str(producto.id)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando producto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando producto"
        )


@router.delete("/api/{producto_id}")
async def eliminar_producto(
    producto_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Eliminar un producto (desactivarlo)"""
    try:
        producto = await EcomerceProductos.get(producto_id)
        
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )
        
        # En lugar de eliminar, desactivar el producto
        producto.active = False
        await producto.save()
        
        logger.info(f"Producto {producto_id} desactivado por admin {admin_user.usuario}")
        
        return {
            "message": "Producto desactivado exitosamente",
            "producto_id": producto_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando producto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando producto"
        )


@router.post("/api/{producto_id}/toggle-active")
async def toggle_producto_activo(
    producto_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Activar/desactivar un producto"""
    try:
        producto = await EcomerceProductos.get(producto_id)
        
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )
        
        # Cambiar el estado
        producto.active = not producto.active
        await producto.save()
        
        logger.info(
            f"Producto {producto_id} {'activado' if producto.active else 'desactivado'} "
            f"por admin {admin_user.usuario}"
        )
        
        return {
            "message": f"Producto {'activado' if producto.active else 'desactivado'} exitosamente",
            "producto_id": producto_id,
            "active": producto.active
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando estado del producto: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cambiando estado del producto"
        )
