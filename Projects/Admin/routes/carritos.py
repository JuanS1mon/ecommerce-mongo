"""
Router de Gestión de Carritos para Admin
Ver y gestionar todos los carritos del ecommerce
"""
import logging
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

from Projects.ecomerce.models.carritos_beanie import EcomerceCarritos
from Projects.ecomerce.models.productos_beanie import EcomerceProductos
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.middleware.admin_auth import require_admin
from Projects.Admin.utils.template_helpers import render_admin_template

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/carritos",
    tags=["admin-carritos"]
)

# Estados de carrito (solo para visualización)
ESTADOS_CARRITO = ['activo', 'completado', 'abandonado']


@router.get("/", response_class=HTMLResponse)
async def lista_carritos_view(
    request: Request
):
    """Vista de lista de carritos para el admin (autenticación en frontend)"""
    try:
        return render_admin_template(
            "carritos.html",
            request,
            active_page="carritos"
        )
    except Exception as e:
        logger.error(f"Error cargando carritos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando carritos"
        )


@router.get("/api/list")
async def listar_carritos_api(
    admin_user: AdminUsuarios = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    search: Optional[str] = None
):
    """
    API para listar carritos con filtros
    
    Query params:
    - skip: Número de carritos a saltar (paginación)
    - limit: Número máximo de carritos a devolver
    - estado: Filtrar por estado
    - search: Buscar por ID de carrito, nombre de usuario o email
    """
    from beanie.operators import Or, RegEx
    from bson import ObjectId
    try:
        # Construir filtros
        filtros = []
        
        if estado:
            filtros.append(EcomerceCarritos.estado == estado)
        
        # Búsqueda
        if search:
            try:
                # Intentar buscar por ObjectId de carrito
                carrito_oid = ObjectId(search)
                filtros.append(EcomerceCarritos.id == carrito_oid)
            except:
                # Si no es ObjectId, buscar usuarios por nombre/email
                usuarios_match = await EcomerceUsuarios.find(
                    Or(
                        RegEx(EcomerceUsuarios.nombre, search, "i"),
                        RegEx(EcomerceUsuarios.email, search, "i")
                    )
                ).to_list()
                
                if usuarios_match:
                    usuarios_ids = [u.id for u in usuarios_match]
                    from beanie.operators import In
                    filtros.append(In(EcomerceCarritos.id_usuario, usuarios_ids))
                else:
                    # Si no hay usuarios, no hay resultados
                    return {
                        "total": 0,
                        "skip": skip,
                        "limit": limit,
                        "carritos": []
                    }
        
        # Query con filtros
        if filtros:
            query = EcomerceCarritos.find(*filtros)
        else:
            query = EcomerceCarritos.find()
        
        # Total y carritos paginados
        total = await query.count()
        carritos = await query.sort("-created_at").skip(skip).limit(limit).to_list()
        
        # Obtener información de usuarios
        # Convertir id_usuario a ObjectId (puede ser str u ObjectId)
        usuarios_ids = []
        for c in carritos:
            if c.id_usuario:
                try:
                    if isinstance(c.id_usuario, str):
                        # Si es string, intentar convertir a ObjectId
                        if len(c.id_usuario) == 24:
                            usuarios_ids.append(ObjectId(c.id_usuario))
                    else:
                        usuarios_ids.append(c.id_usuario)
                except:
                    pass
        
        from beanie.operators import In
        usuarios = await EcomerceUsuarios.find(
            In(EcomerceUsuarios.id, usuarios_ids)
        ).to_list() if usuarios_ids else []
        usuarios_dict = {u.id: u for u in usuarios}
        
        # También crear un dict con string keys para compatibilidad
        usuarios_dict_str = {str(u.id): u for u in usuarios}
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "carritos": [
                {
                    "id": str(c.id),
                    "id_usuario": str(c.id_usuario) if c.id_usuario else None,
                    "usuario_nombre": (
                        usuarios_dict.get(c.id_usuario).nombre if c.id_usuario in usuarios_dict
                        else usuarios_dict_str.get(str(c.id_usuario)).nombre if str(c.id_usuario) in usuarios_dict_str
                        else "Usuario desconocido"
                    ),
                    "estado": c.estado,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "items_count": len(c.items) if c.items else 0,
                    "total_carrito": sum(item.get("precio_unitario", 0) * item.get("cantidad", 0) for item in (c.items or []))
                }
                for c in carritos
            ]
        }
    except Exception as e:
        logger.error(f"Error listando carritos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando carritos: {str(e)}"
        )


