"""
Servicio de Sincronización de Usuarios Admin entre Aplicaciones
=================================================================

Este módulo maneja la sincronización de usuarios administradores entre
el sistema de gestión de proyectos y la aplicación de ecommerce.

Funcionalidades:
- Obtener usuarios desde la API del proyecto
- Comparar usuarios locales vs remotos
- Crear usuarios faltantes con contraseñas ya hasheadas
- Actualizar datos de usuarios existentes
- Desactivar usuarios vencidos
"""

import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional
import httpx
import os
from dotenv import load_dotenv
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto

load_dotenv()
logger = logging.getLogger(__name__)


class SincronizadorUsuarios:
    """Servicio para sincronizar usuarios admin entre aplicaciones."""
    
    def __init__(self, api_base_url: Optional[str] = None, proyecto_nombre: Optional[str] = None):
        """
        Inicializa el sincronizador.
        
        Args:
            api_base_url: URL base de la API del proyecto (ej: http://localhost:8000)
            proyecto_nombre: Nombre del proyecto a sincronizar (ej: Ecomerce)
        """
        self.api_base_url = api_base_url or os.getenv("API_BASE_URL")
        self.proyecto_nombre = proyecto_nombre or os.getenv("ADMIN_PROYECTO_NOMBRE")
        
        if not self.api_base_url:
            raise ValueError("API_BASE_URL no configurado")
        if not self.proyecto_nombre:
            raise ValueError("ADMIN_PROYECTO_NOMBRE no configurado")
    
    async def obtener_usuarios_remotos(self) -> List[Dict]:
        """
        Obtiene la lista de usuarios del proyecto desde la API remota.
        
        Returns:
            Lista de diccionarios con datos de usuarios
            
        Raises:
            httpx.HTTPError: Si hay error en la petición HTTP
        """
        url = f"{self.api_base_url}/api/v1/proyecto/{self.proyecto_nombre}/usuarios"
        
        logger.info(f"[SYNC] Consultando usuarios remotos: {url}")
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            
            data = response.json()
            usuarios = data.get("usuarios", [])
            
            logger.info(f"[SYNC] Obtenidos {len(usuarios)} usuarios remotos")
            return usuarios
    
    async def obtener_usuarios_locales(self) -> List[AdminUsuarios]:
        """
        Obtiene todos los usuarios admin locales del proyecto.
        
        Returns:
            Lista de documentos AdminUsuarios
        """
        usuarios = await AdminUsuarios.find(
            AdminUsuarios.proyecto_nombre == self.proyecto_nombre
        ).to_list()
        
        logger.info(f"[SYNC] Encontrados {len(usuarios)} usuarios locales")
        return usuarios
    
    async def sincronizar_usuarios(self, dry_run: bool = False) -> Dict:
        """
        Sincroniza usuarios entre la aplicación remota y local.
        
        Proceso:
        1. Obtiene usuarios remotos desde la API
        2. Obtiene usuarios locales de la BD
        3. Crea usuarios faltantes
        4. Actualiza usuarios existentes
        5. Desactiva usuarios vencidos
        
        Args:
            dry_run: Si es True, solo simula sin hacer cambios
            
        Returns:
            Diccionario con estadísticas de la sincronización
        """
        logger.info(f"[SYNC] Iniciando sincronización {'(DRY RUN)' if dry_run else ''}")
        
        estadisticas = {
            "usuarios_remotos": 0,
            "usuarios_locales": 0,
            "usuarios_creados": 0,
            "usuarios_actualizados": 0,
            "usuarios_desactivados": 0,
            "errores": []
        }
        
        try:
            # 1. Obtener usuarios remotos
            usuarios_remotos = await self.obtener_usuarios_remotos()
            estadisticas["usuarios_remotos"] = len(usuarios_remotos)
            
            # 2. Obtener usuarios locales
            usuarios_locales = await self.obtener_usuarios_locales()
            estadisticas["usuarios_locales"] = len(usuarios_locales)
            
            # Crear mapa de usuarios locales por email
            usuarios_locales_map = {u.mail: u for u in usuarios_locales}
            
            # 3. Procesar cada usuario remoto
            for usuario_remoto in usuarios_remotos:
                email = usuario_remoto["email"]
                
                try:
                    # Verificar si existe localmente
                    usuario_local = usuarios_locales_map.get(email)
                    
                    if not usuario_local:
                        # CREAR nuevo usuario
                        await self._crear_usuario(usuario_remoto, estadisticas, dry_run)
                    else:
                        # ACTUALIZAR usuario existente
                        await self._actualizar_usuario(usuario_local, usuario_remoto, estadisticas, dry_run)
                    
                except Exception as e:
                    error_msg = f"Error procesando usuario {email}: {str(e)}"
                    logger.error(f"[SYNC] {error_msg}", exc_info=True)
                    estadisticas["errores"].append(error_msg)
            
            logger.info(f"[SYNC] Sincronización completada: {estadisticas}")
            
        except Exception as e:
            error_msg = f"Error en sincronización: {str(e)}"
            logger.error(f"[SYNC] {error_msg}", exc_info=True)
            estadisticas["errores"].append(error_msg)
        
        return estadisticas
    
    async def _crear_usuario(self, usuario_remoto: Dict, estadisticas: Dict, dry_run: bool):
        """
        Crea un nuevo usuario local desde datos remotos Y su vinculación al proyecto.
        
        Args:
            usuario_remoto: Datos del usuario desde la API
            estadisticas: Diccionario para actualizar estadísticas
            dry_run: Si es True, solo simula sin crear
        """
        email = usuario_remoto["email"]
        
        logger.info(f"[SYNC] Creando usuario: {email}")
        
        if dry_run:
            logger.info(f"[SYNC] DRY RUN - No se crea usuario {email}")
            estadisticas["usuarios_creados"] += 1
            return
        
        # Crear usuario con la contraseña ya hasheada desde el sistema remoto
        nuevo_usuario = AdminUsuarios(
            mail=usuario_remoto["email"],
            usuario=usuario_remoto["username"],
            nombre=usuario_remoto.get("nombre", usuario_remoto["username"]),
            clave_hash=usuario_remoto["clave_hash"],  # Hash directamente desde remoto
            activo=usuario_remoto["activo"],
            proyecto_nombre=self.proyecto_nombre,
            fecha_vencimiento=self._parse_fecha(usuario_remoto.get("fecha_vencimiento"))
        )
        
        await nuevo_usuario.save()
        logger.info(f"[SYNC] Usuario creado: {email}")
        
        # Crear vinculación con el proyecto
        await self._crear_vinculacion(nuevo_usuario, usuario_remoto)
        
        estadisticas["usuarios_creados"] += 1
    
    async def _actualizar_usuario(
        self, 
        usuario_local: AdminUsuarios, 
        usuario_remoto: Dict, 
        estadisticas: Dict, 
        dry_run: bool
    ):
        """
        Actualiza un usuario local con datos remotos.
        
        Args:
            usuario_local: Documento AdminUsuarios local
            usuario_remoto: Datos del usuario desde la API
            estadisticas: Diccionario para actualizar estadísticas
            dry_run: Si es True, solo simula sin actualizar
        """
        email = usuario_remoto["email"]
        cambios = []
        
        # Verificar qué campos cambiaron
        if usuario_local.usuario != usuario_remoto["username"]:
            cambios.append(f"usuario: {usuario_local.usuario} -> {usuario_remoto['username']}")
            usuario_local.usuario = usuario_remoto["username"]
        
        if usuario_local.nombre != usuario_remoto.get("nombre"):
            cambios.append(f"nombre: {usuario_local.nombre} -> {usuario_remoto.get('nombre')}")
            usuario_local.nombre = usuario_remoto.get("nombre", usuario_remoto["username"])
        
        if usuario_local.clave_hash != usuario_remoto["clave_hash"]:
            cambios.append("contraseña actualizada")
            usuario_local.clave_hash = usuario_remoto["clave_hash"]
        
        fecha_remota = self._parse_fecha(usuario_remoto.get("fecha_vencimiento"))
        if usuario_local.fecha_vencimiento != fecha_remota:
            cambios.append(f"fecha_vencimiento: {usuario_local.fecha_vencimiento} -> {fecha_remota}")
            usuario_local.fecha_vencimiento = fecha_remota
        
        # Verificar si está vencido
        if fecha_remota and fecha_remota < datetime.now(timezone.utc):
            if usuario_local.activo:
                cambios.append("desactivado por vencimiento")
                usuario_local.activo = False
                estadisticas["usuarios_desactivados"] += 1
        elif usuario_local.activo != usuario_remoto["activo"]:
            cambios.append(f"activo: {usuario_local.activo} -> {usuario_remoto['activo']}")
            usuario_local.activo = usuario_remoto["activo"]
        
        # Guardar si hay cambios
        if cambios:
            logger.info(f"[SYNC] Actualizando usuario {email}: {', '.join(cambios)}")
            
            if not dry_run:
                await usuario_local.save()
            
            estadisticas["usuarios_actualizados"] += 1
    
    def _parse_fecha(self, fecha_str: Optional[str]) -> Optional[datetime]:
        """
        Convierte string de fecha a datetime UTC.
        
        Args:
            fecha_str: String con fecha en formato ISO
            
        Returns:
            datetime object o None
        """
        if not fecha_str:
            return None
        
        try:
            # Quitar la Z final si existe
            fecha_str = fecha_str.rstrip('Z')
            dt = datetime.fromisoformat(fecha_str)
            
            # Asegurar que tenga timezone
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            return dt
        except Exception as e:
            logger.error(f"[SYNC] Error parseando fecha {fecha_str}: {e}")
            return None
    
    async def _crear_vinculacion(self, usuario: AdminUsuarios, usuario_remoto: Dict):
        """
        Crea una vinculación entre usuario y proyecto.
        
        Args:
            usuario: Documento AdminUsuarios
            usuario_remoto: Datos del usuario remoto con fecha_vencimiento
        """
        try:
            # Buscar proyecto
            proyecto = await Proyecto.find_one(Proyecto.nombre == self.proyecto_nombre)
            
            if not proyecto:
                logger.warning(f"[SYNC] Proyecto '{self.proyecto_nombre}' no encontrado, creándolo...")
                proyecto = Proyecto(
                    nombre=self.proyecto_nombre,
                    descripcion=f"Proyecto {self.proyecto_nombre}",
                    activo=True
                )
                await proyecto.save()
                logger.info(f"[SYNC] Proyecto creado: {self.proyecto_nombre}")
            
            # Verificar si ya existe vinculación
            vinculacion_existente = await UsuarioProyecto.find_one(
                UsuarioProyecto.usuario_id == usuario.id,
                UsuarioProyecto.proyecto_id == proyecto.id
            )
            
            if vinculacion_existente:
                logger.info(f"[SYNC] Vinculación ya existe para {usuario.mail}")
                return
            
            # Crear nueva vinculación
            vinculacion = UsuarioProyecto(
                usuario_id=usuario.id,
                proyecto_id=proyecto.id,
                fecha_vencimiento=self._parse_fecha(usuario_remoto.get("fecha_vencimiento")),
                activo=usuario_remoto["activo"]
            )
            
            await vinculacion.save()
            logger.info(f"[SYNC] Vinculación creada para {usuario.mail} -> {self.proyecto_nombre}")
            
        except Exception as e:
            logger.error(f"[SYNC] Error creando vinculación para {usuario.mail}: {e}", exc_info=True)


async def sincronizar_usuarios_admin(dry_run: bool = False) -> Dict:
    """
    Función de conveniencia para ejecutar sincronización.
    
    Args:
        dry_run: Si es True, solo simula sin hacer cambios
        
    Returns:
        Diccionario con estadísticas de la sincronización
    """
    sincronizador = SincronizadorUsuarios()
    return await sincronizador.sincronizar_usuarios(dry_run=dry_run)
