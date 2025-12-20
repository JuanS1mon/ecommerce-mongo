# Imports necesarios
from datetime import date, timedelta, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, FastAPI, Form, HTTPException, Request, status
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, HTMLResponse
from security.security import encriptar_clave
from security.jwt_auth import get_current_user, require_admin
from security.auth_middleware import require_admin_for_template, get_authenticated_user
from db.models.config.usuarios import Usuarios
from db.schemas.config.Usuarios import UserDB


# Definir la instancia de Jinja2Templates
templates = Jinja2Templates(directory="static")

# Definir el router directamente
router = APIRouter(
    include_in_schema=False,
    prefix="/admin",
    tags=["Admin"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "Ruta no encontrada"}}
)

@router.get("")
async def admin_page(
    request: Request, 
    user_data: Dict[str, Any] = Depends(require_admin_for_template)
):
    """
    Página de admin - Versión simplificada para debug
    """
    try:
        print(f"🔍 ADMIN DEBUG: Usuario autenticado: {user_data['user']['usuario']}")
        print(f"🔍 ADMIN DEBUG: Roles: {user_data['user'].get('roles', [])}")
        print(f"🔍 ADMIN DEBUG: is_admin: {user_data.get('is_admin', False)}")
        
        # Usar los datos del middleware
        template_data = {
            "request": request,
            **user_data
        }
        
        print(f"🔍 Renderizando template con datos: {template_data.keys()}")
        return templates.TemplateResponse("admin.html", template_data)
        
    except Exception as e:
        print(f"❌ ERROR EN ADMIN: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500, 
            detail=f"Error en admin: {str(e)}"
        )

@router.get("/data")
async def admin_data(
        current_user: UserDB = Depends(require_admin)
    ):
    """
    API protegida para obtener datos del usuario admin.
    Requiere token JWT válido.
    """
    print("=========== API DE DATOS ADMIN ===========")
    print(f"Usuario autenticado: {current_user.usuario}")
    print(f"Roles: {current_user.roles}")
    
    return {
        "user": {
            "username": current_user.usuario,
            "nombre": current_user.nombre,
            "email": current_user.mail,
            "roles": current_user.roles,
            "activo": current_user.activo
        },
        "message": "Datos de admin obtenidos exitosamente"
    }

@router.get("/perfil")
async def user_perfil(
    request: Request,
    user_data: Dict[str, Any] = Depends(require_admin_for_template)
):
    """Página de perfil de cliente - AUTENTICACIÓN BACKEND"""
    return templates.TemplateResponse(
        "/clientes/cliente_admin.html",
        {
            "request": request,
            **user_data
        }
    )

@router.post("/perfil")
async def update_perfil(
    request: Request,
    nombre: str = Form(...),
    telefono: str = Form(...),
    email: str = Form(...),
    direccion: str = Form(...),
    fecha_nacimiento: Optional[str] = Form(None),
    password: Optional[str] = Form(None),
    user: UserDB = Depends(get_authenticated_user)
):
    """Actualización del perfil de cliente - AUTENTICACIÓN BACKEND"""
    db_user = db.query(Usuarios).filter(Usuarios.codigo == user.codigo).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="Cliente no encontrado")

    db_user.nombre = nombre
    db_user.telefono = telefono
    db_user.mail = email
    db_user.direccion = direccion
    if fecha_nacimiento:
        db_user.fecha_nacimiento = fecha_nacimiento
    if password:
        db_user.clave = encriptar_clave(password)

    try:
        db.commit()
        db.refresh(db_user)
        message = "Perfil actualizado exitosamente"
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar el perfil: {str(e)}")

    return templates.TemplateResponse(
        "/clientes/cliente_admin.html",
        {
            "request": request, 
            "user": user, 
            "message": message,
            "is_authenticated": True,
            "is_admin": "admin" in getattr(user, 'roles', [])
        }
    )

# ============================================================================
# ROUTER DEBUG: Endpoint de admin simplificado para diagnóstico
# ============================================================================

@router.get("/debug")
async def admin_debug(
    request: Request,
    current_user: UserDB = Depends(require_admin)
):
    """Endpoint de debug simplificado para admin"""
    try:
        print("🔍 DEBUG /admin/debug - Iniciando...")
        print(f"Usuario: {current_user}")
        print(f"Request: {request}")
        
        # Verificar usuario
        if not current_user:
            print("❌ Usuario no encontrado")
            raise HTTPException(status_code=401, detail="Usuario no autenticado")
        
        print(f"✅ Usuario válido: {current_user.usuario}")
        
        # Intentar devolver JSON simple primero
        return {
            "message": "Debug exitoso",
            "user": {
                "usuario": current_user.usuario,
                "nombre": current_user.nombre,
                "roles": getattr(current_user, 'roles', [])
            }
        }
        
    except Exception as e:
        print(f"❌ Error en debug: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error debug: {str(e)}")

