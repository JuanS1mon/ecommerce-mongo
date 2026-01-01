"""
Router de Gestión de Pedidos para Admin - Migrado a MongoDB/Beanie
Ver y gestionar todos los pedidos del ecommerce
"""
import logging
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel
from bson import ObjectId
from beanie.operators import Or, RegEx, In

from Projects.ecomerce.models.pedidos_beanie import EcomercePedidos
from Projects.ecomerce.models.pedido_historial_beanie import EcomercePedidoHistorial
from Projects.ecomerce.models.productos_beanie import EcomerceProductos
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.middleware.admin_auth import require_admin
from Projects.Admin.utils.template_helpers import render_admin_template
from Services.mail.mail import enviar_email_simple
import json

logger = logging.getLogger(__name__)

# Mapeo de estados a emojis y colores
ESTADO_INFO = {
    'pendiente': {'emoji': '⏳', 'color': '#FFA500', 'texto': 'Pedido Pendiente'},
    'pendiente_pago_efectivo': {'emoji': '💵', 'color': '#f39c12', 'texto': 'Pendiente Pago Efectivo'},
    'procesando': {'emoji': '📦', 'color': '#3498db', 'texto': 'Procesando Pedido'},
    'enviado': {'emoji': '🚚', 'color': '#9b59b6', 'texto': 'Pedido Enviado'},
    'entregado': {'emoji': '✅', 'color': '#27ae60', 'texto': 'Pedido Entregado'},
    'cancelado': {'emoji': '❌', 'color': '#e74c3c', 'texto': 'Pedido Cancelado'}
}

# Flujo de estados
FLUJO_ESTADOS_PEDIDOS = {
    'pendiente': 'procesando',
    'pendiente_pago_efectivo': 'procesando',
    'procesando': 'enviado',
    'enviado': 'entregado',
    'entregado': None,
    'cancelado': None
}

# Estados válidos
ESTADOS_VALIDOS = ['pendiente', 'pendiente_pago_efectivo', 'procesando', 'enviado', 'entregado', 'cancelado']

