# Sistema de Sincronización de Usuarios Admin entre Aplicaciones

Este documento describe el sistema completo de sincronización de usuarios administradores entre dos aplicaciones FastAPI con MongoDB.

## 📋 Tabla de Contenidos
- [Arquitectura](#arquitectura)
- [Modelo de Datos](#modelo-de-datos)
- [Rutas del Servidor Fuente](#rutas-del-servidor-fuente)
- [Rutas del Servidor Destino](#rutas-del-servidor-destino)
- [Servicio de Sincronización](#servicio-de-sincronización)
- [Flujo de Sincronización Automática](#flujo-de-sincronización-automática)
- [Configuración](#configuración)
- [Implementación Paso a Paso](#implementación-paso-a-paso)

---

## 🏗️ Arquitectura

### Servidores
- **Servidor Fuente (Puerto 8000)**: Sistema de gn de proyectos que contiene la base de datos maestra de usuarios admin
- **Servidor Destino (Puerto 8001)**: Aplicación de ecommerce que sincroniza usuarios desde el servidor fuente

### Base de Datos
- MongoDB con Beanie ODM (async)
- Base de datos: `db_ecomerce`

### Colecciones
```
admin_usuarios         # Usuarios administradores
proyectos              # Proyectos del sistema
usuario_proyectos      # Vinculaciones usuario-proyecto con vencimiento
```

---

## 📊 Modelo de Datos

### 1. AdminUsuarios (admin_usuarios)

```python
"""
Modelo de Usuarios Administradores para el Panel Admin
Colección: admin_usuarios
"""
from beanie import Document
from pydantic import Field, EmailStr
from typing import Optional
from datetime import datetime


class AdminUsuarios(Document):
    """
    Modelo de usuarios administradores del sistema
    """
    # Campos principales
    usuario: str = Field(..., description="Username único del administrador")
    nombre: str = Field(..., description="Nombre completo del administrador")
    mail: EmailStr = Field(..., description="Email del administrador")
    clave_hash: str = Field(..., description="Contraseña hasheada con bcrypt")
    activo: bool = Field(default=True, description="Estado activo/inactivo")
    imagen_perfil: Optional[str] = Field(default=None, description="URL de imagen de perfil")
    
    # Sistema de proyectos con vencimiento
    proyecto_nombre: Optional[str] = Field(default="Ecomerce", description="Nombre del proyecto asignado")
    fecha_vencimiento: Optional[datetime] = Field(default=None, description="Fecha de vencimiento del acceso (null = sin vencimiento)")
    
    # Auditoría
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "admin_usuarios"
```

**Campos Clave:**
- `usuario`: Username único para login
- `mail`: Email único para login alternativo
- `clave_hash`: Hash bcrypt de la contraseña (NUNCA plain text)
- `activo`: Boolean que controla si el usuario puede acceder
- `fecha_vencimiento`: Fecha límite de acceso (null = sin límite)
- `proyecto_nombre`: Proyecto al que pertenece

---

### 2. Proyecto (proyectos)

```python
from beanie import Document, PydanticObjectId
from pydantic import Field
from typing import Optional
from datetime import datetime


class Proyecto(Document):
    """
    Modelo de proyectos del sistema
    """
    nombre: str = Field(..., description="Nombre único del proyecto")
    descripcion: Optional[str] = Field(default=None)
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "proyectos"
```

---

### 3. UsuarioProyecto (usuario_proyectos)

```python
from beanie import Document, PydanticObjectId
from pydantic import Field
from typing import Optional
from datetime import datetime


class UsuarioProyecto(Document):
    """
    Vinculación entre usuarios y proyectos con fecha de vencimiento
    """
    usuario_id: PydanticObjectId = Field(..., description="ID del usuario")
    proyecto_id: PydanticObjectId = Field(..., description="ID del proyecto")
    fecha_vencimiento: Optional[datetime] = Field(default=None)
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "usuario_proyectos"
```

---

## 🔌 Rutas del Servidor Fuente (Puerto 8000)

### Endpoint: Listar Usuarios por Proyecto

**Archivo**: `Projects/Admin/routes/validacion_externa.py`

```python
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from datetime import datetime

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto

router = APIRouter(prefix="/api/v1", tags=["Validación Externa"])


@router.get(
    "/proyecto/{proyecto_nombre}/usuarios",
    summary="Listar usuarios admin de un proyecto"
)
async def listar_usuarios_proyecto(proyecto_nombre: str, request: Request):
    """
    Lista todos los usuarios administradores vinculados a un proyecto.
    
    Args:
        proyecto_nombre: Nombre del proyecto (ej: "Ecomerce")
        
    Returns:
        JSON con lista de usuarios y sus datos
    """
    try:
        # Buscar proyecto
        proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
        
        if not proyecto:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "Proyecto no encontrado",
                    "proyecto": proyecto_nombre
                }
            )
        
        # Buscar vinculaciones del proyecto
        vinculaciones = await UsuarioProyecto.find(
            UsuarioProyecto.proyecto_id == proyecto.id
        ).to_list()
        
        # Obtener datos de cada usuario
        usuarios_data = []
        
        for vinc in vinculaciones:
            usuario = await AdminUsuarios.get(vinc.usuario_id)
            
            if usuario:
                # Formato de fecha ISO para compatibilidad
                fecha_venc = None
                if vinc.fecha_vencimiento:
                    fecha_venc = vinc.fecha_vencimiento.isoformat()
                
                usuarios_data.append({
                    "email": usuario.mail,
                    "username": usuario.usuario,
                    "nombre": usuario.nombre,
                    "activo": vinc.activo and usuario.activo,
                    "fecha_vencimiento": fecha_venc,
                    "clave_hash": usuario.clave_hash  # Hash completo para sincronización
                })
        
        return JSONResponse(
            status_code=200,
            content={
                "proyecto": proyecto_nombre,
                "usuarios": usuarios_data,
                "total": len(usuarios_data)
            }
        )
        
    except Exception as e:
        logger.error(f"Error listando usuarios: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"error": "Error interno del servidor"}
        )
```

**Respuesta Ejemplo:**

```json
{
  "proyecto": "Ecomerce",
  "usuarios": [
    {
      "email": "admin@sysneg.com",
      "username": "admin",
      "nombre": "Administrador Principal",
      "activo": true,
      "fecha_vencimiento": "2026-07-03T00:00:00Z",
      "clave_hash": "$2b$12$JujECruz/Ag07y27CWvDOezYtu.b174XNup3xb1TrsCBgwy1JkajW"
    },
    {
      "email": "fjuansimon@gmail.com",
      "username": "juansimon",
      "nombre": "Juan Simon",
      "activo": true,
      "fecha_vencimiento": "2026-08-15T00:00:00Z",
      "clave_hash": "$2b$12$..."
    }
  ],
  "total": 2
}
```

---

## ✅ Endpoint de Validación de Acceso (Ambos Servidores)

### Endpoint: Validar Acceso de Usuario a Proyecto

**Archivo**: `Projects/Admin/routes/validacion_externa.py`

Este endpoint realiza una validación completa de:
- Credenciales del usuario (email + password)
- Asignación al proyecto
- Estado activo del usuario, proyecto y vinculación
- Fecha de vencimiento

#### Schemas Pydantic

**Archivo**: `Projects/Admin/schemas/validacion_externa.py`

```python
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime


class ValidateRequest(BaseModel):
    """Schema para la solicitud de validación de acceso"""
    email: EmailStr = Field(..., description="Email del usuario registrado")
    password: str = Field(..., description="Contraseña del usuario")
    proyecto_nombre: str = Field(..., description="Nombre exacto del proyecto (case-sensitive)")


class DatosUsuario(BaseModel):
    """Datos básicos del usuario para incluir en la respuesta"""
    email: str = Field(..., description="Email del usuario")
    username: str = Field(..., description="Nombre de usuario")


class ValidateResponse(BaseModel):
    """Schema para la respuesta de validación de acceso"""
    valid: bool = Field(..., description="true si el acceso es válido, false si no")
    mensaje: str = Field(..., description="Descripción del resultado de la validación")
    datos_usuario: Optional[DatosUsuario] = Field(None, description="Datos del usuario (solo si valid=true)")
    fecha_vencimiento: Optional[datetime] = Field(None, description="Fecha de vencimiento del acceso")
```

#### Implementación del Endpoint

```python
@router.post("/api/v1/validate", response_model=ValidateResponse)
async def validate_user_project_access(request_data: ValidateRequest, request: Request):
    """
    Valida el acceso de un usuario a un proyecto específico.
    
    Validaciones en orden:
    1. Usuario existe por email
    2. Contraseña correcta (bcrypt)
    3. Usuario activo
    4. Proyecto existe
    5. Proyecto activo
    6. Vinculación existe
    7. Vinculación activa
    8. Fecha de vencimiento no expirada
    
    Returns:
        ValidateResponse con valid=True/False y mensaje descriptivo
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        logger.info(f"[VALIDACIÓN] Intento desde {client_ip} - {request_data.email} - {request_data.proyecto_nombre}")
        
        # ===== PASO 1: Buscar usuario por email =====
        usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == request_data.email)
        
        if not usuario:
            logger.warning(f"[VALIDACIÓN] Usuario no encontrado: {request_data.email}")
            return ValidateResponse(
                valid=False,
                mensaje="Credenciales inválidas"
            )
        
        # ===== PASO 2: Verificar contraseña =====
        password_bytes = request_data.password.encode('utf-8')
        clave_hash_bytes = usuario.clave_hash.encode('utf-8')
        
        if not bcrypt.checkpw(password_bytes, clave_hash_bytes):
            logger.warning(f"[VALIDACIÓN] Contraseña incorrecta: {request_data.email}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Credenciales inválidas"
            )
        
        # ===== PASO 3: Verificar usuario activo =====
        if not usuario.activo:
            logger.warning(f"[VALIDACIÓN] Usuario inactivo: {request_data.email}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Usuario no está activo"
            )
        
        # ===== PASO 4: Buscar proyecto =====
        proyecto = await Proyecto.find_one(Proyecto.nombre == request_data.proyecto_nombre)
        
        if not proyecto:
            logger.warning(f"[VALIDACIÓN] Proyecto no encontrado: {request_data.proyecto_nombre}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Proyecto no encontrado"
            )
        
        # ===== PASO 5: Verificar proyecto activo =====
        if not proyecto.activo:
            logger.warning(f"[VALIDACIÓN] Proyecto inactivo: {request_data.proyecto_nombre}")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="El proyecto no está activo"
            )
        
        # ===== PASO 6: Buscar vinculación usuario-proyecto =====
        vinculacion = await UsuarioProyecto.find_one(
            UsuarioProyecto.usuario_id == usuario.id,
            UsuarioProyecto.proyecto_id == proyecto.id
        )
        
        if not vinculacion:
            logger.warning(f"[VALIDACIÓN] Usuario no asignado al proyecto")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="Usuario no asignado a este proyecto"
            )
        
        # ===== PASO 7: Verificar vinculación activa =====
        if not vinculacion.activo:
            logger.warning(f"[VALIDACIÓN] Vinculación inactiva")
            await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
            return ValidateResponse(
                valid=False,
                mensaje="La vinculación está inactiva"
            )
        
        # ===== PASO 8: Verificar fecha de vencimiento =====
        if vinculacion.fecha_vencimiento:
            ahora = datetime.utcnow()
            if ahora > vinculacion.fecha_vencimiento:
                logger.warning(f"[VALIDACIÓN] Acceso vencido")
                await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=False)
                return ValidateResponse(
                    valid=False,
                    mensaje="El acceso al proyecto ha vencido"
                )
        
        # ===== ACCESO VÁLIDO =====
        await _update_validation_attempt(usuario.id, request_data.proyecto_nombre, success=True)
        
        logger.info(f"[VALIDACIÓN] ✅ Acceso válido para {request_data.email}")
        
        return ValidateResponse(
            valid=True,
            mensaje="Acceso válido",
            datos_usuario=DatosUsuario(
                email=usuario.mail,
                username=usuario.usuario
            ),
            fecha_vencimiento=vinculacion.fecha_vencimiento
        )
    
    except Exception as e:
        logger.error(f"[VALIDACIÓN] Error: {e}", exc_info=True)
        return ValidateResponse(
            valid=False,
            mensaje="Error interno del servidor"
        )


async def _update_validation_attempt(usuario_id, proyecto_nombre: str, success: bool):
    """
    Actualiza los campos de tracking de validación en la vinculación.
    
    Args:
        usuario_id: ID del usuario
        proyecto_nombre: Nombre del proyecto
        success: True si la validación fue exitosa, False si falló
    """
    try:
        proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
        if not proyecto:
            return
        
        vinculacion = await UsuarioProyecto.find_one(
            UsuarioProyecto.usuario_id == usuario_id,
            UsuarioProyecto.proyecto_id == proyecto.id
        )
        
        if vinculacion:
            ahora = datetime.utcnow()
            vinculacion.last_validation_attempt = ahora
            
            if success:
                vinculacion.last_validated_at = ahora
            
            vinculacion.updated_at = ahora
            await vinculacion.save()
    
    except Exception as e:
        logger.error(f"[TRACKING] Error: {e}")
```

**Respuestas Ejemplo:**

**Acceso Válido (200 OK):**
```json
{
  "valid": true,
  "mensaje": "Acceso válido",
  "datos_usuario": {
    "email": "admin@sysneg.com",
    "username": "admin"
  },
  "fecha_vencimiento": "2026-07-03T23:59:59Z"
}
```

**Acceso Denegado - Usuario Inactivo (200 OK):**
```json
{
  "valid": false,
  "mensaje": "Usuario no está activo"
}
```

**Acceso Denegado - Proyecto No Asignado (200 OK):**
```json
{
  "valid": false,
  "mensaje": "Usuario no asignado a este proyecto"
}
```

**Acceso Denegado - Vencido (200 OK):**
```json
{
  "valid": false,
  "mensaje": "El acceso al proyecto ha vencido"
}
```

### Casos de Uso del Endpoint de Validación

#### Caso 1: Validación desde Aplicación Externa

```python
import requests

# Aplicación externa valida acceso antes de permitir login
response = requests.post(
    "http://127.0.0.1:8000/api/v1/validate",
    json={
        "email": "usuario@example.com",
        "password": "password123",
        "proyecto_nombre": "Ecomerce"
    }
)

data = response.json()

if data["valid"]:
    print(f"✅ Acceso permitido para {data['datos_usuario']['username']}")
    print(f"Vence: {data['fecha_vencimiento']}")
else:
    print(f"❌ Acceso denegado: {data['mensaje']}")
```

#### Caso 2: Middleware de Autenticación

```python
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
import httpx

async def validar_acceso_middleware(request: Request, email: str, password: str):
    """
    Middleware que valida el acceso consultando el servidor de proyectos
    """
    api_url = "http://127.0.0.1:8000/api/v1/validate"
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            api_url,
            json={
                "email": email,
                "password": password,
                "proyecto_nombre": "Ecomerce"
            }
        )
        
        data = response.json()
        
        if not data["valid"]:
            raise HTTPException(
                status_code=401,
                detail=data["mensaje"]
            )
        
        # Acceso válido, continuar
        return data["datos_usuario"]
```

#### Caso 3: Integración con Sistema de Single Sign-On (SSO)

```python
async def sso_validate_user(email: str, password: str, app_name: str):
    """
    Valida usuario para múltiples aplicaciones usando el sistema central
    """
    import httpx
    
    api_url = "http://127.0.0.1:8000/api/v1/validate"
    
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                api_url,
                json={
                    "email": email,
                    "password": password,
                    "proyecto_nombre": app_name
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                
                if data["valid"]:
                    return {
                        "authenticated": True,
                        "user": data["datos_usuario"],
                        "expires": data.get("fecha_vencimiento")
                    }
                else:
                    return {
                        "authenticated": False,
                        "reason": data["mensaje"]
                    }
        
        return {
            "authenticated": False,
            "reason": "Error de conexión con servidor de autenticación"
        }
    
    except Exception as e:
        logger.error(f"Error en SSO: {e}")
        return {
            "authenticated": False,
            "reason": "Error interno"
        }
```

### Flujo de Validación

```
┌──────────────────────────────────────────────────────────┐
│            APLICACIÓN EXTERNA REQUIERE ACCESO            │
└────────────────────────┬─────────────────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ POST /api/v1/validate        │
          │ {email, password, proyecto}  │
          └──────────┬───────────────────┘
                     │
                     ▼
          ┌──────────────────────┐
          │ ¿Usuario existe?     │
          └──────┬───────────────┘
                 │
          ┌──────┴──────┐
         NO              SÍ
          │              │
          ▼              ▼
      RECHAZAR   ┌────────────────┐
                 │ ¿Password OK?  │
                 └───┬────────────┘
                     │
              ┌──────┴──────┐
             NO            SÍ
              │             │
              ▼             ▼
          RECHAZAR  ┌──────────────┐
                    │ ¿Usuario     │
                    │ activo?      │
                    └───┬──────────┘
                        │
                 ┌──────┴──────┐
                NO            SÍ
                 │             │
                 ▼             ▼
             RECHAZAR  ┌──────────────┐
                       │ ¿Proyecto    │
                       │ existe?      │
                       └───┬──────────┘
                           │
                    ┌──────┴──────┐
                   NO            SÍ
                    │             │
                    ▼             ▼
                RECHAZAR  ┌──────────────┐
                          │ ¿Proyecto    │
                          │ activo?      │
                          └───┬──────────┘
                              │
                       ┌──────┴──────┐
                      NO            SÍ
                       │             │
                       ▼             ▼
                   RECHAZAR  ┌──────────────────┐
                             │ ¿Vinculación     │
                             │ existe?          │
                             └───┬──────────────┘
                                 │
                          ┌──────┴──────┐
                         NO            SÍ
                          │             │
                          ▼             ▼
                      RECHAZAR  ┌──────────────────┐
                                │ ¿Vinculación     │
                                │ activa?          │
                                └───┬──────────────┘
                                    │
                             ┌──────┴──────┐
                            NO            SÍ
                             │             │
                             ▼             ▼
                         RECHAZAR  ┌──────────────────┐
                                   │ ¿Fecha vencida?  │
                                   └───┬──────────────┘
                                       │
                                ┌──────┴──────┐
                               SÍ            NO
                                │             │
                                ▼             ▼
                            RECHAZAR   ┌──────────────┐
                                       │ ✅ ACCESO    │
                                       │    VÁLIDO    │
                                       └──────────────┘
```

---

## 🎯 Rutas del Servidor Destino (Puerto 8001)

### Endpoint: Login con Sincronización Automática

**Archivo**: `Projects/Admin/routes/auth.py`

#### Función: Sincronizar Usuario Remoto

```python
async def sincronizar_usuario_remoto(username_o_email: str):
    """
    Crea un usuario local desde el servidor remoto si no existe.
    
    Args:
        username_o_email: Username o email del usuario
        
    Returns:
        AdminUsuarios object o None
    """
    try:
        api_base_url = os.getenv("API_BASE_URL")
        proyecto_nombre = os.getenv("ADMIN_PROYECTO_NOMBRE", "Ecomerce")
        
        if not api_base_url:
            logger.warning("[SYNC USER] API_BASE_URL no configurado")
            return None
        
        # Consultar servidor remoto
        url = f"{api_base_url}/api/v1/proyecto/{proyecto_nombre}/usuarios"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
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
                return None
            
            # Buscar o crear proyecto
            proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
            if not proyecto:
                proyecto = Proyecto(
                    nombre=proyecto_nombre,
                    descripcion=f"Proyecto {proyecto_nombre}",
                    activo=True
                )
                await proyecto.save()
            
            # Parsear fecha de vencimiento
            fecha_venc = None
            if usuario_remoto.get("fecha_vencimiento"):
                fecha_str = usuario_remoto["fecha_vencimiento"].rstrip('Z')
                fecha_venc = datetime.fromisoformat(fecha_str)
                if fecha_venc.tzinfo is None:
                    fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
            
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
            
            # Crear vinculación
            vinculacion = UsuarioProyecto(
                usuario_id=nuevo_usuario.id,
                proyecto_id=proyecto.id,
                fecha_vencimiento=fecha_venc,
                activo=usuario_remoto["activo"]
            )
            await vinculacion.save()
            
            return nuevo_usuario
            
    except Exception as e:
        logger.error(f"[SYNC USER] Error: {e}", exc_info=True)
        return None
```

#### Función: Sincronizar Datos de Usuario

```python
async def sincronizar_password_remota(usuario: AdminUsuarios) -> bool:
    """
    Sincroniza contraseña, estado activo y fecha_vencimiento desde servidor remoto.
    
    Args:
        usuario: Usuario local a sincronizar
        
    Returns:
        True si se actualizó algo, False si no
    """
    try:
        api_base_url = os.getenv("API_BASE_URL")
        proyecto_nombre = usuario.proyecto_nombre or os.getenv("ADMIN_PROYECTO_NOMBRE", "Ecomerce")
        
        if not api_base_url:
            return False
        
        # Consultar servidor remoto
        url = f"{api_base_url}/api/v1/proyecto/{proyecto_nombre}/usuarios"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(url)
            
            if response.status_code != 200:
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
                return False
            
            hash_remoto = usuario_remoto.get("clave_hash")
            
            if not hash_remoto:
                return False
            
            # Verificar si hay cambios
            cambios = []
            
            # Contraseña
            if hash_remoto != usuario.clave_hash:
                cambios.append("contraseña")
                usuario.clave_hash = hash_remoto
            
            # Estado activo
            activo_remoto = usuario_remoto.get("activo", True)
            if activo_remoto != usuario.activo:
                cambios.append("estado activo")
                usuario.activo = activo_remoto
            
            # Fecha de vencimiento
            if usuario_remoto.get("fecha_vencimiento"):
                fecha_str = usuario_remoto["fecha_vencimiento"].rstrip('Z')
                fecha_venc = datetime.fromisoformat(fecha_str)
                if fecha_venc.tzinfo is None:
                    fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
                
                if fecha_venc != usuario.fecha_vencimiento:
                    cambios.append("fecha_vencimiento")
                    usuario.fecha_vencimiento = fecha_venc
            
            if not cambios:
                return False
            
            # Guardar cambios
            await usuario.save()
            logger.info(f"[SYNC] Actualizados: {', '.join(cambios)}")
            
            return True
            
    except Exception as e:
        logger.error(f"[SYNC] Error: {e}", exc_info=True)
        return False
```

#### Endpoint: Login

```python
@router.post("/api/login", name="admin_login_api")
async def admin_login_api(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    next: str = Form(default="/admin/dashboard")
):
    """
    Login con sincronización automática de usuarios desde servidor remoto.
    """
    try:
        client_ip = request.client.host if request.client else "unknown"
        
        # PASO 1: Buscar usuario localmente
        usuario = await AdminUsuarios.find_one(AdminUsuarios.usuario == username)
        
        if not usuario:
            usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == username)
        
        # PASO 2: Si no existe, crear desde servidor remoto
        if not usuario:
            logger.warning(f"⚠️  Usuario no encontrado: {username}, sincronizando...")
            usuario = await sincronizar_usuario_remoto(username)
            
            if not usuario:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
        
        # PASO 3: Si está inactivo, verificar en servidor remoto
        if not usuario.activo:
            logger.warning(f"⚠️  Usuario inactivo: {username}, verificando...")
            
            if await sincronizar_password_remota(usuario):
                usuario = await AdminUsuarios.get(usuario.id)
                
                if not usuario.activo:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Usuario inactivo"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario inactivo"
                )
        
        # PASO 4: Verificar fecha de vencimiento
        if usuario.fecha_vencimiento:
            ahora = datetime.now(timezone.utc)
            fecha_venc = usuario.fecha_vencimiento
            
            if fecha_venc.tzinfo is None:
                fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
            
            if fecha_venc < ahora:
                usuario.activo = False
                await usuario.save()
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail=f"Su acceso ha expirado el {fecha_venc.strftime('%d/%m/%Y')}"
                )
        
        # PASO 5: Verificar contraseña
        if not verificar_clave(password, usuario.clave_hash):
            # Intentar sincronizar desde remoto
            if await sincronizar_password_remota(usuario):
                usuario = await AdminUsuarios.get(usuario.id)
                
                # Verificar nuevamente estado activo
                if not usuario.activo:
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Usuario inactivo"
                    )
                
                # Verificar nuevamente vencimiento
                if usuario.fecha_vencimiento:
                    ahora = datetime.now(timezone.utc)
                    fecha_venc = usuario.fecha_vencimiento
                    if fecha_venc.tzinfo is None:
                        fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
                    
                    if fecha_venc < ahora:
                        usuario.activo = False
                        await usuario.save()
                        raise HTTPException(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            detail=f"Su acceso ha expirado"
                        )
                
                # Verificar contraseña nuevamente
                if not verificar_clave(password, usuario.clave_hash):
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Credenciales inválidas"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Credenciales inválidas"
                )
        else:
            # Contraseña correcta, sincronizar otros datos
            await sincronizar_password_remota(usuario)
            usuario = await AdminUsuarios.get(usuario.id)
            
            # Verificar si se desactivó
            if not usuario.activo:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Usuario inactivo"
                )
            
            # Verificar vencimiento actualizado
            if usuario.fecha_vencimiento:
                ahora = datetime.now(timezone.utc)
                fecha_venc = usuario.fecha_vencimiento
                if fecha_venc.tzinfo is None:
                    fecha_venc = fecha_venc.replace(tzinfo=timezone.utc)
                
                if fecha_venc < ahora:
                    usuario.activo = False
                    await usuario.save()
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=f"Su acceso ha expirado"
                    )
        
        # PASO 6: Generar JWT token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": usuario.mail,
                "usuario": usuario.usuario,
                "nombre": usuario.nombre
            },
            expires_delta=access_token_expires
        )
        
        logger.info(f"✅ Login exitoso: {username} desde {client_ip}")
        
        return JSONResponse(
            status_code=200,
            content={
                "access_token": access_token,
                "token_type": "bearer",
                "usuario": {
                    "mail": usuario.mail,
                    "usuario": usuario.usuario,
                    "nombre": usuario.nombre
                },
                "next": next
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error en login: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error interno del servidor"
        )
```

---

## 🔄 Flujo de Sincronización Automática

### Diagrama de Flujo

```
┌─────────────────────────────────────────────────────────────┐
│                    USUARIO INTENTA LOGIN                     │
│              POST /admin/api/login                          │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │ ¿Usuario existe localmente?  │
          └──────────┬───────────────────┘
                     │
          ┌──────────┴──────────┐
          │                     │
         NO                    SÍ
          │                     │
          ▼                     ▼
┌──────────────────┐  ┌─────────────────────┐
│ SINCRONIZAR      │  │ ¿Usuario activo?    │
│ DESDE REMOTO     │  └──────┬──────────────┘
│ - Crear usuario  │         │
│ - Crear vinc.    │  ┌──────┴──────┐
└────────┬─────────┘  │            │
         │           NO           SÍ
         ▼            │            │
┌──────────────────┐  │            ▼
│ ¿Se creó?        │  │  ┌──────────────────────┐
└───┬──────────────┘  │  │ ¿Fecha vencida?      │
    │                 │  └──────┬───────────────┘
   SÍ                 │         │
    │                 │  ┌──────┴──────┐
    │                 │  │            │
    │                 │ NO           SÍ
    │                 │  │            │
    │                 ▼  ▼            ▼
    │        ┌────────────────┐  ┌────────────┐
    │        │ SINCRONIZAR    │  │ RECHAZAR   │
    │        │ DESDE REMOTO   │  │ ACCESO     │
    │        │ - Password     │  └────────────┘
    │        │ - Estado       │
    │        │ - Fecha venc.  │
    │        └────┬───────────┘
    │             │
    │             ▼
    │    ┌──────────────────┐
    │    │ ¿Sigue inactivo  │
    │    │ o vencido?       │
    │    └────┬─────────────┘
    │         │
    │  ┌──────┴──────┐
    │  │            │
    │ SÍ           NO
    │  │            │
    │  ▼            ▼
    │ RECHAZAR  ┌──────────────────┐
    │ ACCESO    │ VERIFICAR        │
    │           │ CONTRASEÑA       │
    │           └────┬─────────────┘
    │                │
    │         ┌──────┴──────┐
    │         │            │
    │      CORRECTO    INCORRECTO
    │         │            │
    │         │            ▼
    │         │   ┌──────────────────┐
    │         │   │ SINCRONIZAR      │
    │         │   │ CONTRASEÑA       │
    │         │   │ DESDE REMOTO     │
    │         │   └────┬─────────────┘
    │         │        │
    │         │        ▼
    │         │   ┌──────────────┐
    │         │   │ ¿Ahora OK?   │
    │         │   └───┬──────────┘
    │         │       │
    │         │  ┌────┴────┐
    │         │  │        │
    │         │ SÍ       NO
    │         │  │        │
    ▼         ▼  ▼        ▼
┌──────────────────┐  ┌────────────┐
│ GENERAR JWT      │  │ RECHAZAR   │
│ ✅ LOGIN EXITOSO │  │ ACCESO     │
└──────────────────┘  └────────────┘
```

---

## ⚙️ Configuración

### Variables de Entorno (.env)

**Servidor Destino (Puerto 8001)**:

```env
# URL del servidor fuente
API_BASE_URL=http://127.0.0.1:8000

# Nombre del proyecto
ADMIN_PROYECTO_NOMBRE=Ecomerce

# JWT Configuration
JWT_SECRET_KEY=tu_clave_secreta_super_segura
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# MongoDB
MONGO_URL=mongodb://localhost:27017
MONGO_DB=db_ecomerce
```

### Dependencias Requeridas

```txt
fastapi
uvicorn
motor
beanie
pydantic[email]
python-dotenv
httpx
bcrypt
python-jose[cryptography]
```

---

## 🚀 Implementación Paso a Paso

### Paso 1: Preparar Modelos

1. Crea los tres modelos en `Projects/Admin/models/`:

**admin_usuarios_beanie.py**:
```python
from beanie import Document
from pydantic import Field, EmailStr
from typing import Optional
from datetime import datetime

class AdminUsuarios(Document):
    usuario: str = Field(...)
    nombre: str = Field(...)
    mail: EmailStr = Field(...)
    clave_hash: str = Field(...)
    activo: bool = Field(default=True)
    imagen_perfil: Optional[str] = Field(default=None)
    proyecto_nombre: Optional[str] = Field(default="Ecomerce")
    fecha_vencimiento: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "admin_usuarios"
```

**proyectos_beanie.py**:
```python
from beanie import Document, PydanticObjectId
from pydantic import Field
from typing import Optional
from datetime import datetime

class Proyecto(Document):
    nombre: str = Field(...)
    descripcion: Optional[str] = Field(default=None)
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "proyectos"


class UsuarioProyecto(Document):
    usuario_id: PydanticObjectId = Field(...)
    proyecto_id: PydanticObjectId = Field(...)
    fecha_vencimiento: Optional[datetime] = Field(default=None)
    activo: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "usuario_proyectos"
```

2. Registra los modelos en tu configuración de Beanie:

```python
from beanie import init_beanie
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto

async def init_db():
    await init_beanie(
        database=database,
        document_models=[
            AdminUsuarios,
            Proyecto,
            UsuarioProyecto
        ]
    )
```

---

### Paso 2: Implementar Rutas en Servidor Fuente

1. Crea `Projects/Admin/routes/validacion_externa.py` con el endpoint de listado
2. Registra el router en tu aplicación principal:

```python
from Projects.Admin.routes import validacion_externa

app.include_router(validacion_externa.router)
```

---

### Paso 3: Implementar Sincronización en Servidor Destino

1. Instala dependencias:

```bash
pip install httpx python-dotenv
```

2. Configura variables de entorno en `.env`

3. Modifica `Projects/Admin/routes/auth.py`:
   - Agrega `from dotenv import load_dotenv` y `load_dotenv()`
   - Agrega las funciones de sincronización
   - Modifica el endpoint de login

---

## � Implementar Validación en Servidor Destino

El servidor destino (puerto 8001) puede implementar el **mismo endpoint de validación** para que otras aplicaciones puedan validar usuarios contra él.

### Opción 1: Validación Local (Sin Consultar Remoto)

Si los usuarios ya están sincronizados localmente, implementa el mismo endpoint:

```python
# En Projects/Admin/routes/validacion_externa.py del servidor destino

@router.post("/api/v1/validate", response_model=ValidateResponse)
async def validate_user_project_access(request_data: ValidateRequest, request: Request):
    """
    Valida el acceso de un usuario a un proyecto específico (local).
    Mismo código que el servidor fuente.
    """
    # [Mismo código que en servidor fuente]
    # Ver implementación completa en la sección "Endpoint de Validación de Acceso"
    pass
```

### Opción 2: Proxy al Servidor Fuente

Si quieres que el servidor destino consulte al servidor fuente para validar:

```python
# En Projects/Admin/routes/validacion_externa.py del servidor destino

@router.post("/api/v1/validate", response_model=ValidateResponse)
async def validate_user_project_access_proxy(request_data: ValidateRequest, request: Request):
    """
    Proxy de validación: consulta al servidor fuente.
    Útil para mantener una única fuente de verdad.
    """
    try:
        api_base_url = os.getenv("API_BASE_URL")
        
        if not api_base_url:
            return ValidateResponse(
                valid=False,
                mensaje="Servidor de validación no configurado"
            )
        
        # Consultar servidor fuente
        url = f"{api_base_url}/api/v1/validate"
        
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                url,
                json={
                    "email": request_data.email,
                    "password": request_data.password,
                    "proyecto_nombre": request_data.proyecto_nombre
                }
            )
            
            if response.status_code == 200:
                return ValidateResponse(**response.json())
            else:
                return ValidateResponse(
                    valid=False,
                    mensaje="Error consultando servidor de validación"
                )
    
    except Exception as e:
        logger.error(f"Error en proxy de validación: {e}", exc_info=True)
        return ValidateResponse(
            valid=False,
            mensaje="Error interno del servidor"
        )
```

### Opción 3: Validación Híbrida (Local con Fallback Remoto)

Valida localmente, pero si falla consulta al servidor remoto para sincronizar:

```python
@router.post("/api/v1/validate", response_model=ValidateResponse)
async def validate_user_project_access_hybrid(request_data: ValidateRequest, request: Request):
    """
    Validación híbrida: intenta local, si falla sincroniza y reintenta.
    """
    try:
        # Intentar validación local
        resultado_local = await _validar_local(request_data)
        
        if resultado_local.valid:
            return resultado_local
        
        # Si falló localmente, sincronizar y reintentar
        logger.info(f"Validación local falló, sincronizando desde remoto...")
        
        # Sincronizar usuario desde remoto
        usuario_sincronizado = await sincronizar_usuario_remoto(request_data.email)
        
        if usuario_sincronizado:
            # Reintentar validación local
            resultado_local = await _validar_local(request_data)
            return resultado_local
        else:
            return ValidateResponse(
                valid=False,
                mensaje="Credenciales inválidas"
            )
    
    except Exception as e:
        logger.error(f"Error en validación híbrida: {e}", exc_info=True)
        return ValidateResponse(
            valid=False,
            mensaje="Error interno del servidor"
        )


async def _validar_local(request_data: ValidateRequest) -> ValidateResponse:
    """
    Función auxiliar para validación local.
    Implementa las 8 validaciones descritas arriba.
    """
    # [Implementar las 8 validaciones locales]
    # Ver código completo en sección "Endpoint de Validación de Acceso"
    pass
```

---

## 📋 Tabla Resumen de Endpoints

| Endpoint | Método | Servidor | Propósito | Autenticación |
|----------|--------|----------|-----------|---------------|
| `/api/v1/proyecto/{nombre}/usuarios` | GET | Fuente (8000) | Listar usuarios de un proyecto | No requerida |
| `/api/v1/validate` | POST | Fuente (8000) | Validar acceso usuario-proyecto | No requerida |
| `/admin/api/login` | POST | Destino (8001) | Login con sincronización automática | No requerida |
| `/api/v1/validate` | POST | Destino (8001) | Validar acceso (opcional - 3 opciones) | No requerida |

---

## �📝 Notas Importantes

### Seguridad

1. **Nunca envíes contraseñas en texto plano**: Solo sincroniza los hashes bcrypt
2. **Usa HTTPS en producción**: La sincronización debe ser sobre conexiones seguras
3. **Valida orígenes**: Considera agregar autenticación al endpoint de listado
4. **Rate limiting**: Implementa límites de tasa para prevenir abuso

### Rendimiento

1. **Timeout de httpx**: Configurado a 10 segundos, ajusta según necesites
2. **Cache**: Considera cachear las consultas al servidor remoto
3. **Sincronización selectiva**: Solo sincroniza cuando sea necesario

### Mantenimiento

1. **Logs**: Todos los eventos están logueados con prefijos `[SYNC USER]` y `[SYNC PASSWORD]`
2. **Monitoreo**: Monitorea los logs para detectar problemas
3. **Backups**: Realiza backups antes de cambios masivos

---

## 🧪 Pruebas

### Test 1: Login con Usuario No Existente

```python
import requests

response = requests.post(
    "http://127.0.0.1:8001/admin/api/login",
    data={
        "username": "nuevo_usuario@example.com",
        "password": "password123"
    }
)

# Debe crear el usuario desde el servidor remoto y hacer login
print(response.json())
```

### Test 2: Reactivación de Usuario

```python
# 1. Desactivar usuario localmente en servidor destino
# 2. Activar usuario en servidor fuente
# 3. Intentar login en servidor destino

response = requests.post(
    "http://127.0.0.1:8001/admin/api/login",
    data={
        "username": "usuario_desactivado@example.com",
        "password": "password123"
    }
)

# Debe sincronizar estado activo y permitir login
print(response.json())
```

### Test 3: Cambio de Contraseña

```python
# 1. Cambiar contraseña en servidor fuente
# 2. Intentar login en servidor destino con nueva contraseña

response = requests.post(
    "http://127.0.0.1:8001/admin/api/login",
    data={
        "username": "admin@example.com",
        "password": "nueva_password123"
    }
)

# Debe sincronizar contraseña y permitir login
print(response.json())
```

### Test 4: Validación de Acceso Externo

```python
import requests

# Test validación exitosa
response = requests.post(
    "http://127.0.0.1:8000/api/v1/validate",
    json={
        "email": "admin@sysneg.com",
        "password": "admin123",
        "proyecto_nombre": "Ecomerce"
    }
)

data = response.json()
print(f"Válido: {data['valid']}")
print(f"Mensaje: {data['mensaje']}")

if data['valid']:
    print(f"Usuario: {data['datos_usuario']['username']}")
    print(f"Email: {data['datos_usuario']['email']}")
    print(f"Vencimiento: {data.get('fecha_vencimiento')}")
```

### Test 5: Validación con Usuario Inactivo

```python
# 1. Desactivar usuario en base de datos
# 2. Intentar validación

response = requests.post(
    "http://127.0.0.1:8000/api/v1/validate",
    json={
        "email": "usuario_inactivo@example.com",
        "password": "password123",
        "proyecto_nombre": "Ecomerce"
    }
)

data = response.json()
# Debe retornar: {"valid": false, "mensaje": "Usuario no está activo"}
print(data)
```

### Test 6: Validación con Proyecto No Asignado

```python
response = requests.post(
    "http://127.0.0.1:8000/api/v1/validate",
    json={
        "email": "admin@sysneg.com",
        "password": "admin123",
        "proyecto_nombre": "ProyectoNoAsignado"
    }
)

data = response.json()
# Debe retornar: {"valid": false, "mensaje": "Proyecto no encontrado"}
# o "Usuario no asignado a este proyecto"
print(data)
```

### Test 7: Validación con Acceso Vencido

```python
from datetime import datetime, timedelta

# 1. Configurar fecha_vencimiento en el pasado
# 2. Intentar validación

response = requests.post(
    "http://127.0.0.1:8000/api/v1/validate",
    json={
        "email": "usuario_vencido@example.com",
        "password": "password123",
        "proyecto_nombre": "Ecomerce"
    }
)

data = response.json()
# Debe retornar: {"valid": false, "mensaje": "El acceso al proyecto ha vencido"}
print(data)
```

---

## 📚 Resumen

Este sistema proporciona:

✅ **Sincronización automática** de usuarios durante el login  
✅ **Creación automática** de usuarios que no existen localmente  
✅ **Actualización automática** de contraseñas, estado activo y fechas de vencimiento  
✅ **Reactivación automática** cuando usuarios son reactivados remotamente  
✅ **Validación de vencimientos** con desactivación automática  
✅ **Sistema de vinculaciones** usuario-proyecto con fechas de vencimiento  
✅ **Logs detallados** para debugging y auditoría  

**Resultado**: Los usuarios se mantienen sincronizados automáticamente entre ambas aplicaciones sin intervención manual.

---

## 🔗 Enlaces Útiles

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Beanie ODM Documentation](https://beanie-odm.dev/)
- [MongoDB Documentation](https://docs.mongodb.com/)
- [httpx Documentation](https://www.python-httpx.org/)
- [bcrypt Documentation](https://github.com/pyca/bcrypt/)

---

**Versión**: 2.0  
**Fecha**: 12 de enero de 2026  
**Autor**: Sistema de Sincronización Automática
