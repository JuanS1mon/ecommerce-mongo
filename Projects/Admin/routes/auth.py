"""
Router de autenticación para el panel de administración
Maneja login, logout y verificación de credenciales admin
Migrado a MongoDB con Beanie
"""
from fastapi import APIRouter, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from datetime import timedelta
import logging
import httpx
import os
from dotenv import load_dotenv

load_dotenv()  # Cargar variables de entorno

from security.jwt_auth import (
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
from security.security import verificar_clave
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.utils.template_helpers import render_admin_template
from Projects.Admin.services.validacion_vencimiento import verificar_y_actualizar_vencimiento
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["Admin Auth"])


async def sincronizar_usuario_remoto(username_o_email: str) -> AdminUsuarios:
    """
    Sincroniza un usuario individual desde el servidor remoto.
    Busca el usuario por username o email.
    
    Args:
        username_o_email: Username o email del usuario a sincronizar
        
    Returns:
        Usuario sincronizado o None si no se pudo sincronizar
    """
    try:
        api_base_url = os.getenv("API_BASE_URL")
        proyecto_nombre = os.getenv("ADMIN_PROYECTO_NOMBRE", "Ecomerce")
        
        if not api_base_url:
            logger.warning(f"[SYNC USER] API_BASE_URL no configurado")
            return None
        
        # Consultar servidor remoto
        url = f"{api_base_url}/api/v1/proyecto/{proyecto_nombre}/usuarios"
        logger.info(f"[SYNC USER] Consultando: {url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.warning(f"[SYNC USER] Error al consultar servidor remoto: {response.status_code}")
                return None
            
            data = response.json()
            usuarios_remotos = data.get("usuarios", [])
            
            # Buscar usuario por username o email
            usuario_remoto = None
            for u in usuarios_remotos:
                if u["username"] == username_o_email or u["email"] == username_o_email:
                    usuario_remoto = u
                    break
            
            if not usuario_remoto:
                logger.warning(f"[SYNC USER] Usuario {username_o_email} no encontrado en servidor remoto")
                return None
            
            # Verificar si el proyecto existe, si no, crearlo
            from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto
            
            proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
            if not proyecto:
                logger.info(f"[SYNC USER] Creando proyecto: {proyecto_nombre}")
                proyecto = Proyecto(
                    nombre=proyecto_nombre,
                    descripcion=f"Proyecto {proyecto_nombre}",
                    activo=True
                )
                await proyecto.save()
            
            # Parsear fecha de vencimiento
            fecha_venc = None
            if usuario_remoto.get("fecha_vencimiento"):
                try:
                    fecha_str = usuario_remoto["fecha_vencimiento"].rstrip('Z')
                    fecha_venc = datetime.fromisoformat(fecha_str)
                    if fecha_venc.tzinfo is None:
                        fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
                except Exception as e:
                    logger.error(f"[SYNC USER] Error parseando fecha: {e}")
            
            # Crear usuario local
            nuevo_usuario = AdminUsuarios(
                mail=usuario_remoto["email"],
                usuario=usuario_remoto["username"],
                nombre=usuario_remoto.get("nombre", usuario_remoto["username"]),
                clave_hash=usuario_remoto["clave_hash"],
                activo=usuario_remoto["activo"],
                proyecto_nombre=proyecto_nombre,
                fecha_vencimiento=fecha_venc
            )
            
            await nuevo_usuario.save()
            logger.info(f"[SYNC USER] Usuario creado: {usuario_remoto['email']}")
            
            # Crear vinculación
            vinculacion = UsuarioProyecto(
                usuario_id=nuevo_usuario.id,
                proyecto_id=proyecto.id,
                fecha_vencimiento=fecha_venc,
                activo=usuario_remoto["activo"]
            )
            await vinculacion.save()
            logger.info(f"[SYNC USER] Vinculación creada para {usuario_remoto['email']}")
            
            return nuevo_usuario
            
    except Exception as e:
        logger.error(f"[SYNC USER] Error sincronizando usuario: {e}", exc_info=True)
        return None


async def sincronizar_password_remota(usuario: AdminUsuarios) -> bool:
    """
    Sincroniza la contraseña de un usuario desde el servidor remoto.
    
    Args:
        usuario: Usuario local a sincronizar
        
    Returns:
        True si se actualizó la contraseña, False si no
    """
    try:
        api_base_url = os.getenv("API_BASE_URL")
        proyecto_nombre = usuario.proyecto_nombre or os.getenv("ADMIN_PROYECTO_NOMBRE", "Ecomerce")
        
        if not api_base_url:
            logger.warning(f"[SYNC PASSWORD] API_BASE_URL no configurado, no se puede sincronizar")
            return False
        
        # Consultar servidor remoto
        url = f"{api_base_url}/api/v1/proyecto/{proyecto_nombre}/usuarios"
        logger.info(f"[SYNC PASSWORD] Consultando: {url}")
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
                logger.warning(f"[SYNC PASSWORD] Error al consultar servidor remoto: {response.status_code}")
                return False
            
            data = response.json()
            usuarios_remotos = data.get("usuarios", [])
            
            # Buscar usuario por email
            usuario_remoto = None
            for u in usuarios_remotos:
                if u["email"] == usuario.mail:
                    usuario_remoto = u
                    break
            
            if not usuario_remoto:
                logger.warning(f"[SYNC PASSWORD] Usuario {usuario.mail} no encontrado en servidor remoto")
                return False
            
            # Comparar hashes
            hash_remoto = usuario_remoto.get("clave_hash")
            
            if not hash_remoto:
                logger.warning(f"[SYNC PASSWORD] Hash remoto no disponible")
                return False
            
            # Verificar si hay cambios
            cambios = []
            
            if hash_remoto != usuario.clave_hash:
                cambios.append("contraseña")
                usuario.clave_hash = hash_remoto
            
            # Actualizar estado activo
            activo_remoto = usuario_remoto.get("activo", True)
            if activo_remoto != usuario.activo:
                cambios.append("estado activo")
                usuario.activo = activo_remoto
            
            # Actualizar fecha_vencimiento
            if usuario_remoto.get("fecha_vencimiento"):
                try:
                    fecha_str = usuario_remoto["fecha_vencimiento"].rstrip('Z')
                    fecha_venc = datetime.fromisoformat(fecha_str)
                    if fecha_venc.tzinfo is None:
                        fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
                    
                    if fecha_venc != usuario.fecha_vencimiento:
                        cambios.append("fecha_vencimiento")
                        usuario.fecha_vencimiento = fecha_venc
                except Exception as e:
                    logger.error(f"[SYNC PASSWORD] Error parseando fecha: {e}")
            
            if not cambios:
                logger.info(f"[SYNC PASSWORD] Usuario {usuario.mail} ya está sincronizado")
                return False
            
            # Guardar cambios
            logger.info(f"[SYNC PASSWORD] Actualizando: {', '.join(cambios)} para {usuario.mail}")
            await usuario.save()
            
            logger.info(f"[SYNC PASSWORD] ✅ Sincronización exitosa para {usuario.mail}")
            return True
            
    except Exception as e:
        logger.error(f"[SYNC PASSWORD] Error sincronizando contraseña: {e}", exc_info=True)
        return False


@router.get("/login", response_class=HTMLResponse, name="admin_login_page")
async def admin_login_page(request: Request, next: str = None):
    """
    Página de login del panel de administración
    
    Args:
        request: Request object
        next: URL a la que redirigir después del login exitoso
    """
    return render_admin_template("login.html", request, next=next or "/admin/dashboard")


@router.post("/api/login", name="admin_login_api")
async def admin_login_api(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/admin/dashboard")
):
    """
    API de login para administradores
    Verifica credenciales usando MongoDB con Beanie
    
    Args:
        username: Nombre de usuario
        password: Contraseña
        next: URL de redirección después del login
        
    Returns:
        JSONResponse con token y datos del usuario
    """
    try:
        # Obtener información del cliente
        client_ip = request.client.host if request.client else "unknown"
        
        # Buscar usuario en MongoDB (por username o por email)
        usuario = await AdminUsuarios.find_one(AdminUsuarios.usuario == username)
        
        if not usuario:
            # Intentar buscar por email
            usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == username)
        
        if not usuario:
            logger.warning(f"⚠️  Usuario no encontrado localmente: {username}, intentando sincronizar desde servidor remoto...")
            
            # Intentar sincronizar usuario desde servidor remoto
            usuario_sincronizado = await sincronizar_usuario_remoto(username)
            
            if usuario_sincronizado:
                usuario = usuario_sincronizado
                logger.info(f"✅ Usuario {username} sincronizado exitosamente desde servidor remoto")
            else:
                logger.warning(f"❌ Intento de login admin fallido - Usuario no existe: {username} desde {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
        
        # Verificar si está activo
        if not usuario.activo:
            logger.warning(f"⚠️  Usuario inactivo localmente: {username}, verificando estado en servidor remoto...")
            
            # Sincronizar datos desde servidor remoto para verificar si fue reactivado
            datos_sincronizados = await sincronizar_password_remota(usuario)
            
            if datos_sincronizados:
                # Recargar usuario para obtener estado actualizado
                usuario = await AdminUsuarios.get(usuario.id)
                logger.info(f"✅ Datos sincronizados desde servidor remoto para {username}")
                
                # Verificar nuevamente si está activo después de sincronizar
                if not usuario.activo:
                    logger.warning(f"❌ Usuario sigue inactivo después de sincronizar: {username} desde {client_ip}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Usuario inactivo"
                    )
                else:
                    logger.info(f"✅ Usuario {username} reactivado en servidor remoto")
            else:
                logger.warning(f"❌ No se pudo sincronizar estado del usuario: {username} desde {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario inactivo"
                )
        
        # Verificar si la fecha de vencimiento ha expirado
        # Si está vencido, desactivar automáticamente el usuario
        if usuario.fecha_vencimiento:
            ahora = datetime.now(timezone.utc)
            
            # Si la fecha_vencimiento no tiene timezone, agregarla
            fecha_venc = usuario.fecha_vencimiento
            if fecha_venc.tzinfo is None:
                fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
            
            if fecha_venc < ahora:
                logger.warning(f"⚠️  Usuario {username} con fecha de vencimiento expirada: {fecha_venc}")
                
                # Desactivar usuario automáticamente
                usuario.activo = False
                await usuario.save()
                
                logger.info(f"🔒 Usuario {username} desactivado automáticamente por vencimiento")
                
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Su acceso ha expirado el {fecha_venc.strftime('%d/%m/%Y')}"
                )
        
        # Verificar contraseña
        if not verificar_clave(password, usuario.clave_hash):
            logger.warning(f"⚠️  Contraseña incorrecta para {username}, verificando sincronización con servidor remoto...")
            
            # Intentar sincronizar contraseña y otros datos desde servidor remoto
            password_sincronizada = await sincronizar_password_remota(usuario)
            
            if password_sincronizada:
                # Reintentar verificación con el hash actualizado
                # Recargar usuario para obtener los datos actualizados
                usuario = await AdminUsuarios.get(usuario.id)
                
                # Verificar nuevamente si está activo (pudo haberse actualizado)
                if not usuario.activo:
                    logger.warning(f"❌ Usuario {username} desactivado en servidor remoto")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Usuario inactivo"
                    )
                
                # Verificar nuevamente fecha de vencimiento (pudo haberse actualizado)
                if usuario.fecha_vencimiento:
                    ahora = datetime.now(timezone.utc)
                    fecha_venc = usuario.fecha_vencimiento
                    if fecha_venc.tzinfo is None:
                        fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
                    
                    if fecha_venc < ahora:
                        logger.warning(f"⚠️  Usuario {username} con fecha de vencimiento expirada: {fecha_venc}")
                        usuario.activo = False
                        await usuario.save()
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Su acceso ha expirado el {fecha_venc.strftime('%d/%m/%Y')}"
                        )
                
                if verificar_clave(password, usuario.clave_hash):
                    logger.info(f"✅ Datos sincronizados exitosamente para {username}")
                else:
                    logger.warning(f"❌ Intento de login admin fallido - Contraseña incorrecta después de sincronización: {username} desde {client_ip}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Credenciales inválidas"
                    )
            else:
                logger.warning(f"❌ Intento de login admin fallido - Contraseña incorrecta: {username} desde {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
        else:
            # Contraseña correcta, sincronizar otros datos (activo, fecha_vencimiento)
            logger.info(f"✅ Contraseña correcta para {username}, verificando sincronización de datos...")
            await sincronizar_password_remota(usuario)
            # Recargar usuario para obtener datos actualizados
            usuario = await AdminUsuarios.get(usuario.id)
            
            # Verificar si se desactivó durante la sincronización
            if not usuario.activo:
                logger.warning(f"❌ Usuario {username} desactivado en servidor remoto")
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario inactivo"
                )
            
            # Verificar fecha de vencimiento actualizada
            if usuario.fecha_vencimiento:
                ahora = datetime.now(timezone.utc)
                fecha_venc = usuario.fecha_vencimiento
                if fecha_venc.tzinfo is None:
                    fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
                
                if fecha_venc < ahora:
                    logger.warning(f"⚠️  Usuario {username} con fecha de vencimiento expirada: {fecha_venc}")
                    usuario.activo = False
                    await usuario.save()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Su acceso ha expirado el {fecha_venc.strftime('%d/%m/%Y')}"
                    )
        
        # Verificar y actualizar fecha de vencimiento si es necesario
        # Solo se ejecuta si la fecha es null o >= a hoy
        if usuario.proyecto_nombre:
            resultado_validacion = await verificar_y_actualizar_vencimiento(usuario, password)
            
            if resultado_validacion["error"]:
                logger.warning(f"⚠️  Error validando vencimiento para {username}: {resultado_validacion['mensaje']}")
                # No bloquear el login por error de API, continuar con la fecha local
            elif resultado_validacion["actualizado"]:
                logger.info(f"✅ Fecha de vencimiento actualizada para {username}: {resultado_validacion['fecha_vencimiento']}")
        
        # Crear token JWT
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": usuario.usuario, "user_id": str(usuario.id)},
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Login admin exitoso: {username} desde {client_ip}")
        
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={
                "success": True,
                "message": "Login exitoso",
                "access_token": access_token,
                "token_type": "bearer",
                "redirect_url": next,
                "user": {
                    "id": str(usuario.id),
                    "username": usuario.usuario,
                    "nombre": usuario.nombre,
                    "email": usuario.mail
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en login admin: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )


@router.post("/logout", name="admin_logout")
async def admin_logout(request: Request):
    """
    Logout del panel de administración
    El cliente debe eliminar el token
    """
    logger.info("Admin logout")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "success": True,
            "message": "Logout exitoso",
            "redirect_url": "/admin/login"
        }
    )
