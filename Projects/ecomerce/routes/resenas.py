from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Optional
from Projects.ecomerce.models.resenas_beanie import EcomerceResenas, ResenaCreate, ResenaResponse
from Projects.ecomerce.models.productos_beanie import EcomerceProductos
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from security.ecommerce_auth import get_current_ecommerce_user
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/resenas",
    tags=["resenas"]
)

security = HTTPBearer()

@router.post("/", response_model=ResenaResponse)
async def crear_resena(
    resena: ResenaCreate,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Crear una nueva reseña para un producto"""
    try:
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Usuario no autenticado")

        # Verificar que el producto existe
        producto = await EcomerceProductos.get(resena.id_producto)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        # Verificar que no haya reseña previa del usuario para este producto
        resena_existente = await EcomerceResenas.find_one(
            EcomerceResenas.id_usuario == str(user['id']),
            EcomerceResenas.id_producto == resena.id_producto
        )

        if resena_existente:
            raise HTTPException(status_code=400, detail="Ya has reseñado este producto")

        # Crear la reseña
        nueva_resena = EcomerceResenas(
            id_usuario=str(user['id']),
            id_producto=resena.id_producto,
            calificacion=resena.calificacion,
            comentario=resena.comentario,
            titulo=resena.titulo
        )

        await nueva_resena.insert()

        return ResenaResponse(
            id=str(nueva_resena.id),
            id_usuario=nueva_resena.id_usuario,
            id_producto=nueva_resena.id_producto,
            calificacion=nueva_resena.calificacion,
            comentario=nueva_resena.comentario,
            titulo=nueva_resena.titulo,
            verificada=nueva_resena.verificada,
            util=nueva_resena.util,
            no_util=nueva_resena.no_util,
            created_at=nueva_resena.created_at,
            nombre_usuario=user.get('nombre')
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando reseña: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/producto/{producto_id}", response_model=List[ResenaResponse])
async def obtener_resenas_producto(
    producto_id: str,
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0)
):
    """Obtener reseñas de un producto específico"""
    try:
        # Verificar que el producto existe
        producto = await EcomerceProductos.get(producto_id)
        if not producto:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        resenas = await EcomerceResenas.find(
            EcomerceResenas.id_producto == producto_id
        ).sort([("created_at", -1)]).skip(offset).limit(limit).to_list()

        # Obtener nombres de usuarios
        resenas_response = []
        for resena in resenas:
            usuario = await EcomerceUsuarios.get(resena.id_usuario)
            nombre_usuario = usuario.nombre if usuario else "Usuario anónimo"

            resenas_response.append(ResenaResponse(
                id=str(resena.id),
                id_usuario=resena.id_usuario,
                id_producto=resena.id_producto,
                calificacion=resena.calificacion,
                comentario=resena.comentario,
                titulo=resena.titulo,
                verificada=resena.verificada,
                util=resena.util,
                no_util=resena.no_util,
                created_at=resena.created_at,
                nombre_usuario=nombre_usuario
            ))

        return resenas_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo reseñas: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")