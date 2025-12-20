# ============================================================================
# LISTA DE DESEOS - API ROUTES
# ============================================================================
# Rutas para gestión de listas de deseos de usuarios

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from Projects.ecomerce.models.lista_deseos_beanie import EcomerceListaDeseos
from Projects.ecomerce.models.productos_beanie import EcomerceProductos
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from security.get_optional_user import get_optional_user
from security.jwt_auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class ListaDeseosCreate(BaseModel):
    producto_id: str

class ListaDeseosResponse(BaseModel):
    id: str
    fecha_agregado: datetime
    producto: Optional[dict] = None

# Agregar producto a lista de deseos
@router.post("/", response_model=dict)
async def agregar_a_lista_deseos(
    lista_data: ListaDeseosCreate,
    current_user: EcomerceUsuarios = Depends(get_current_user)
):
    try:
        # Verificar que el producto existe
        producto = await EcomerceProductos.get(lista_data.producto_id)
        if not producto:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )

        # Verificar que no esté ya en la lista
        existing = await EcomerceListaDeseos.find_one({
            "id_usuario": str(current_user.id),
            "productos.id_producto": lista_data.producto_id
        })

        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El producto ya está en tu lista de deseos"
            )

        # Buscar o crear lista de deseos del usuario
        lista_deseos = await EcomerceListaDeseos.find_one({"id_usuario": str(current_user.id)})
        if not lista_deseos:
            lista_deseos = EcomerceListaDeseos(
                id_usuario=str(current_user.id),
                productos=[]
            )

        # Agregar producto a la lista
        producto_info = {
            "id_producto": lista_data.producto_id,
            "fecha_agregado": datetime.utcnow(),
            "precio_al_agregar": None  # TODO: Obtener precio actual del producto
        }
        lista_deseos.productos.append(producto_info)
        lista_deseos.updated_at = datetime.utcnow()

        if hasattr(lista_deseos, 'id') and lista_deseos.id:
            await lista_deseos.save()
        else:
            await lista_deseos.insert()

        return {
            "message": "Producto agregado a la lista de deseos",
            "lista_deseos_id": str(lista_deseos.id)
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error agregando producto a lista de deseos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Obtener lista de deseos del usuario
@router.get("/", response_model=List[ListaDeseosResponse])
async def obtener_lista_deseos(
    current_user: EcomerceUsuarios = Depends(get_current_user)
):
    try:
        lista_deseos = await EcomerceListaDeseos.find_one({"id_usuario": str(current_user.id)})
        if not lista_deseos:
            return []

        # Enriquecer con información del producto
        productos_enriquecidos = []
        for item in lista_deseos.productos:
            producto = await EcomerceProductos.get(item["id_producto"])
            if producto:
                productos_enriquecidos.append({
                    "id": item["id_producto"],
                    "fecha_agregado": item["fecha_agregado"],
                    "producto": {
                        "id": str(producto.id),
                        "codigo": producto.codigo,
                        "nombre": producto.nombre,
                        "descripcion": producto.descripcion if hasattr(producto, 'descripcion') else None,
                        "precio": producto.precio,
                        "imagen_url": producto.imagen_url,
                        "categoria": producto.id_categoria
                    }
                })

        return productos_enriquecidos

    except Exception as e:
        logger.error(f"Error obteniendo lista de deseos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Verificar si un producto está en la lista de deseos
@router.get("/check/{producto_id}")
async def verificar_en_lista_deseos(
    producto_id: str,
    current_user: EcomerceUsuarios = Depends(get_optional_user)
):
    if not current_user:
        return {"en_lista_deseos": False}

    try:
        lista_deseos = await EcomerceListaDeseos.find_one({"id_usuario": str(current_user.id)})
        if not lista_deseos:
            return {"en_lista_deseos": False}

        # Verificar si el producto está en la lista
        en_lista = any(item["id_producto"] == producto_id for item in lista_deseos.productos)
        return {"en_lista_deseos": en_lista}

    except Exception as e:
        logger.error(f"Error verificando lista de deseos: {e}")
        return {"en_lista_deseos": False}

# Remover producto de la lista de deseos
@router.delete("/{producto_id}")
async def remover_de_lista_deseos(
    producto_id: str,
    current_user: EcomerceUsuarios = Depends(get_current_user)
):
    try:
        lista_deseos = await EcomerceListaDeseos.find_one({"id_usuario": str(current_user.id)})
        if not lista_deseos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No tienes una lista de deseos"
            )

        # Buscar y remover el producto
        producto_encontrado = False
        productos_filtrados = []
        for item in lista_deseos.productos:
            if item["id_producto"] == producto_id:
                producto_encontrado = True
            else:
                productos_filtrados.append(item)

        if not producto_encontrado:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado en la lista de deseos"
            )

        lista_deseos.productos = productos_filtrados
        lista_deseos.updated_at = datetime.utcnow()
        await lista_deseos.save()

        return {"message": "Producto removido de la lista de deseos"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error removiendo producto de lista de deseos: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Obtener conteo de productos en lista de deseos
@router.get("/count")
async def contar_lista_deseos(
    current_user: EcomerceUsuarios = Depends(get_optional_user)
):
    if not current_user:
        return {"count": 0}

    try:
        lista_deseos = await EcomerceListaDeseos.find_one({"id_usuario": str(current_user.id)})
        if not lista_deseos:
            return {"count": 0}

        count = len(lista_deseos.productos)
        return {"count": count}

    except Exception as e:
        logger.error(f"Error contando lista de deseos: {e}")
        return {"count": 0}