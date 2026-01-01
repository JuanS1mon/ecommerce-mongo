"""
Router del Dashboard del Panel de Administración
Muestra estadísticas generales del ecommerce
MIGRADO A MONGODB CON BEANIE
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.ecomerce.models.pedidos_beanie import EcomercePedidos
from Projects.ecomerce.models.productos_beanie import EcomerceProductos
from Projects.ecomerce.models.carritos_beanie import EcomerceCarritos
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from Projects.Admin.middleware.admin_auth import require_admin
from Projects.Admin.utils.template_helpers import render_admin_template

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin",
    tags=["admin-dashboard"]
)


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard_view(
    request: Request
):
    try:
        return render_admin_template(
            "dashboard.html",
            request,
            active_page="dashboard"
        )
    except Exception as e:
        logger.error(f"Error cargando dashboard: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando dashboard"
        )


@router.get("/api/dashboard/stats")
async def get_dashboard_stats_api(
    response: Response,
    admin_user: Any = Depends(require_admin)
):
    """API para obtener estadísticas del dashboard (sin cache)"""
    try:
        # Headers para evitar cache
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        
        logger.info(f"Usuario admin accediendo a stats")
        stats = await get_dashboard_stats()
        return stats
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


async def get_dashboard_stats() -> Dict[str, Any]:
    fecha_inicio = datetime.now() - timedelta(days=30)
    total_productos = await EcomerceProductos.find(EcomerceProductos.active == True).count()
    productos_inactivos = await EcomerceProductos.find(EcomerceProductos.active == False).count()
    total_pedidos = await EcomercePedidos.find_all().count()
    pedidos_pendientes = await EcomercePedidos.find(EcomercePedidos.estado == 'pendiente').count()
    pedidos_procesando = await EcomercePedidos.find(EcomercePedidos.estado == 'procesando').count()
    pedidos_enviados = await EcomercePedidos.find(EcomercePedidos.estado == 'enviado').count()
    pedidos_entregados = await EcomercePedidos.find(EcomercePedidos.estado == 'entregado').count()
    
    from beanie.operators import In
    pedidos_completados = await EcomercePedidos.find(
        In(EcomercePedidos.estado, ['procesando', 'enviado', 'entregado'])
    ).to_list()
    ventas_totales = sum(p.total for p in pedidos_completados if p.total)
    
    pedidos_mes = await EcomercePedidos.find(
        EcomercePedidos.created_at >= fecha_inicio,
        In(EcomercePedidos.estado, ['procesando', 'enviado', 'entregado'])
    ).to_list()
    ventas_mes = sum(p.total for p in pedidos_mes if p.total)
    
    total_usuarios_ecommerce = await EcomerceUsuarios.find_all().count()
    usuarios_activos_ecommerce = await EcomerceUsuarios.find(EcomerceUsuarios.activo == True).count()
    carritos_activos = await EcomerceCarritos.find(EcomerceCarritos.estado == 'activo').count()
    
    fecha_abandono = datetime.now() - timedelta(days=7)
    carritos_abandonados = await EcomerceCarritos.find(
        EcomerceCarritos.estado == 'activo',
        EcomerceCarritos.created_at < fecha_abandono
    ).count()
    
    productos_top = []
    
    pedidos_recientes_docs = await EcomercePedidos.find_all().sort(-EcomercePedidos.created_at).limit(10).to_list()
    
    # Obtener IDs únicos de usuarios de los pedidos
    from bson import ObjectId
    usuarios_ids = list(set([p.id_usuario for p in pedidos_recientes_docs if p.id_usuario]))
    
    # Buscar información de usuarios
    usuarios_map = {}
    if usuarios_ids:
        try:
            # Convertir strings a ObjectId si es necesario
            obj_ids = []
            for uid in usuarios_ids:
                try:
                    if isinstance(uid, str):
                        obj_ids.append(ObjectId(uid))
                    else:
                        obj_ids.append(uid)
                except:
                    pass
            
            from beanie.operators import In as BeanieIn
            usuarios = await EcomerceUsuarios.find(
                BeanieIn(EcomerceUsuarios.id, obj_ids)
            ).to_list()
            
            usuarios_map = {str(u.id): u for u in usuarios}
        except Exception as e:
            logger.error(f"Error obteniendo usuarios: {str(e)}")
    
    return {
        "productos": {
            "total": total_productos,
            "activos": total_productos,
            "inactivos": productos_inactivos
        },
        "pedidos": {
            "total": total_pedidos,
            "pendientes": pedidos_pendientes,
            "procesando": pedidos_procesando,
            "enviados": pedidos_enviados,
            "entregados": pedidos_entregados
        },
        "ventas": {
            "totales": float(ventas_totales),
            "mes_actual": float(ventas_mes),
            "moneda": "ARS"
        },
        "usuarios": {
            "total": total_usuarios_ecommerce,
            "activos": usuarios_activos_ecommerce,
            "inactivos": total_usuarios_ecommerce - usuarios_activos_ecommerce
        },
        "carritos": {
            "activos": carritos_activos,
            "abandonados": carritos_abandonados
        },
        "productos_top": productos_top,
        "pedidos_recientes": [
            {
                "id": str(p.id),
                "usuario_id": str(p.id_usuario) if p.id_usuario else None,
                "usuario_nombre": usuarios_map.get(str(p.id_usuario)).nombre if str(p.id_usuario) in usuarios_map else "Usuario desconocido",
                "usuario_email": usuarios_map.get(str(p.id_usuario)).email if str(p.id_usuario) in usuarios_map else "",
                "usuario_telefono": usuarios_map.get(str(p.id_usuario)).telefono if str(p.id_usuario) in usuarios_map else "",
                "fecha": p.created_at.isoformat() if p.created_at else None,
                "total": float(p.total) if p.total else 0.0,
                "estado": p.estado,
                "metodo_pago": getattr(p, 'metodo_pago', 'N/A')
            }
            for p in pedidos_recientes_docs
        ]
    }


@router.get("/")
async def admin_root(
    request: Request,
    admin_user: Any = Depends(require_admin)
):
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/admin/dashboard", status_code=302)