def generar_email_html(nombre: str, pedido_id: str, estado_anterior: str, estado_nuevo: str, total: float) -> str:
    """Genera un email HTML con formato atractivo para notificación de cambio de estado"""
    
    info_nuevo = ESTADO_INFO.get(estado_nuevo, {'emoji': '📋', 'color': '#95a5a6', 'texto': estado_nuevo.upper()})
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f4f4;">
        <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f4f4f4; padding: 20px;">
            <tr>
                <td align="center">
                    <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 10px; overflow: hidden;">
                        <tr>
                            <td style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center;">
                                <h1 style="color: #ffffff; margin: 0; font-size: 28px;">Actualización de Pedido</h1>
                            </td>
                        </tr>
                        <tr>
                            <td style="padding: 40px 30px;">
                                <p style="color: #333333; font-size: 16px;">Hola <strong>{nombre}</strong>,</p>
                                <p style="color: #333333; font-size: 16px;">Te informamos que el estado de tu pedido ha sido actualizado.</p>
                                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-radius: 8px; margin: 20px 0;">
                                    <tr>
                                        <td style="padding: 25px;">
                                            <p><strong>Número de Pedido:</strong> #{pedido_id}</p>
                                            <p><strong>Total:</strong> ${total:.2f}</p>
                                            <p>Estado anterior: {estado_anterior.upper()}</p>
                                            <div style="background-color: {info_nuevo['color']}; color: #ffffff; padding: 15px; border-radius: 6px; text-align: center; margin-top: 15px;">
                                                <span style="font-size: 24px;">{info_nuevo['emoji']}</span>
                                                <span style="font-size: 18px; font-weight: bold;"> {info_nuevo['texto']}</span>
                                            </div>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                        <tr>
                            <td style="background-color: #f8f9fa; padding: 20px; text-align: center;">
                                <p style="color: #999999; font-size: 12px;">© 2024 Tu Tienda Online. Todos los derechos reservados.</p>
                            </td>
                        </tr>
                    </table>
                </td>
            </tr>
        </table>
    </body>
    </html>
    """
    return html

router = APIRouter(
    prefix="/admin/pedidos",
    tags=["admin-pedidos"]
)

# Pydantic models
class EstadoUpdate(BaseModel):
    estado: str

class EstadoBulkUpdate(BaseModel):
    pedido_ids: List[str]
    estado: str

class ItemPedido(BaseModel):
    id_producto: str
    cantidad: int
    precio_unitario: float
    nombre_producto: str

class EditarPedidoRequest(BaseModel):
    items: List[ItemPedido]
    motivo: Optional[str] = None


@router.get("/", response_class=HTMLResponse)
async def lista_pedidos_view(request: Request):
    """Vista de lista de pedidos para el admin"""
    try:
        return render_admin_template(
            "pedidos.html",
            request,
            active_page="pedidos",
            now=datetime.now().timestamp()
        )
    except Exception as e:
        logger.error(f"Error cargando pedidos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando pedidos"
        )


@router.get("/api/list")
async def listar_pedidos_api(
    admin_user: AdminUsuarios = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    metodo_pago: Optional[str] = None,
    search: Optional[str] = None,
    fecha_desde: Optional[str] = None,
    fecha_hasta: Optional[str] = None,
    usuario_id: Optional[str] = None
):
    """API para listar pedidos con filtros"""
    try:
        # Construir filtros
        filtros = []
        
        if estado and estado in ESTADOS_VALIDOS:
            filtros.append(EcomercePedidos.estado == estado)
        
        if metodo_pago:
            filtros.append(EcomercePedidos.metodo_pago == metodo_pago)
        
        if search:
            # Buscar por ObjectId de pedido o en usuarios
            try:
                pedido_oid = ObjectId(search)
                filtros.append(EcomercePedidos.id == pedido_oid)
            except:
                # Buscar usuarios por nombre/email
                usuarios_match = await EcomerceUsuarios.find(
                    Or(
                        RegEx(EcomerceUsuarios.nombre, search, "i"),
                        RegEx(EcomerceUsuarios.email, search, "i")
                    )
                ).to_list()
                
                if usuarios_match:
                    usuarios_ids = [u.id for u in usuarios_match]
                    filtros.append(In(EcomercePedidos.id_usuario, usuarios_ids))
                else:
                    return {"total": 0, "skip": skip, "limit": limit, "pedidos": []}
        
        if fecha_desde:
            fecha_desde_dt = datetime.strptime(fecha_desde, '%Y-%m-%d')
            filtros.append(EcomercePedidos.created_at >= fecha_desde_dt)
        
        if fecha_hasta:
            fecha_hasta_dt = datetime.strptime(fecha_hasta, '%Y-%m-%d')
            filtros.append(EcomercePedidos.created_at <= fecha_hasta_dt)
        
        if usuario_id:
            filtros.append(EcomercePedidos.id_usuario == ObjectId(usuario_id))
        
        # Query con filtros
        if filtros:
            query = EcomercePedidos.find(*filtros)
        else:
            query = EcomercePedidos.find()
        
        # Total y paginación
        total = await query.count()
        pedidos = await query.sort("-created_at").skip(skip).limit(limit).to_list()
        
        # Obtener información de usuarios
        usuarios_ids = []
        for p in pedidos:
            if p.id_usuario:
                try:
                    usuarios_ids.append(ObjectId(p.id_usuario))
                except:
                    pass
        
        usuarios = await EcomerceUsuarios.find(
            In(EcomerceUsuarios.id, usuarios_ids)
        ).to_list() if usuarios_ids else []
        
        # Crear diccionario con strings como keys para comparar
        usuarios_dict = {str(u.id): u for u in usuarios}
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "pedidos": [
                {
                    "id": str(p.id),
                    "id_usuario": str(p.id_usuario) if p.id_usuario else None,
                    "usuario_nombre": usuarios_dict.get(str(p.id_usuario)).nombre if p.id_usuario and str(p.id_usuario) in usuarios_dict else "Usuario desconocido",
                    "usuario_email": usuarios_dict.get(str(p.id_usuario)).email if p.id_usuario and str(p.id_usuario) in usuarios_dict else "",
                    "usuario_telefono": usuarios_dict.get(str(p.id_usuario)).telefono if p.id_usuario and str(p.id_usuario) in usuarios_dict else "",
                    "fecha_pedido": p.created_at.isoformat() if p.created_at else None,
                    "total": float(p.total),
                    "estado": p.estado,
                    "metodo_pago": p.metodo_pago,
                    "external_reference": p.external_reference,
                    "items_count": len(p.items) if p.items else 0
                }
                for p in pedidos
            ]
        }
    except Exception as e:
        logger.error(f"Error listando pedidos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error listando pedidos: {str(e)}"
        )


@router.get("/api/estadisticas")
async def obtener_estadisticas_pedidos(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener estadísticas de pedidos"""
    try:
        # Corregido: usar find() en lugar de find_all()
        pedidos = await EcomercePedidos.find().to_list()
        
        # Agrupar por estado
        stats = {}
        for pedido in pedidos:
            estado = pedido.estado if pedido.estado else "sin_estado"
            if estado not in stats:
                stats[estado] = {"total_pedidos": 0, "suma_total": 0.0}
            stats[estado]["total_pedidos"] += 1
            stats[estado]["suma_total"] += float(pedido.total) if pedido.total else 0.0
        
        logger.info(f"Estadísticas calculadas: {stats}")
        
        return {
            "por_estado": [
                {
                    "estado": estado,
                    "total_pedidos": data["total_pedidos"],
                    "suma_total": data["suma_total"]
                }
                for estado, data in stats.items()
            ]
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de pedidos: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.get("/api/{pedido_id}")
async def obtener_pedido(
    pedido_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener detalles completos de un pedido"""
    try:
        logger.info(f"Obteniendo pedido {pedido_id}")
        pedido = await EcomercePedidos.get(ObjectId(pedido_id))
        
        if not pedido:
            logger.warning(f"Pedido {pedido_id} no encontrado")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado"
            )
        
        # Obtener información del usuario
        usuario = None
        if pedido.id_usuario:
            usuario = await EcomerceUsuarios.get(pedido.id_usuario)
        
        return {
            "id": str(pedido.id),
            "id_usuario": str(pedido.id_usuario) if pedido.id_usuario else None,
            "usuario_nombre": usuario.nombre if usuario else "Usuario desconocido",
            "usuario_email": usuario.email if usuario else "",
            "usuario_telefono": usuario.telefono if usuario else "",
            "fecha_pedido": pedido.created_at.isoformat() if pedido.created_at else None,
            "total": float(pedido.total),
            "estado": pedido.estado,
            "metodo_pago": pedido.metodo_pago,
            "external_reference": pedido.external_reference,
            "items": [
                {
                    "id_producto": item.get("id_producto"),
                    "nombre_producto": item.get("nombre_producto"),
                    "cantidad": item.get("cantidad", 0),
                    "precio_unitario": float(item.get("precio_unitario", 0)),
                    "subtotal": float(item.get("cantidad", 0) * item.get("precio_unitario", 0))
                }
                for item in (pedido.items or [])
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo pedido: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo pedido: {str(e)}"
        )


@router.put("/api/{pedido_id}/estado")
async def cambiar_estado_pedido(
    pedido_id: str,
    estado_data: EstadoUpdate,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Cambiar el estado de un pedido"""
    try:
        if estado_data.estado not in ESTADOS_VALIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado inválido. Estados válidos: {', '.join(ESTADOS_VALIDOS)}"
            )
        
        # Obtener el pedido
        pedido = await EcomercePedidos.get(ObjectId(pedido_id))
        
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado"
            )
        
        # Obtener información del usuario
        usuario = None
        if pedido.id_usuario:
            usuario = await EcomerceUsuarios.get(pedido.id_usuario)
        
        estado_anterior = pedido.estado
        pedido.estado = estado_data.estado
        await pedido.save()
        
        # Crear historial
        historial = EcomercePedidoHistorial(
            id_pedido=str(pedido.id),
            estado_anterior=estado_anterior,
            estado_nuevo=estado_data.estado,
            id_usuario_admin=str(admin_user.id),
            fecha=datetime.now()
        )
        await historial.insert()
        
        logger.info(
            f"Estado del pedido {pedido_id} cambiado de '{estado_anterior}' a '{estado_data.estado}' "
            f"por admin {admin_user.usuario}"
        )
        
        # Enviar email de notificación
        if usuario and usuario.email:
            try:
                asunto = f"Actualización de tu pedido #{pedido_id}"
                mensaje_html = generar_email_html(
                    nombre=usuario.nombre or 'Cliente',
                    pedido_id=pedido_id,
                    estado_anterior=estado_anterior,
                    estado_nuevo=estado_data.estado,
                    total=pedido.total
                )
                enviar_email_simple(usuario.email, asunto, mensaje_html)
                logger.info(f"Email enviado a {usuario.email}")
            except Exception as email_error:
                logger.error(f"Error enviando email: {str(email_error)}")
        
        return {
            "message": "Estado del pedido actualizado exitosamente",
            "pedido_id": pedido_id,
            "estado_anterior": estado_anterior,
            "estado_nuevo": estado_data.estado
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cambiando estado del pedido: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error cambiando estado del pedido: {str(e)}"
        )


