"""
Router para sincronización de usuarios admin
============================================

Endpoints administrativos para sincronizar usuarios entre sistemas.
"""

import logging
from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import JSONResponse
from security.jwt_auth import get_current_admin_user
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.services.sincronizar_usuarios import sincronizar_usuarios_admin

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/api/sync", tags=["Admin Sync"])


@router.post(
    "/usuarios",
    summary="Sincronizar usuarios admin",
    description="""
    Sincroniza usuarios administradores desde el sistema de proyectos.
    
    **Requiere autenticación de admin.**
    
    Este endpoint:
    - Obtiene usuarios del proyecto desde la API remota
    - Crea usuarios faltantes en este sistema
    - Actualiza información de usuarios existentes
    - Desactiva usuarios con fecha de vencimiento expirada
    
    **Parámetros:**
    - dry_run: Si es true, simula sin hacer cambios reales
    """
)
async def sincronizar_usuarios(
    request: Request,
    dry_run: bool = Query(False, description="Simular sin hacer cambios"),
    current_admin: AdminUsuarios = Depends(get_current_admin_user)
):
    """
    Sincroniza usuarios administradores.
    
    Args:
        request: Request object
        dry_run: Si es True, solo simula
        current_admin: Usuario admin autenticado
        
    Returns:
        JSONResponse con estadísticas de la sincronización
    """
    try:
        logger.info(f"[SYNC API] Solicitud de sincronización por admin: {current_admin.usuario}")
        
        if dry_run:
            logger.info("[SYNC API] Modo DRY RUN activado")
        
        # Ejecutar sincronización
        estadisticas = await sincronizar_usuarios_admin(dry_run=dry_run)
        
        # Preparar respuesta
        response_data = {
            "success": True,
            "message": "Sincronización completada" if not dry_run else "Simulación completada (no se hicieron cambios)",
            "dry_run": dry_run,
            "estadisticas": estadisticas
        }
        
        logger.info(f"[SYNC API] Sincronización completada: {estadisticas}")
        
        return JSONResponse(
            status_code=200,
            content=response_data
        )
        
    except Exception as e:
        logger.error(f"[SYNC API] Error en sincronización: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": "Error en sincronización",
                "detalle": str(e)
            }
        )


@router.get(
    "/status",
    summary="Estado de la sincronización",
    description="Obtiene información sobre la configuración de sincronización"
)
async def sync_status(
    current_admin: AdminUsuarios = Depends(get_current_admin_user)
):
    """
    Obtiene el estado de configuración de sincronización.
    
    Args:
        current_admin: Usuario admin autenticado
        
    Returns:
        JSONResponse con información de configuración
    """
    from config import FRONTEND_URL
    import os
    
    api_base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
    proyecto_nombre = os.getenv("ADMIN_PROYECTO_NOMBRE", "Ecomerce")
    
    return JSONResponse(
        status_code=200,
        content={
            "api_base_url": api_base_url,
            "proyecto_nombre": proyecto_nombre,
            "configurado": bool(api_base_url and proyecto_nombre)
        }
    )
