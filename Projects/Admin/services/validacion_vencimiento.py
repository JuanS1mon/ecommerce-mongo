"""
Servicio de Validación Interna de Vencimiento de Usuarios Admin
Verifica contra la API de proyectos y actualiza la fecha de vencimiento local
"""
import logging
import os
from datetime import datetime
from typing import Optional, Dict, Any
import httpx
from dotenv import load_dotenv

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios

load_dotenv()
logger = logging.getLogger(__name__)

# URL de la API de validación (puede ser la misma aplicación u otra instancia)
API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
VALIDATE_ENDPOINT = f"{API_BASE_URL}/api/v1/validate"


async def verificar_y_actualizar_vencimiento(usuario: AdminUsuarios, password: str) -> Dict[str, Any]:
    """
    Verifica el vencimiento del usuario contra la API de proyectos y actualiza si es necesario.
    
    Esta función se ejecuta cuando:
    1. El usuario no tiene fecha de vencimiento (null)
    2. La fecha de vencimiento actual es >= a la fecha de hoy
    
    Lógica:
    - Si la fecha de vencimiento local es null o >= hoy, consulta la API
    - Si el proyecto sigue activo en la API, actualiza la fecha local
    - Si hay una fecha diferente en la API, la actualiza localmente
    - Esto evita consultar la API en cada login mientras la fecha sea válida
    
    Args:
        usuario: Usuario admin a verificar
        password: Contraseña del usuario (necesaria para validar en API)
        
    Returns:
        Dict con:
            - actualizado: bool - Si se actualizó la fecha
            - fecha_vencimiento: datetime - Nueva fecha de vencimiento
            - mensaje: str - Mensaje descriptivo
            - error: bool - Si hubo algún error
    """
    try:
        # Si el usuario no tiene proyecto asignado, no hay nada que validar
        if not usuario.proyecto_nombre:
            logger.debug(f"Usuario {usuario.usuario} no tiene proyecto asignado. No se valida vencimiento.")
            return {
                "actualizado": False,
                "fecha_vencimiento": None,
                "mensaje": "Usuario sin proyecto asignado",
                "error": False
            }
        
        # Verificar si necesita validación
        ahora = datetime.utcnow()
        
        # Solo validar si:
        # 1. No tiene fecha de vencimiento (null)
        # 2. O la fecha de vencimiento es >= a hoy (está por vencer o vencida)
        if usuario.fecha_vencimiento and usuario.fecha_vencimiento < ahora:
            # La fecha ya venció y es menor a hoy, no validar
            logger.debug(f"Usuario {usuario.usuario} con fecha vencida. No se consulta API.")
            return {
                "actualizado": False,
                "fecha_vencimiento": usuario.fecha_vencimiento,
                "mensaje": "Fecha de vencimiento expirada",
                "error": False
            }
        
        # Necesita validación: consultar API de proyectos
        logger.info(f"[VALIDACIÓN INTERNA] Verificando vencimiento para {usuario.usuario} - Proyecto: {usuario.proyecto_nombre}")
        
        # Preparar request a la API de validación
        payload = {
            "email": usuario.mail,
            "password": password,
            "proyecto_nombre": usuario.proyecto_nombre
        }
        
        # Consultar API con timeout corto
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(VALIDATE_ENDPOINT, json=payload)
            response.raise_for_status()
            data = response.json()
        
        # Procesar respuesta
        if not data.get("valid", False):
            # Acceso denegado en la API
            mensaje = data.get("mensaje", "Acceso denegado")
            logger.warning(f"[VALIDACIÓN INTERNA] Usuario {usuario.usuario} denegado en API: {mensaje}")
            
            # No actualizar la fecha local si fue denegado
            return {
                "actualizado": False,
                "fecha_vencimiento": usuario.fecha_vencimiento,
                "mensaje": f"Validación API falló: {mensaje}",
                "error": True
            }
        
        # Acceso válido: obtener nueva fecha de vencimiento
        nueva_fecha_str = data.get("fecha_vencimiento")
        nueva_fecha = None
        
        if nueva_fecha_str:
            # Convertir de ISO string a datetime
            nueva_fecha = datetime.fromisoformat(nueva_fecha_str.replace('Z', '+00:00'))
            # Convertir a UTC naive (sin timezone)
            if nueva_fecha.tzinfo:
                nueva_fecha = nueva_fecha.replace(tzinfo=None)
        
        # Verificar si necesita actualización
        fecha_cambio = False
        if nueva_fecha != usuario.fecha_vencimiento:
            fecha_cambio = True
            logger.info(f"[VALIDACIÓN INTERNA] Actualizando fecha para {usuario.usuario}")
            logger.info(f"   Fecha anterior: {usuario.fecha_vencimiento}")
            logger.info(f"   Fecha nueva: {nueva_fecha}")
            
            # Actualizar fecha de vencimiento en el usuario
            usuario.fecha_vencimiento = nueva_fecha
            usuario.updated_at = datetime.utcnow()
            await usuario.save()
        else:
            logger.debug(f"[VALIDACIÓN INTERNA] Fecha de vencimiento sin cambios para {usuario.usuario}")
        
        return {
            "actualizado": fecha_cambio,
            "fecha_vencimiento": nueva_fecha,
            "mensaje": "Vencimiento verificado y actualizado" if fecha_cambio else "Vencimiento verificado",
            "error": False
        }
    
    except httpx.TimeoutException:
        logger.error(f"[VALIDACIÓN INTERNA] Timeout consultando API para {usuario.usuario}")
        return {
            "actualizado": False,
            "fecha_vencimiento": usuario.fecha_vencimiento,
            "mensaje": "Timeout consultando API de proyectos",
            "error": True
        }
    
    except httpx.HTTPStatusError as e:
        logger.error(f"[VALIDACIÓN INTERNA] Error HTTP consultando API: {e.response.status_code}")
        return {
            "actualizado": False,
            "fecha_vencimiento": usuario.fecha_vencimiento,
            "mensaje": f"Error consultando API: {e.response.status_code}",
            "error": True
        }
    
    except Exception as e:
        logger.error(f"[VALIDACIÓN INTERNA] Error verificando vencimiento: {str(e)}", exc_info=True)
        return {
            "actualizado": False,
            "fecha_vencimiento": usuario.fecha_vencimiento,
            "mensaje": f"Error interno: {str(e)}",
            "error": True
        }


async def validar_acceso_admin(usuario: AdminUsuarios) -> bool:
    """
    Valida si un usuario admin tiene acceso válido basándose en su fecha de vencimiento.
    
    Esta función NO consulta la API, solo verifica la fecha local.
    La actualización de la fecha se hace en verificar_y_actualizar_vencimiento.
    
    Args:
        usuario: Usuario admin a validar
        
    Returns:
        bool: True si tiene acceso válido, False si está vencido
    """
    # Si no tiene fecha de vencimiento, el acceso es permanente
    if not usuario.fecha_vencimiento:
        return True
    
    # Verificar si la fecha de vencimiento ya pasó
    ahora = datetime.utcnow()
    
    if ahora > usuario.fecha_vencimiento:
        logger.warning(f"[VALIDACIÓN] Acceso vencido para {usuario.usuario}. Vencimiento: {usuario.fecha_vencimiento}")
        return False
    
    logger.debug(f"[VALIDACIÓN] Acceso válido para {usuario.usuario}. Vence: {usuario.fecha_vencimiento}")
    return True