@router.get("/api/estadisticas")
async def obtener_estadisticas_carritos(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener estadísticas de carritos por estado"""
    try:
        logger.info(f"=== INICIO estadisticas - Usuario: {admin_user.usuario if admin_user else 'None'} ===")
        
        # Obtener todos los carritos
        carritos = await EcomerceCarritos.find().to_list()
        
        # Agrupar por estado
        stats = {}
        for carrito in carritos:
            estado = carrito.estado if carrito.estado else "sin_estado"
            
            if estado not in stats:
                stats[estado] = {"total_carritos": 0, "suma_total": 0.0}
            
            stats[estado]["total_carritos"] += 1
            
            # Calcular total del carrito
            if carrito.items:
                total_carrito = sum(
                    item.get("precio_unitario", 0) * item.get("cantidad", 0)
                    for item in carrito.items
                )
                stats[estado]["suma_total"] += total_carrito
        
        # Convertir a lista
        result_list = [
            {
                "estado": estado,
                "total_carritos": data["total_carritos"],
                "suma_total": data["suma_total"]
            }
            for estado, data in stats.items()
        ]
        
        logger.info(f"=== Retornando estadísticas con {len(result_list)} estados ===")
        logger.info(f"Result list: {result_list}")
        
        return {
            "por_estado": result_list
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de carritos: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/api/{carrito_id}")
async def obtener_carrito_detalle(
    carrito_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener detalles completos de un carrito"""
    from bson import ObjectId
    try:
        logger.info(f"Obteniendo carrito {carrito_id}")
        
        carrito = await EcomerceCarritos.get(ObjectId(carrito_id))
        
        if not carrito:
            logger.warning(f"Carrito {carrito_id} no encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Carrito no encontrado"
            )
        
        logger.info(f"Carrito encontrado: {carrito.id}, Estado: {carrito.estado}")
        
        # Obtener información del usuario
        usuario = None
        if carrito.id_usuario:
            try:
                # Intentar buscar el usuario por ID
                if isinstance(carrito.id_usuario, str):
                    # Si es string, buscar directamente por ese valor
                    # Puede ser un ID numérico legacy o un ObjectId en formato string
                    try:
                        # Intentar como ObjectId primero
                        usuario_oid = ObjectId(carrito.id_usuario)
                        usuario = await EcomerceUsuarios.get(usuario_oid)
                    except:
                        # Si falla, buscar por id como string
                        usuario = await EcomerceUsuarios.find_one(
                            EcomerceUsuarios.id == carrito.id_usuario
                        )
                else:
                    # Si ya es ObjectId, buscar directamente
                    usuario = await EcomerceUsuarios.get(carrito.id_usuario)
            except Exception as e:
                logger.warning(f"No se pudo obtener usuario {carrito.id_usuario}: {str(e)}")
        
        # Obtener información de productos para los items
        productos_ids = [ObjectId(item.get("id_producto")) for item in (carrito.items or []) if item.get("id_producto")]
        from beanie.operators import In
        productos = await EcomerceProductos.find(
            In(EcomerceProductos.id, productos_ids)
        ).to_list() if productos_ids else []
        productos_dict = {p.id: p for p in productos}
        
        # Calcular total
        total_carrito = sum(
            item.get("precio_unitario", 0) * item.get("cantidad", 0)
            for item in (carrito.items or [])
        )
        
        return {
            "id": str(carrito.id),
            "id_usuario": str(carrito.id_usuario) if carrito.id_usuario else None,
            "usuario_nombre": usuario.nombre if usuario else "Usuario desconocido",
            "usuario_email": usuario.email if usuario else "",
            "usuario_telefono": usuario.telefono if usuario else "",
            "estado": carrito.estado,
            "created_at": carrito.created_at.isoformat() if carrito.created_at else None,
            "total_carrito": float(total_carrito),
            "items": [
                {
                    "id_producto": item.get("id_producto"),
                    "nombre_producto": productos_dict.get(ObjectId(item.get("id_producto"))).nombre if item.get("id_producto") and ObjectId(item.get("id_producto")) in productos_dict else "Producto desconocido",
                    "cantidad": item.get("cantidad", 0),
                    "precio_unitario": float(item.get("precio_unitario", 0)),
                    "subtotal": float(item.get("cantidad", 0) * item.get("precio_unitario", 0))
                }
                for item in (carrito.items or [])
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo carrito: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo carrito: {str(e)}"
        )


