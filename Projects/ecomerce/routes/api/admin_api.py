"""
API endpoints para el panel de administración
Proporciona datos JSON para el dashboard de admin
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query

from db.models.config.usuarios import Usuarios
from security.jwt_auth import get_current_user
from security.auth_middleware import require_role_api
from db.schemas.config.Usuarios import UserDB

router = APIRouter(
    prefix="/api/admin",
    tags=["Admin API"],
    dependencies=[Depends(require_role_api(["admin"]))]
)

@router.get("/metrics")
async def get_admin_metrics(
    current_user: UserDB = Depends(get_current_user),
):
    """Obtiene métricas generales del sistema para el dashboard"""
    try:
        # Contar usuarios totales
        total_users = db.query(Usuarios).count()
        
        # Contar usuarios activos
        active_users = db.query(Usuarios).filter(Usuarios.activo == True).count()
        
        # Contar actividades (simulado ya que no tenemos tabla activity_log)
        total_activities = 25  # Valor simulado
        
        # Estado del sistema (simulado)
        system_status = "Activo"
        
        return {
            "total_users": total_users,
            "active_users": active_users,
            "inactive_users": total_users - active_users,
            "total_activities": total_activities,
            "system_status": system_status,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo métricas: {str(e)}")

@router.get("/activities")
async def get_admin_activities(
    type_filter: Optional[str] = Query(None, alias="type"),
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0),
    current_user: UserDB = Depends(get_current_user),
):
    """Obtiene actividades del sistema con paginación y filtros"""
    try:
        # Generar actividades simuladas ya que no tenemos tabla activity_log
        all_simulated_activities = []
        
        # Crear una lista de actividades simuladas
        action_types = ["login", "logout", "create", "update", "delete", "system", "migration"]
        
        for i in range(50):  # Simular 50 actividades en total
            activity = {
                "id": i + 1,
                "action": action_types[i % len(action_types)],
                "timestamp": (datetime.now() - timedelta(hours=i, minutes=i*5)).isoformat(),
                "user_id": (i % 3) + 1,  # Rotar entre usuarios 1, 2, 3
                "details": f"Actividad simulada #{i + 1}"
            }
            all_simulated_activities.append(activity)
        
        # Aplicar filtro por tipo si se especifica
        if type_filter:
            filtered_activities = [
                a for a in all_simulated_activities 
                if type_filter.lower() in a["action"].lower()
            ]
        else:
            filtered_activities = all_simulated_activities
        
        # Aplicar paginación
        start_idx = offset
        end_idx = offset + limit
        activities = filtered_activities[start_idx:end_idx]
        
        # Determinar si hay más páginas
        has_more = end_idx < len(filtered_activities)
        
        return {
            "activities": activities,
            "total": len(activities),
            "has_more": has_more,
            "offset": offset,
            "limit": limit
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo actividades: {str(e)}")

@router.get("/users")
async def get_admin_users(
    limit: int = Query(10, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    current_user: UserDB = Depends(get_current_user),
):
    """Obtiene lista de usuarios con paginación y búsqueda"""
    try:
        query = db.query(Usuarios)
        
        if search:
            query = query.filter(
                Usuarios.usuario.ilike(f"%{search}%") |
                Usuarios.nombre.ilike(f"%{search}%") |
                Usuarios.mail.ilike(f"%{search}%")
            )
        
        total = query.count()
        users = query.offset(offset).limit(limit).all()
        
        return {
            "users": [
                {
                    "codigo": user.codigo,
                    "usuario": user.usuario,
                    "nombre": user.nombre,
                    "mail": user.mail,
                    "activo": user.activo,
                    "fecha_creacion": user.fecha_creacion.isoformat() if user.fecha_creacion else None,
                    "ultimo_acceso": user.ultimo_acceso.isoformat() if user.ultimo_acceso else None
                }
                for user in users
            ],
            "total": total,
            "offset": offset,
            "limit": limit,
            "has_more": offset + limit < total
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo usuarios: {str(e)}")

@router.get("/system-health")
async def get_system_health(
    current_user: UserDB = Depends(get_current_user),
):
    """Obtiene estado de salud del sistema"""
    try:
        # Verificar conexión a base de datos
        db_status = "ok"
        try:
        except Exception:
            db_status = "error"
        
        # Verificar otros componentes (simulado)
        components = {
            "database": db_status,
            "cache": "ok",
            "storage": "ok",
            "api": "ok"
        }
        
        overall_status = "healthy" if all(status == "ok" for status in components.values()) else "degraded"
        
        return {
            "status": overall_status,
            "components": components,
            "timestamp": datetime.now().isoformat(),
            "uptime": "99.9%"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo estado del sistema: {str(e)}")

@router.get("/dashboard-summary")
async def get_dashboard_summary(
    current_user: UserDB = Depends(get_current_user),
):
    """Obtiene un resumen completo para el dashboard"""
    try:
        # Obtener métricas
        metrics_response = await get_admin_metrics(current_user, db)
        
        # Obtener actividades recientes
        activities_response = await get_admin_activities(None, 5, 0, current_user, db)
        
        # Obtener estado del sistema
        health_response = await get_system_health(current_user, db)
        
        return {
            "metrics": metrics_response,
            "recent_activities": activities_response["activities"],
            "system_health": health_response,
            "last_updated": datetime.now().isoformat()
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error obteniendo resumen del dashboard: {str(e)}")