@router.put("/api/estado/bulk")
async def actualizar_estado_bulk(
    update_data: EstadoBulkUpdate,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Actualizar estado de múltiples pedidos a la vez"""
    try:
        # Validar que el estado sea válido
        if update_data.estado not in ESTADOS_VALIDOS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Estado '{update_data.estado}' no válido. Estados válidos: {', '.join(ESTADOS_VALIDOS)}"
            )
        
        # Validar que haya al menos un pedido
        if not update_data.pedido_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe proporcionar al menos un ID de pedido"
            )
        
        # Convertir IDs de string a ObjectId
        pedido_object_ids = []
        for pedido_id in update_data.pedido_ids:
            try:
                pedido_object_ids.append(ObjectId(pedido_id))
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"ID de pedido inválido: {pedido_id}"
                )
        
        # Buscar todos los pedidos
        pedidos = await EcomercePedidos.find(
            In(EcomercePedidos.id, pedido_object_ids)
        ).to_list()
        
        if not pedidos:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No se encontraron pedidos con los IDs proporcionados"
            )
        
        actualizados = 0
        errores = []
        
        # Actualizar cada pedido
        for pedido in pedidos:
            try:
                estado_anterior = pedido.estado
                pedido.estado = update_data.estado
                await pedido.save()
                
                # Registrar en historial
                historial = EcomercePedidoHistorial(
                    id_pedido=pedido.id,
                    estado_anterior=estado_anterior,
                    estado_nuevo=update_data.estado,
                    id_usuario_admin=admin_user.id,
                    fecha=datetime.now()
                )
                await historial.insert()
                
                # Enviar email si el pedido tiene usuario
                if pedido.id_usuario:
                    try:
                        usuario = await EcomerceUsuarios.get(pedido.id_usuario)
                        if usuario and usuario.email:
                            email_html = generar_email_html(
                                nombre=usuario.nombre,
                                pedido_id=str(pedido.id),
                                estado_anterior=estado_anterior,
                                estado_nuevo=update_data.estado,
                                total=pedido.total
                            )
                            
                            info_estado = ESTADO_INFO.get(update_data.estado, {'texto': update_data.estado})
                            await enviar_email_simple(
                                destinatario=usuario.email,
                                asunto=f"Actualización de tu pedido #{str(pedido.id)[-8:]} - {info_estado['texto']}",
                                html=email_html
                            )
                    except Exception as email_error:
                        logger.warning(f"Error enviando email para pedido {pedido.id}: {str(email_error)}")
                
                actualizados += 1
                
            except Exception as e:
                logger.error(f"Error actualizando pedido {pedido.id}: {str(e)}")
                errores.append({
                    "pedido_id": str(pedido.id),
                    "error": str(e)
                })
        
        return {
            "success": True,
            "actualizados": actualizados,
            "total": len(update_data.pedido_ids),
            "errores": errores,
            "message": f"Se actualizaron {actualizados} de {len(update_data.pedido_ids)} pedidos"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en actualización bulk: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando pedidos: {str(e)}"
        )


@router.post("/api/{pedido_id}/siguiente-estado")
async def avanzar_siguiente_estado_pedido(
    pedido_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Avanzar automáticamente al siguiente estado en el flujo"""
    try:
        pedido = await EcomercePedidos.get(ObjectId(pedido_id))
        
        if not pedido:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Pedido no encontrado"
            )
        
        estado_actual = pedido.estado
        siguiente_estado = FLUJO_ESTADOS_PEDIDOS.get(estado_actual)
        
        if siguiente_estado is None:
            if estado_actual == 'entregado':
                mensaje = "El pedido ya está entregado (estado final)"
            elif estado_actual == 'cancelado':
                mensaje = "El pedido está cancelado"
            else:
                mensaje = "No hay siguiente estado definido"
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=mensaje
            )
        
        # Cambiar al siguiente estado
        estado_anterior = pedido.estado
        pedido.estado = siguiente_estado
        await pedido.save()
        
        # Crear historial
        historial = EcomercePedidoHistorial(
            id_pedido=str(pedido.id),
            estado_anterior=estado_anterior,
            estado_nuevo=siguiente_estado,
            id_usuario_admin=str(admin_user.id),
            fecha=datetime.now()
        )
        await historial.insert()
        
        logger.info(
            f"Pedido {pedido_id} avanzado de '{estado_anterior}' a '{siguiente_estado}' "
            f"por admin {admin_user.usuario}"
        )
        
        return {
            "message": "Pedido avanzado al siguiente estado",
            "pedido_id": pedido_id,
            "estado_anterior": estado_anterior,
            "estado_nuevo": siguiente_estado
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error avanzando estado del pedido: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error avanzando estado: {str(e)}"
        )


@router.get("/api/{pedido_id}/historial")
async def obtener_historial_pedido(
    pedido_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener historial de cambios de estado de un pedido"""
    try:
        historial = await EcomercePedidoHistorial.find(
            EcomercePedidoHistorial.id_pedido == ObjectId(pedido_id)
        ).sort("-fecha").to_list()
        
        # Obtener información de admins
        admin_ids = [h.id_usuario_admin for h in historial if h.id_usuario_admin]
        admins = await AdminUsuarios.find(
            AdminUsuarios.id.in_(admin_ids)
        ).to_list() if admin_ids else []
        admins_dict = {a.id: a for a in admins}
        
        return {
            "historial": [
                {
                    "id": str(h.id),
                    "estado_anterior": h.estado_anterior,
                    "estado_nuevo": h.estado_nuevo,
                    "admin_nombre": admins_dict.get(h.id_usuario_admin).nombre if h.id_usuario_admin in admins_dict else "Desconocido",
                    "fecha": h.fecha.isoformat() if h.fecha else None
                }
                for h in historial
            ]
        }
    except Exception as e:
        logger.error(f"Error obteniendo historial: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo historial: {str(e)}"
        )
