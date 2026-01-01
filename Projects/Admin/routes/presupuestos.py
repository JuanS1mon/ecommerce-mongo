"""
Router de Gestión de Presupuestos para Admin - Migrado a MongoDB/Beanie
"""
import logging
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from bson import ObjectId
from beanie.operators import Or, RegEx
import base64
import os

from Projects.ecomerce.models.presupuesto_beanie import EcomercePresupuestos
from Projects.ecomerce.models.usuarios import EcomerceUsuarios
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.middleware.admin_auth import require_admin
from Projects.Admin.utils.template_helpers import render_admin_template
from Services.mail.mail import enviar_email_simple
from config import (
    COMPANY_NAME, COMPANY_ADDRESS, COMPANY_PHONE, 
    COMPANY_EMAIL, COMPANY_WEBSITE, COMPANY_TAX_ID
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/presupuestos",
    tags=["admin-presupuestos"]
)

ESTADOS_VALIDOS = ['pendiente', 'contactado', 'presupuestado', 'aprobado', 'rechazado']

ESTADO_INFO = {
    'pendiente': {'emoji': '⏳', 'color': '#FFA500', 'texto': 'Pendiente de Revisión'},
    'contactado': {'emoji': '📞', 'color': '#3498db', 'texto': 'Cliente Contactado'},
    'presupuestado': {'emoji': '📝', 'color': '#9b59b6', 'texto': 'Presupuesto Enviado'},
    'aprobado': {'emoji': '✅', 'color': '#27ae60', 'texto': 'Aprobado'},
    'rechazado': {'emoji': '❌', 'color': '#e74c3c', 'texto': 'Rechazado'}
}

class EstadoUpdate(BaseModel):
    estado: str

class PresupuestoRespuesta(BaseModel):
    productos: List[dict]
    total: float
    observaciones: Optional[str] = None
    validez_dias: int = 30


