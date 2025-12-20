# ============================================================================
# CUPONES - API ROUTES
# ============================================================================
# Rutas para gestión de cupones de descuento

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import logging

from Projects.ecomerce.models.cupones_beanie import EcomerceCupones
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from security.get_optional_user import get_optional_user
from security.jwt_auth import get_current_user

router = APIRouter()
logger = logging.getLogger(__name__)

# Pydantic models
class CuponCreate(BaseModel):
    codigo: str
    descripcion: str
    tipo_descuento: str  # "porcentaje" o "monto_fijo"
    valor_descuento: float
    fecha_expiracion: Optional[datetime] = None
    uso_maximo: Optional[int] = None
    activo: bool = True

class CuponResponse(BaseModel):
    id: str
    codigo: str
    descripcion: str
    tipo_descuento: str
    valor_descuento: float
    fecha_expiracion: Optional[datetime]
    uso_maximo: Optional[int]
    usos_actuales: int
    activo: bool
    fecha_creacion: datetime

class CuponValidacion(BaseModel):
    codigo: str
    subtotal: float

class CuponValidacionResponse(BaseModel):
    valido: bool
    cupon: Optional[CuponResponse] = None
    descuento: float = 0
    mensaje: str

# Crear nuevo cupón (solo admin)
@router.post("/", response_model=CuponResponse)
async def crear_cupon(
    cupon_data: CuponCreate,
    current_user: EcomerceUsuarios = Depends(get_current_user)
):
    # TODO: Verificar permisos de admin
    try:
        # Verificar que el código no exista
        existing = await EcomerceCupones.find_one({"codigo": cupon_data.codigo.upper()})
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya existe un cupón con este código"
            )

        cupon = EcomerceCupones(
            codigo=cupon_data.codigo.upper(),
            descripcion=cupon_data.descripcion,
            tipo_descuento=cupon_data.tipo_descuento,
            valor_descuento=cupon_data.valor_descuento,
            fecha_expiracion=cupon_data.fecha_expiracion,
            usos_maximos=cupon_data.uso_maximo,
            activo=cupon_data.activo
        )

        await cupon.insert()
        return cupon

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando cupón: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Obtener todos los cupones (solo admin)
@router.get("/", response_model=List[CuponResponse])
async def obtener_cupones(
    current_user: EcomerceUsuarios = Depends(get_current_user),
    activo: Optional[bool] = None
):
    # TODO: Verificar permisos de admin
    try:
        query = {}
        if activo is not None:
            query["activo"] = activo

        cupones = await EcomerceCupones.find(query).sort([("created_at", -1)]).to_list()
        return cupones

    except Exception as e:
        logger.error(f"Error obteniendo cupones: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Obtener cupón por ID
@router.get("/{cupon_id}", response_model=CuponResponse)
async def obtener_cupon(
    cupon_id: str,
    current_user: EcomerceUsuarios = Depends(get_current_user)
):
    # TODO: Verificar permisos de admin
    try:
        cupon = await EcomerceCupones.get(cupon_id)
        if not cupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupón no encontrado"
            )

        return cupon

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo cupón: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Validar cupón para uso
@router.post("/validar", response_model=CuponValidacionResponse)
async def validar_cupon(
    validacion: CuponValidacion,
    current_user: EcomerceUsuarios = Depends(get_optional_user)
):
    try:
        cupon = await EcomerceCupones.find_one({"codigo": validacion.codigo.upper()})

        if not cupon:
            return CuponValidacionResponse(
                valido=False,
                mensaje="Cupón no encontrado"
            )

        if not cupon.activo:
            return CuponValidacionResponse(
                valido=False,
                mensaje="Este cupón no está activo"
            )

        if cupon.fecha_expiracion and cupon.fecha_expiracion < datetime.utcnow():
            return CuponValidacionResponse(
                valido=False,
                mensaje="Este cupón ha expirado"
            )

        if cupon.usos_maximos and cupon.usos_actuales >= cupon.usos_maximos:
            return CuponValidacionResponse(
                valido=False,
                mensaje="Este cupón ha alcanzado el límite de usos"
            )

        # Calcular descuento
        descuento = 0
        if cupon.tipo_descuento == "porcentaje":
            descuento = validacion.subtotal * (cupon.valor_descuento / 100)
        elif cupon.tipo_descuento == "monto_fijo":
            descuento = min(cupon.valor_descuento, validacion.subtotal)

        return CuponValidacionResponse(
            valido=True,
            cupon=cupon,
            descuento=descuento,
            mensaje="Cupón válido"
        )

    except Exception as e:
        logger.error(f"Error validando cupón: {e}")
        return CuponValidacionResponse(
            valido=False,
            mensaje="Error al validar el cupón"
        )

# Actualizar cupón (solo admin)
@router.put("/{cupon_id}", response_model=CuponResponse)
async def actualizar_cupon(
    cupon_id: str,
    cupon_data: CuponCreate,
    current_user: EcomerceUsuarios = Depends(get_current_user)
):
    # TODO: Verificar permisos de admin
    try:
        cupon = await EcomerceCupones.get(cupon_id)
        if not cupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupón no encontrado"
            )

        # Verificar código único si cambió
        if cupon_data.codigo.upper() != cupon.codigo:
            existing = await EcomerceCupones.find_one({"codigo": cupon_data.codigo.upper()})
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ya existe un cupón con este código"
                )

        # Actualizar campos
        cupon.codigo = cupon_data.codigo.upper()
        cupon.descripcion = cupon_data.descripcion
        cupon.tipo_descuento = cupon_data.tipo_descuento
        cupon.valor_descuento = cupon_data.valor_descuento
        cupon.fecha_expiracion = cupon_data.fecha_expiracion
        cupon.usos_maximos = cupon_data.uso_maximo
        cupon.activo = cupon_data.activo

        await cupon.save()
        return cupon

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando cupón: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Eliminar cupón (solo admin)
@router.delete("/{cupon_id}")
async def eliminar_cupon(
    cupon_id: str,
    current_user: EcomerceUsuarios = Depends(get_current_user)
):
    # TODO: Verificar permisos de admin
    try:
        cupon = await EcomerceCupones.get(cupon_id)
        if not cupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupón no encontrado"
            )

        await cupon.delete()
        return {"message": "Cupón eliminado exitosamente"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando cupón: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )

# Incrementar usos del cupón (llamado internamente al aplicar cupón)
@router.post("/{cupon_id}/usar")
async def usar_cupon(
    cupon_id: str,
    current_user: EcomerceUsuarios = Depends(get_optional_user)
):
    try:
        cupon = await EcomerceCupones.get(cupon_id)
        if not cupon:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cupón no encontrado"
            )

        cupon.usos_actuales += 1
        await cupon.save()

        return {"message": "Uso del cupón registrado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registrando uso del cupón: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )