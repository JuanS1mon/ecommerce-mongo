# routers/admin_contrato.py
from fastapi import APIRouter, HTTPException, Depends
from models.models_beanie import Contrato, Servicio, Usuario, Producto
from security.jwt_auth import require_admin
from pydantic import BaseModel
from typing import List
from datetime import datetime, timedelta

router = APIRouter()

class ContratoUpdate(BaseModel):
    estado: str  # pendiente, aprobado, activo, cancelado, suspendido, expirado
    detalles: str = ""

    # Validar transiciones de estado - más flexible para administradores
    def validate_transition(self, current_estado: str):
        # Para administradores, permitir cualquier transición excepto desde expirado
        if current_estado == "expirado":
            # Solo permitir cancelado desde expirado (por si acaso)
            if self.estado not in ["cancelado"]:
                raise ValueError(f"No se puede cambiar el estado de un contrato expirado")
        # Para otros estados, permitir cualquier cambio válido
        valid_states = ["pendiente", "aprobado", "activo", "cancelado", "suspendido", "expirado"]
        if self.estado not in valid_states:
            raise ValueError(f"Estado inválido: {self.estado}")

@router.get("/admin/contratos", response_model=List[dict])
async def listar_contratos_admin(current_user: dict = Depends(require_admin)):
    from beanie import PydanticObjectId
    
    contratos = await Contrato.find().to_list()
    
    # Convertir contratos a diccionarios con información adicional
    contratos_dict = []
    for contrato in contratos:
        contrato_dict = contrato.model_dump()
        contrato_dict['id'] = str(contrato.id)
        
        # Obtener información del usuario
        usuario_nombre = f"Usuario {contrato.usuario_id[:8]}..."
        usuario_email = "N/A"
        try:
            # Intentar convertir a ObjectId si es necesario
            usuario_id = contrato.usuario_id
            if isinstance(usuario_id, str) and len(usuario_id) == 24:
                usuario_id = PydanticObjectId(usuario_id)
            usuario = await Usuario.get(usuario_id)
            if usuario:
                usuario_nombre = usuario.username
                usuario_email = usuario.email
        except Exception as e:
            print(f"Error obteniendo usuario {contrato.usuario_id}: {e}")
        
        contrato_dict['usuario_nombre'] = usuario_nombre
        contrato_dict['usuario_email'] = usuario_email
        
        # Obtener información del servicio/producto
        servicio_info = "N/A"
        if contrato.servicio_id:
            try:
                # Intentar convertir a ObjectId si es necesario
                servicio_id = contrato.servicio_id
                if isinstance(servicio_id, str) and len(servicio_id) == 24:
                    servicio_id = PydanticObjectId(servicio_id)
                
                # Buscar primero en servicios
                servicio = await Servicio.get(servicio_id)
                if servicio:
                    servicio_info = servicio.nombre
                else:
                    # Buscar en productos
                    producto = await Producto.get(servicio_id)
                    if producto:
                        servicio_info = producto.nombre
            except Exception as e:
                print(f"Error obteniendo servicio {contrato.servicio_id}: {e}")
                servicio_info = f"Servicio {contrato.servicio_id[:8]}..."
        
        contrato_dict['servicio_nombre'] = servicio_info
        
        contratos_dict.append(contrato_dict)
    
    return contratos_dict

@router.get("/admin/contratos/{contrato_id}", response_model=dict)
async def obtener_contrato_admin(contrato_id: str, current_user: dict = Depends(require_admin)):
    contrato = await Contrato.get(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    # Convertir a diccionario asegurando que el id esté incluido
    contrato_dict = contrato.model_dump()
    contrato_dict['id'] = str(contrato.id)
    return contrato_dict

@router.put("/admin/contratos/{contrato_id}")
async def actualizar_contrato_admin(contrato_id: str, update: ContratoUpdate, current_user: dict = Depends(require_admin)):
    contrato = await Contrato.get(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    # Validar transición de estado
    try:
        update.validate_transition(contrato.estado)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    old_estado = contrato.estado
    contrato.estado = update.estado
    contrato.detalles = update.detalles
    
    # Lógica específica por estado
    if update.estado == "activo" and not contrato.fecha_fin:
        contrato.fecha_fin = datetime.utcnow() + timedelta(days=contrato.duracion_meses * 30)
    elif update.estado == "expirado":
        contrato.fecha_fin = datetime.utcnow()  # Marcar como expirado ahora
    
    await contrato.save()
    
    # Notificaciones por email según el estado
    servicio = await Servicio.get(contrato.servicio_id) if contrato.servicio_id else None
    
    if update.estado == "aprobado" and old_estado == "pendiente":
        # Email de aprobación
        pass  # Agregar lógica de email similar a la de activación
    elif update.estado == "activo" and old_estado == "aprobado":
        # Email de activación (ya existente)
        try:
            from Services.mail.mail import enviar_correo
            from Projects.ecomerce.models.usuarios import EcomerceUsuarios
            user = await EcomerceUsuarios.find_one(EcomerceUsuarios.id == contrato.usuario_id)
            user_email = user.email if user else None
            if user_email and servicio:
                subject = f"Contrato de {servicio.nombre} activado"
                message = f"""
¡Felicitaciones!

Tu contrato para el servicio "{servicio.nombre}" ha sido activado.

Detalles del contrato:
- Servicio: {servicio.nombre}
- Precio mensual: ${contrato.precio_mensual or 0}
- Duración: {contrato.duracion_meses} meses
- Fecha de activación: {datetime.utcnow().strftime('%Y-%m-%d')}
- Fecha de expiración: {contrato.fecha_fin.strftime('%Y-%m-%d') if contrato.fecha_fin else 'N/A'}

El servicio ya está disponible para su uso.

Atentamente,
Equipo de Servicios Profesionales
"""
                enviar_correo(user_email, subject, message)
        except Exception as e:
            print(f"Error sending activation email: {e}")
    elif update.estado == "suspendido":
        # Email de suspensión
        pass  # Agregar lógica
    elif update.estado == "expirado":
        # Email de expiración
        pass  # Agregar lógica
    
    return {"message": "Contrato actualizado exitosamente"}

@router.delete("/admin/contratos/{contrato_id}")
async def eliminar_contrato_admin(contrato_id: str, current_user: dict = Depends(require_admin)):
    contrato = await Contrato.get(contrato_id)
    if not contrato:
        raise HTTPException(status_code=404, detail="Contrato no encontrado")
    
    await contrato.delete()
    return {"message": "Contrato eliminado exitosamente"}

@router.get("/admin/analytics")
async def get_analytics(current_user: dict = Depends(require_admin)):
    from models.models_beanie import Usuario, AdminUsuarios
    
    # Cantidad de usuarios registrados
    total_usuarios = await Usuario.count()
    
    # Cantidad de contratos
    total_contratos = await Contrato.count()
    
    # Contratos por vencer (próximos 30 días)
    now = datetime.utcnow()
    future = now + timedelta(days=30)
    contratos_por_vencer = await Contrato.find(
        Contrato.estado == "activo",
        Contrato.fecha_fin >= now,
        Contrato.fecha_fin <= future
    ).count()
    
    return {
        "total_usuarios": total_usuarios,
        "total_contratos": total_contratos,
        "contratos_por_vencer": contratos_por_vencer
    }