def generar_presupuesto_html(
    presupuesto,
    productos: List[dict],
    total: float,
    observaciones: str = "",
    validez_dias: int = 30
) -> str:
    """Genera presupuesto HTML"""
    fecha_emision = datetime.now()
    fecha_vencimiento = fecha_emision + timedelta(days=validez_dias)
    
    items_html = ""
    for item in productos:
        items_html += f"""
        <tr>
            <td style="padding: 10px; border-bottom: 1px solid #ddd;">{item.get('nombre', 'N/A')}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: center;">{item.get('cantidad', 0)}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right;">${item.get('precio_unitario', 0):.2f}</td>
            <td style="padding: 10px; border-bottom: 1px solid #ddd; text-align: right; font-weight: bold;">${item.get('subtotal', 0):.2f}</td>
        </tr>
        """
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head><meta charset="UTF-8"></head>
    <body style="font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f4f4f4;">
        <div style="max-width: 800px; margin: 0 auto; background-color: #fff; padding: 30px; border-radius: 8px;">
            <h1 style="color: #333; text-align: center;">PRESUPUESTO</h1>
            <p><strong>Fecha Emisión:</strong> {fecha_emision.strftime('%Y-%m-%d')}</p>
            <p><strong>Válido hasta:</strong> {fecha_vencimiento.strftime('%Y-%m-%d')}</p>
            <p><strong>Cliente:</strong> {presupuesto.nombre_contacto}</p>
            <p><strong>Email:</strong> {presupuesto.email_contacto}</p>
            
            <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
                <thead>
                    <tr style="background-color: #f8f8f8;">
                        <th style="padding: 10px; border-bottom: 2px solid #ddd; text-align: left;">Producto</th>
                        <th style="padding: 10px; border-bottom: 2px solid #ddd; text-align: center;">Cant.</th>
                        <th style="padding: 10px; border-bottom: 2px solid #ddd; text-align: right;">Precio Unit.</th>
                        <th style="padding: 10px; border-bottom: 2px solid #ddd; text-align: right;">Subtotal</th>
                    </tr>
                </thead>
                <tbody>
                    {items_html}
                </tbody>
            </table>
            
            <div style="text-align: right; margin-top: 20px;">
                <p style="font-size: 20px;"><strong>TOTAL: ${total:.2f}</strong></p>
            </div>
            
            {f'<p><strong>Observaciones:</strong> {observaciones}</p>' if observaciones else ''}
            
            <p style="text-align: center; color: #666; margin-top: 30px; font-size: 12px;">
                {COMPANY_NAME} | {COMPANY_EMAIL} | {COMPANY_PHONE}
            </p>
        </div>
    </body>
    </html>
    """
    return html


@router.get("/", response_class=HTMLResponse)
async def lista_presupuestos_view(request: Request):
    """Vista de lista de presupuestos"""
    try:
        return render_admin_template(
            "presupuestos.html",
            request,
            active_page="presupuestos"
        )
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail="Error cargando presupuestos")


@router.get("/api/list")
async def listar_presupuestos_api(
    admin_user: AdminUsuarios = Depends(require_admin),
    skip: int = 0,
    limit: int = 100,
    estado: Optional[str] = None,
    search: Optional[str] = None
):
    """Listar presupuestos con filtros"""
    try:
        filtros = []
        
        if estado and estado in ESTADOS_VALIDOS:
            filtros.append(EcomercePresupuestos.estado == estado)
        
        if search:
            filtros.append(
                Or(
                    RegEx(EcomercePresupuestos.nombre_contacto, search, "i"),
                    RegEx(EcomercePresupuestos.email_contacto, search, "i")
                )
            )
        
        if filtros:
            query = EcomercePresupuestos.find(*filtros)
        else:
            query = EcomercePresupuestos.find()
        
        total = await query.count()
        presupuestos = await query.sort("-fecha_solicitud").skip(skip).limit(limit).to_list()
        
        # Obtener usuarios
        usuarios_ids = [p.id_usuario for p in presupuestos if p.id_usuario]
        usuarios = await EcomerceUsuarios.find(
            EcomerceUsuarios.id.in_(usuarios_ids)
        ).to_list() if usuarios_ids else []
        usuarios_dict = {u.id: u for u in usuarios}
        
        return {
            "total": total,
            "skip": skip,
            "limit": limit,
            "presupuestos": [
                {
                    "id": str(p.id),
                    "nombre_contacto": p.nombre_contacto,
                    "email_contacto": p.email_contacto,
                    "telefono_contacto": p.telefono_contacto,
                    "estado": p.estado,
                    "total": float(p.total),
                    "fecha_solicitud": p.fecha_solicitud.isoformat() if p.fecha_solicitud else None,
                    "items_count": len(p.items) if p.items else 0
                }
                for p in presupuestos
            ]
        }
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error listando presupuestos: {str(e)}")


@router.get("/api/estadisticas")
async def obtener_estadisticas_presupuestos(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener estadísticas de presupuestos"""
    try:
        presupuestos = await EcomercePresupuestos.find().to_list()
        
        stats = {}
        for p in presupuestos:
            estado = p.estado if p.estado else "sin_estado"
            if estado not in stats:
                stats[estado] = {"total": 0, "suma_total": 0.0}
            stats[estado]["total"] += 1
            stats[estado]["suma_total"] += float(p.total) if p.total else 0.0
        
        return {
            "por_estado": [
                {"estado": estado, "total": data["total"], "suma_total": data["suma_total"]}
                for estado, data in stats.items()
            ]
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error obteniendo estadísticas: {str(e)}")


@router.get("/api/{presupuesto_id}")
async def obtener_presupuesto(
    presupuesto_id: str,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener detalles de un presupuesto"""
    try:
        presupuesto = await EcomercePresupuestos.get(ObjectId(presupuesto_id))
        
        if not presupuesto:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        
        return {
            "id": str(presupuesto.id),
            "nombre_contacto": presupuesto.nombre_contacto,
            "email_contacto": presupuesto.email_contacto,
            "telefono_contacto": presupuesto.telefono_contacto,
            "consulta": presupuesto.consulta,
            "estado": presupuesto.estado,
            "total": float(presupuesto.total),
            "fecha_solicitud": presupuesto.fecha_solicitud.isoformat() if presupuesto.fecha_solicitud else None,
            "items": presupuesto.items or []
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.put("/api/{presupuesto_id}/estado")
async def cambiar_estado_presupuesto(
    presupuesto_id: str,
    estado_data: EstadoUpdate,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Cambiar estado de un presupuesto"""
    try:
        if estado_data.estado not in ESTADOS_VALIDOS:
            raise HTTPException(status_code=400, detail="Estado inválido")
        
        presupuesto = await EcomercePresupuestos.get(ObjectId(presupuesto_id))
        
        if not presupuesto:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        
        estado_anterior = presupuesto.estado
        presupuesto.estado = estado_data.estado
        await presupuesto.save()
        
        logger.info(f"Estado de presupuesto {presupuesto_id} cambiado de '{estado_anterior}' a '{estado_data.estado}'")
        
        return {
            "message": "Estado actualizado",
            "presupuesto_id": presupuesto_id,
            "estado_anterior": estado_anterior,
            "estado_nuevo": estado_data.estado
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/api/{presupuesto_id}/enviar")
async def enviar_presupuesto(
    presupuesto_id: str,
    respuesta: PresupuestoRespuesta,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Enviar presupuesto por email"""
    try:
        presupuesto = await EcomercePresupuestos.get(ObjectId(presupuesto_id))
        
        if not presupuesto:
            raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
        
        # Generar HTML
        html_presupuesto = generar_presupuesto_html(
            presupuesto,
            respuesta.productos,
            respuesta.total,
            respuesta.observaciones or "",
            respuesta.validez_dias
        )
        
        # Enviar email
        asunto = f"Presupuesto de {COMPANY_NAME}"
        enviar_email_simple(presupuesto.email_contacto, asunto, html_presupuesto)
        
        # Actualizar estado
        presupuesto.estado = 'presupuestado'
        await presupuesto.save()
        
        logger.info(f"Presupuesto {presupuesto_id} enviado a {presupuesto.email_contacto}")
        
        return {
            "message": "Presupuesto enviado exitosamente",
            "email": presupuesto.email_contacto
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