@router.get("/test-template")
async def test_template(request: Request):
    """Endpoint de prueba para verificar que Jinja2 funciona"""
    test_data = {
        "user": {
            "nombre": "Usuario de Prueba",
            "usuario": "test"
        },
        "user_count": 42,
        "activity_count": 5,
        "activities": [],
        "is_admin": True
    }
    
    try:
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                **test_data
            }
        )
    except Exception as e:
        return f"Error renderizando template: {str(e)}"

@router.get("/debug-cookies")
async def debug_cookies(request: Request):
    """Debug para verificar cookies"""
    return {
        "cookies_recibidas": dict(request.cookies),
        "headers": dict(request.headers),
        "url": str(request.url)
    }

# ============================================================================
# ROUTER DEBUG: Endpoint de admin simplificado para diagnóstico
# ============================================================================

@router.get("/simple-debug")
async def simple_admin_debug(request: Request):
    """Endpoint de debug sin autenticación para verificar básico"""
    return {
        "message": "Endpoint debug sin autenticación funcionando",
        "url": str(request.url),
        "cookies": dict(request.cookies),
        "has_access_token": "access_token" in request.cookies
    }

# ============================================================================
# GESTIÓN DE CLIENTES
# ============================================================================

@router.get("/clientes")
async def clientes_page(
    request: Request,
    user_data: Dict[str, Any] = Depends(require_admin_for_template),
):
    """Página de gestión de clientes"""
    try:
        # Obtener lista de clientes (todos los usuarios que no son admin)

        # Consulta para obtener clientes (usuarios que no tienen rol admin)
            SELECT u.codigo, u.usuario, u.nombre, u.mail, u.activo, u.fecha_creacion
            FROM Usuarios u
            LEFT JOIN UsuariosRol ur ON u.codigo = ur.usuario_id
            LEFT JOIN Roles r ON ur.rol_id = r.id
            WHERE u.activo = 1 AND (r.nombre IS NULL OR r.nombre != 'admin')
            GROUP BY u.codigo, u.usuario, u.nombre, u.mail, u.activo, u.fecha_creacion
            ORDER BY u.fecha_creacion DESC
        """)


        clientes = []
        for row in clientes_result:
            clientes.append({
                "codigo": row[0],
                "usuario": row[1],
                "nombre": row[2],
                "email": row[3],
                "activo": row[4],
                "fecha_creacion": row[5]
            })

        template_data = {
            "request": request,
            **user_data,
            "clientes": clientes,
            "total_clientes": len(clientes)
        }

        return templates.TemplateResponse("clientes.html", template_data)

    except Exception as e:
        print(f"❌ Error en página de clientes: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error en gestión de clientes: {str(e)}"
        )

@router.get("/clientes/{cliente_id}")
async def cliente_detalle(
    cliente_id: int,
    request: Request,
    user_data: Dict[str, Any] = Depends(require_admin_for_template),
):
    """Página de detalle de cliente"""
    try:
        # Obtener datos del cliente
        cliente = db.query(Usuarios).filter(Usuarios.codigo == cliente_id).first()
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente no encontrado")

        cliente_data = {
            "codigo": cliente.codigo,
            "usuario": cliente.usuario,
            "nombre": cliente.nombre,
            "email": cliente.mail,
            "telefono": getattr(cliente, 'telefono', ''),
            "direccion": getattr(cliente, 'direccion', ''),
            "fecha_nacimiento": getattr(cliente, 'fecha_nacimiento', None),
            "activo": cliente.activo,
            "fecha_creacion": getattr(cliente, 'fecha_creacion', None)
        }

        template_data = {
            "request": request,
            **user_data,
            "cliente": cliente_data
        }

        return templates.TemplateResponse("cliente_detalle.html", template_data)

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error en detalle de cliente: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo detalle del cliente: {str(e)}"
        )

@router.get("/loginpage", response_class=HTMLResponse)
async def admin_login_page():
    """Página de login para administradores"""
    try:
        # Usar la página de login existente pero con contexto de admin
        with open("static/login.html", "r", encoding="utf-8") as file:
            content = file.read()
            # Agregar un indicador de que es login de admin
            content = content.replace(
                "<title>",
                "<title>Login Administrador - "
            ).replace(
                "Iniciar Sesión",
                "Iniciar Sesión (Admin)"
            )
            return HTMLResponse(content=content, status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página de login de admin no encontrada</h1>", status_code=404)
