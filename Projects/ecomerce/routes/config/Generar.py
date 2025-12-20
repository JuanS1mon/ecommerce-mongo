# generar.py
"""
Router para el generador de código de aplicaciones.
Proporciona endpoints para generar CRUD, schemas, modelos y vistas HTML.
Incluye mejoras de seguridad, validación y manejo de errores.
"""

from starlette.responses import FileResponse
import logging
import os
import time
from typing import Dict, Any, List, Optional
import traceback
import fileinput

from fastapi import APIRouter, Depends, Request, status, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, JSONResponse

# Imports del proyecto
from .Generar_Funciones.Generar_Cruds import generate_crud_functions
from .Generar_Funciones.Generar_Html import generate_html_form
from .Generar_Funciones.Generar_Html_service import generate_html_for_service
# from .Generar_Funciones.Generar_Models import generate_model  # Legacy - no usado
from .Generar_Funciones.Generar_Routes import generate_route
from .Generar_Funciones.Generar_Schema import generate_schema
from .Generar_Funciones.Generar_Test import generate_tests
from .generator_config import (
    validate_module_name, validate_fields_data, 
    sanitize_path, GENERATOR_CONFIG
)
from .backup_manager import cleanup_old_backups, get_backup_statistics

# Nuevas utilidades de seguridad
from .security_utils import (
    validate_table_name,
    validate_column_name,
    ValidationError,
    DatabaseError,
    sanitize_identifier,
    validate_pagination_params
)
from .database_service import DatabaseService

# Importar utilidades de base de datos para crear tablas
from db.database import engine, Base

from security.auth_middleware import require_auth_for_template
from .rate_limiter import rate_limit_dependency

templates = Jinja2Templates(directory="static")

# Configurar logger para este módulo
logger = logging.getLogger(__name__)

# Inicializar servicio de base de datos
db_service = DatabaseService()

router = APIRouter(
    include_in_schema=False,  # Oculta todas las rutas de este router en la documentación
    prefix="/generar",
    tags=["generar"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "ruta no encontrada"}}
)

@router.get("/")
async def migraciones_page(
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    try:
        logger.info("Intentando renderizar template generar.html")
        logger.debug(f"User data keys: {user_data.keys()}")
        
        # Verificar si el archivo existe
        import os
        template_path = "static/html/generar.html"
        if os.path.exists(template_path):
            logger.info(f"✅ Template file exists: {template_path}")
        else:
            logger.error(f"❌ Template file not found: {template_path}")
            
        return templates.TemplateResponse("html/generar.html", {
            "request": request, 
            **user_data  # Esto incluye user, user_count, activities, is_admin, is_authenticated, etc.
        })
    except Exception as e:
        logger.error(f"Error al renderizar template: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Fallback a una respuesta simple en caso de error
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content="""
        <html>
            <head><title>Error Temporal</title></head>
            <body>
                <h1>Generador de Aplicaciones</h1>
                <p>Error temporal al cargar la página. Por favor, inténtelo de nuevo.</p>
                <p>Error: """ + str(e) + """</p>
            </body>
        </html>
        """, status_code=200)

@router.get("/editor-visual")
async def editor_visual_page(
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Ruta protegida para el Editor Visual Avanzado
    Requiere autenticación y sirve el editor de forma segura
    """
    try:
        logger.info("🎨 Acceso al Editor Visual - Usuario autenticado")
        
        # Verificar si el archivo existe
        import os
        template_path = "static/html/editor_visual.html"
        if os.path.exists(template_path):
            logger.info(f"✅ Editor Visual encontrado: {template_path}")
        else:
            logger.error(f"❌ Editor Visual no encontrado: {template_path}")
            raise HTTPException(status_code=404, detail="Editor Visual no disponible")
            
        return templates.TemplateResponse("html/editor_visual.html", {
            "request": request, 
            **user_data  # Incluye user, user_count, activities, is_admin, is_authenticated, etc.
        })
        
    except Exception as e:
        logger.error(f"❌ Error al cargar Editor Visual: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        
        # Fallback seguro
        from fastapi.responses import HTMLResponse
        return HTMLResponse(content="""
        <html>
            <head><title>Error - Editor Visual</title></head>
            <body style="font-family: Arial; padding: 20px; background: #f3f4f6;">
                <div style="max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1);">
                    <h1 style="color: #dc2626; margin-bottom: 20px;">🚫 Editor Visual No Disponible</h1>
                    <p>Lo sentimos, el Editor Visual no está disponible en este momento.</p>
                    <p><strong>Error:</strong> """ + str(e) + """</p>
                    <div style="margin-top: 20px;">
                        <a href="/generar/" style="background: #3b82f6; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">← Volver al Generador</a>
                        <a href="/admin/" style="background: #6b7280; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-left: 10px;">← Volver a Admin</a>
                    </div>
                </div>
            </body>
        </html>
        """, status_code=500)

@router.get("/services/status")
async def get_services_status(
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Endpoint para obtener el estado de todos los servicios generados
    """
    try:
        services_status = []
        services_dir = "Services"
        
        if os.path.exists(services_dir):
            for service_name in os.listdir(services_dir):
                service_path = os.path.join(services_dir, service_name)
                if os.path.isdir(service_path):
                    # Verificar archivos del servicio
                    required_files = [
                        f"service_{service_name}.py",
                        f"route_{service_name}.py", 
                        f"schema_{service_name}.py",
                        f"model_{service_name}.py",
                        "__init__.py"
                    ]
                    
                    files_status = {}
                    for file_name in required_files:
                        file_path = os.path.join(service_path, file_name)
                        files_status[file_name] = os.path.exists(file_path)
                    
                    services_status.append({
                        "name": service_name,
                        "path": service_path,
                        "files": files_status,
                        "complete": all(files_status.values())
                    })
        
        return {
            "status": "success",
            "services": services_status,
            "total_services": len(services_status)
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estado de servicios: {str(e)}")
        return {"error": "Error al obtener el estado de los servicios"}

@router.delete("/services/{service_name}")
async def delete_service(
    service_name: str,
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Endpoint para eliminar un servicio generado de forma segura
    """
    try:
        # Validar nombre del servicio
        if not service_name.isalnum():
            return {"error": "Nombre de servicio inválido"}
            
        service_path = f"Services/{service_name}"
        
        if not os.path.exists(service_path):
            return {"error": "El servicio no existe"}
        
        # Log de la operación para auditoría
        logger.info(f"Usuario {user_data['user']['usuario']} eliminando servicio: {service_name}")
        
        # Crear backup antes de eliminar
        import shutil
        backup_path = f"Services/backups/{service_name}_{int(time.time())}"
        os.makedirs(os.path.dirname(backup_path), exist_ok=True)
        shutil.copytree(service_path, backup_path)
        
        # Eliminar el servicio
        shutil.rmtree(service_path)
        
        # También eliminar archivos HTML/JS asociados si existen
        static_path = f"static/{service_name}"
        if os.path.exists(static_path):
            shutil.rmtree(static_path)
        
        logger.info(f"Servicio {service_name} eliminado exitosamente. Backup en: {backup_path}")
        
        return {
            "status": "success",
            "message": f"Servicio {service_name} eliminado exitosamente",
            "backup_location": backup_path
        }
        
    except Exception as e:
        logger.error(f"Error eliminando servicio {service_name}: {str(e)}")
        return {"error": f"Error al eliminar el servicio: {str(e)}"}

@router.get("/validate/{module_name}")
async def validate_module_name_endpoint(
    module_name: str,
    user_data: dict = Depends(require_auth_for_template)
) -> Dict[str, Any]:
    """
    Valida si un nombre de módulo está disponible y es válido.
    Usa validación mejorada con seguridad reforzada.
    
    Args:
        module_name: Nombre del módulo a validar
        
    Returns:
        Diccionario con resultado de validación
    """
    try:
        # Validar usando la nueva función de validación
        valid, msg = validate_module_name(module_name)
        
        if not valid:
            return {
                "valid": False,
                "message": msg
            }
        
        # Verificar si ya existe
        service_path = f"Services/{module_name}"
        route_path = f"routers/Maestros/Route_{module_name}.py"
        
        conflicts = []
        if os.path.exists(service_path):
            conflicts.append("Servicio")
        if os.path.exists(route_path):
            conflicts.append("Ruta")
            
        if conflicts:
            return {
                "valid": False,
                "message": f"Ya existe: {', '.join(conflicts)}"
            }
        
        logger.debug(
            "Module name validated",
            extra={
                "user": user_data['user']['usuario'],
                "module": module_name,
                "valid": True
            }
        )
        
        return {
            "valid": True,
            "message": "Nombre disponible"
        }
        
    except Exception as e:
        logger.error(
            f"Error validating module name {module_name}: {str(e)}",
            exc_info=True
        )
        return {
            "valid": False,
            "message": "Error en la validación"
        }

@router.get("/config")
async def get_generator_config(
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Obtiene la configuración actual del generador
    """
    try:
        return {
            "status": "success",
            "config": {
                "max_fields": GENERATOR_CONFIG["max_fields"],
                "max_module_name_length": GENERATOR_CONFIG["max_module_name_length"],
                "max_field_name_length": GENERATOR_CONFIG["max_field_name_length"],
                "allowed_field_types": GENERATOR_CONFIG["allowed_field_types"],
                "reserved_module_names": GENERATOR_CONFIG["reserved_module_names"]
            }
        }
    except Exception as e:
        logger.error(f"Error obteniendo configuración: {str(e)}")
        return {"error": "Error al obtener la configuración"}

@router.get("/list-tables")
async def list_tables(
    user_data: dict = Depends(require_auth_for_template)
) -> Dict[str, Any]:
    """
    Lista todas las tablas disponibles en la base de datos de forma segura.
    Usa DatabaseService para operaciones optimizadas sin queries N+1.
    
    Returns:
        Diccionario con lista de tablas y metadatos
        
    Raises:
        HTTPException: Si hay error en la consulta
    """
    try:
        logger.info(
            "User requesting table list",
            extra={"user": user_data['user']['usuario']}
        )
        
        # Usar DatabaseService para obtener tablas
        tables = db_service.get_all_tables()
        
        # Obtener conteo de registros solo para las primeras 20 tablas (optimización)
        for i, table in enumerate(tables[:20]):
            try:
                table["record_count"] = db_service.get_table_record_count(table["name"])
                
                # Obtener primeras columnas como preview
                columns = db_service.get_table_columns(table["name"])
                table["columns"] = columns[:5]  # Solo las primeras 5 columnas
                
            except Exception as e:
                logger.warning(f"Error getting details for table {table['name']}: {str(e)}")
                table["record_count"] = 0
                table["columns"] = []
        
        logger.info(
            "Table list retrieved successfully",
            extra={
                "user": user_data['user']['usuario'],
                "table_count": len(tables)
            }
        )
        
        return {
            "status": "success",
            "tables": tables,
            "total_tables": len(tables)
        }
        
    except DatabaseError as e:
        logger.error(
            "Database error listing tables",
            extra={"user": user_data['user']['usuario']},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener lista de tablas de la base de datos"
        )
    except Exception as e:
        logger.critical(
            "Unexpected error listing tables",
            extra={"user": user_data['user']['usuario']},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al obtener lista de tablas"
        )

@router.get("/debug-table/{table_name}")
async def debug_table_info(
    table_name: str,
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Endpoint de debugging para diagnosticar problemas con una tabla específica
    """
    try:
        
        db = next(db_gen)
        
        debug_info = {
            "table_name": table_name,
            "tests": {}
        }
        
        try:
            # Test 1: Verificar que la tabla existe
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = :table_name 
                AND TABLE_SCHEMA = 'dbo'
            """)
            table_exists = exists_result.fetchone().count > 0
            debug_info["tests"]["table_exists"] = table_exists
            
            if not table_exists:
                debug_info["message"] = f"La tabla '{table_name}' no existe en el esquema 'dbo'"
                return {"status": "error", "debug": debug_info}
            
            # Test 2: Contar registros con diferentes métodos
            try:
                record_count1 = count_result1.fetchone().count
                debug_info["tests"]["count_method1"] = record_count1
            except Exception as e:
                debug_info["tests"]["count_method1_error"] = str(e)
            
            try:
                record_count2 = count_result2.fetchone().count
                debug_info["tests"]["count_method2"] = record_count2
            except Exception as e:
                debug_info["tests"]["count_method2_error"] = str(e)
            
            # Test 3: Obtener columnas
            try:
                    SELECT 
                        COLUMN_NAME,
                        DATA_TYPE,
                        IS_NULLABLE,
                        COLUMN_DEFAULT,
                        ORDINAL_POSITION
                    FROM INFORMATION_SCHEMA.COLUMNS 
                    WHERE TABLE_NAME = :table_name
                    AND TABLE_SCHEMA = 'dbo'
                    ORDER BY ORDINAL_POSITION
                """)
                
                columns = []
                for col in columns_result:
                    columns.append({
                        "name": col.COLUMN_NAME,
                        "type": col.DATA_TYPE,
                        "nullable": col.IS_NULLABLE,
                        "default": col.COLUMN_DEFAULT,
                        "position": col.ORDINAL_POSITION
                    })
                
                debug_info["tests"]["columns_found"] = len(columns)
                debug_info["tests"]["columns"] = columns
                
            except Exception as e:
                debug_info["tests"]["columns_error"] = str(e)
            
            # Test 4: Obtener permisos de la tabla
            try:
                    SELECT 
                        permission_name,
                        state_desc,
                        principal_id
                    FROM sys.database_permissions p
                    JOIN sys.objects o ON p.major_id = o.object_id
                    WHERE o.name = :table_name
                """)
                
                permissions = []
                for perm in perms_result:
                    permissions.append({
                        "permission": perm.permission_name,
                        "state": perm.state_desc,
                        "principal_id": perm.principal_id
                    })
                
                debug_info["tests"]["permissions"] = permissions
                
            except Exception as e:
                debug_info["tests"]["permissions_error"] = str(e)
            
            return {
                "status": "success",
                "debug": debug_info
            }
            
        finally:
            db.close()
            
    except Exception as e:
        logger.error(f"Error en debug de tabla {table_name}: {str(e)}")
        return {
            "status": "error",
            "message": str(e),
            "debug": debug_info
        }

@router.get("/table-data/{table_name}")
async def get_table_data(
    table_name: str,
    page: int = 1,
    per_page: int = 50,
    user_data: dict = Depends(require_auth_for_template)
) -> Dict[str, Any]:
    """
    Obtiene datos paginados de una tabla específica de forma segura.
    
    Args:
        table_name: Nombre de la tabla
        page: Número de página (default: 1)
        per_page: Registros por página (default: 50, max: 1000)
        
    Returns:
        Diccionario con datos paginados y metadatos
        
    Raises:
        HTTPException: Si hay error de validación o consulta
    """
    try:
        logger.info(
            "User requesting table data",
            extra={
                "user": user_data['user']['usuario'],
                "table": table_name,
                "page": page
            }
        )
        
        # Usar DatabaseService para obtener datos de forma segura
        result = db_service.get_table_data(table_name, page, per_page)
        
        logger.info(
            "Table data retrieved successfully",
            extra={
                "user": user_data['user']['usuario'],
                "table": table_name,
                "page": page,
                "records": len(result.get("records", []))
            }
        )
        
        return result
        
    except ValidationError as e:
        logger.warning(
            f"Validation error for table {table_name}",
            extra={"user": user_data['user']['usuario'], "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(
            f"Database error retrieving table data for {table_name}",
            extra={"user": user_data['user']['usuario']},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener datos de la tabla"
        )
    except Exception as e:
        logger.critical(
            f"Unexpected error retrieving table data for {table_name}",
            extra={"user": user_data['user']['usuario']},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al obtener datos"
        )

@router.get("/table-schema/{table_name}")
async def get_table_schema(
    table_name: str,
    user_data: dict = Depends(require_auth_for_template)
) -> Dict[str, Any]:
    """
    Obtiene el schema detallado de una tabla específica de forma segura.
    
    Args:
        table_name: Nombre de la tabla
        
    Returns:
        Diccionario con información completa del schema
        
    Raises:
        HTTPException: Si hay error de validación o consulta
    """
    try:
        logger.info(
            "User requesting table schema",
            extra={
                "user": user_data['user']['usuario'],
                "table": table_name,
                "table_length": len(table_name)
            }
        )
        
        # Verificar que la tabla existe antes de intentar obtener schema
        if not db_service.table_exists(table_name):
            logger.warning(
                f"Table does not exist: {table_name}",
                extra={"user": user_data['user']['usuario']}
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"La tabla '{table_name}' no existe"
            )
        
        # Usar DatabaseService para obtener schema de forma segura
        schema_info = db_service.get_table_schema(table_name)
        
        logger.info(
            "Table schema retrieved successfully",
            extra={
                "user": user_data['user']['usuario'],
                "table": table_name,
                "columns": len(schema_info.get("columns", []))
            }
        )
        
        return {
            "status": "success",
            "table": schema_info
        }
        
    except ValidationError as e:
        logger.warning(
            f"Validation error for table schema {table_name}",
            extra={"user": user_data['user']['usuario'], "error": str(e)}
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except DatabaseError as e:
        logger.error(
            f"Database error retrieving schema for {table_name}",
            extra={"user": user_data['user']['usuario']},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al obtener schema de la tabla"
        )
    except Exception as e:
        logger.critical(
            f"Unexpected error retrieving schema for {table_name}",
            extra={"user": user_data['user']['usuario']},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al obtener schema"
        )

@router.post("/generate-from-table")
async def generate_from_existing_table(
    request: Request,
    user_data: dict = Depends(require_auth_for_template),
    _rl: bool = Depends(rate_limit_dependency(limit=6, window_seconds=60))
) -> Dict[str, Any]:
    """
    Genera componentes basándose en una tabla existente de forma segura.
    Usa DatabaseService para obtener schema y validación mejorada.
    
    Args:
        request: Request con form data (table_name, module_name, opciones)
        
    Returns:
        Diccionario con resultado de la generación
        
    Raises:
        HTTPException: Si hay error de validación o generación
    """
    try:
        form_data = await request.form()
        
        table_name = form_data.get("table_name", "").strip()
        module_name = form_data.get("module_name", "").strip()
        
        if not table_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Nombre de tabla es requerido"
            )
        
        # Validar nombre de tabla
        is_valid, msg = validate_table_name(table_name)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Nombre de tabla inválido: {msg}"
            )
        
        if not module_name:
            module_name = table_name.lower()
        
        # Validar nombre del módulo
        valid_module, module_msg = validate_module_name(module_name)
        if not valid_module:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Módulo inválido: {module_msg}"
            )
        
        logger.info(
            "Generating from existing table",
            extra={
                "user": user_data['user']['usuario'],
                "table": table_name,
                "module": module_name
            }
        )
        
        # Usar DatabaseService para obtener columnas de forma segura
        try:
            columns = db_service.get_table_columns(table_name)
        except ValidationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(e)
            )
        except DatabaseError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error al obtener información de la tabla: {str(e)}"
            )
        
        if not columns:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No se encontraron columnas en la tabla '{table_name}'"
            )
        
        field_names = []
        field_types = []
        
        # Mapeo de tipos SQL Server a tipos del generador
        type_mapping = {
            'int': 'int',
            'bigint': 'int', 
            'smallint': 'int',
            'tinyint': 'int',
            'varchar': 'string',
            'nvarchar': 'string',
            'char': 'string',
            'nchar': 'string',
            'text': 'text',
            'ntext': 'text',
            'bit': 'boolean',
            'datetime': 'datetime',
            'datetime2': 'datetime',
            'date': 'date',
            'time': 'time',
            'float': 'float',
            'real': 'float',
            'decimal': 'decimal',
            'numeric': 'decimal',
            'money': 'decimal'
        }
        
        for column in columns:
            field_names.append(column['name'])
            mapped_type = type_mapping.get(column['type'].lower(), 'string')
            field_types.append(mapped_type)
        
        # Validar campos obtenidos
        valid_fields, fields_msg = validate_fields_data(field_names, field_types)
        if not valid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campos inválidos: {fields_msg}"
            )
        
        # Procesar opciones de generación
        generate_crud = form_data.get('generate_crud', 'true') == 'true'
        generate_route_opt = form_data.get('generate_route', 'true') == 'true'
        generate_schema_opt = form_data.get('generate_schema', 'true') == 'true'
        generate_html_form_opt = form_data.get('generate_html_form', 'true') == 'true'
        generate_tests_opt = form_data.get('generate_tests', 'false') == 'true'
        generate_service = form_data.get('generate_service', 'false') == 'true'
        
        result_message = f"Generación desde tabla '{table_name}' completada exitosamente"
        
        # Generar componentes
        try:
            if generate_service:
                success = generate_and_save_service(module_name, field_names, field_types)
                if success:
                    result_message += f". Servicio '{module_name}' generado y registrado."
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error al generar el servicio '{module_name}'"
                    )
            elif generate_crud:
                success = generate_and_save_crud(module_name, field_names, field_types)
                if not success:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error al generar CRUD para '{module_name}'"
                    )
                    
                if generate_route_opt:
                    success = generate_and_save_route(module_name, field_names, field_types)
                    if not success:
                        logger.warning(f"Error al generar rutas para '{module_name}'")
                
                if generate_schema_opt:
                    generate_and_save_schema(module_name, field_names, field_types)
                    
                if generate_html_form_opt:
                    html_content = generate_html_form(module_name, field_names, field_types)
                    save_html_form(module_name, html_content)
                    
                if generate_tests_opt:
                    generate_and_save_tests(module_name, field_names, field_types)
            
            logger.info(
                "Generation from table completed",
                extra={
                    "user": user_data['user']['usuario'],
                    "table": table_name,
                    "module": module_name,
                    "fields_count": len(field_names)
                }
            )
            
            return {
                "status": "success",
                "message": result_message,
                "generated_from_table": table_name,
                "module_name": module_name,
                "fields_processed": len(field_names)
            }
            
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                f"Error generating components for {module_name}",
                extra={"user": user_data['user']['usuario']},
                exc_info=True
            )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Error en la generación de componentes: {str(e)}"
            )
            
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.critical(
            "Unexpected error in generate_from_existing_table",
            extra={"user": user_data.get('user', {}).get('usuario', 'unknown')},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al generar desde tabla"
        )

@router.get("/multi-table-example")
async def get_multi_table_example(
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Proporciona un ejemplo de configuración multi-tabla
    """
    try:
        example_config = {
            "tables": [
                {
                    "name": "productos",
                    "fields": [
                        {"name": "id", "type": "int", "primary_key": True},
                        {"name": "nombre", "type": "string"},
                        {"name": "precio", "type": "decimal"},
                        {"name": "categoria_id", "type": "int", "foreign_key": "categorias.id"}
                    ]
                },
                {
                    "name": "categorias",
                    "fields": [
                        {"name": "id", "type": "int", "primary_key": True},
                        {"name": "nombre", "type": "string"},
                        {"name": "descripcion", "type": "text"}
                    ]
                },
                {
                    "name": "ordenes",
                    "fields": [
                        {"name": "id", "type": "int", "primary_key": True},
                        {"name": "fecha", "type": "datetime"},
                        {"name": "total", "type": "decimal"},
                        {"name": "cliente_id", "type": "int"}
                    ]
                }
            ],
            "relationships": [
                {
                    "from_table": "productos",
                    "from_field": "categoria_id",
                    "to_table": "categorias",
                    "to_field": "id",
                    "type": "many_to_one"
                }
            ],
            "options": {
                "generate_crud": True,
                "generate_routes": True,
                "generate_schemas": True,
                "generate_html": True,
                "generate_tests": False,
                "generate_service": False
            }
        }
        
        return {
            "status": "success",
            "success": True,  # Para compatibilidad con frontend
            "example": example_config
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo ejemplo multi-tabla: {str(e)}")
        return {
            "status": "error",
            "success": False,
            "message": f"Error al obtener ejemplo: {str(e)}"
        }

@router.post("/generate-multi-table")
async def generate_multi_table(
    request: Request,
    user_data: dict = Depends(require_auth_for_template),
    _rl: bool = Depends(rate_limit_dependency(limit=4, window_seconds=60))
):
    """
    Genera múltiples tablas y sus relaciones basándose en una configuración JSON.
    Siempre genera en formato de servicio dentro de Services/nombre_proyecto/
    """
    try:
        # Obtener configuración JSON del body
        config_data = await request.json()
        
        if not config_data or "tables" not in config_data:
            return {"error": "Configuración inválida: falta el array 'tables'"}
        
        tables = config_data["tables"]
        options = config_data.get("options", {})
        
        # Obtener o generar nombre del proyecto
        project_name = config_data.get("service_name") or config_data.get("project_name")
        
        if not project_name:
            # Generar nombre automático: app_XXXX
            import glob
            existing_services = glob.glob("Services/app_*")
            if existing_services:
                # Extraer números y encontrar el siguiente
                numbers = []
                for service_path in existing_services:
                    try:
                        num = int(service_path.split("app_")[-1])
                        numbers.append(num)
                    except:
                        pass
                next_num = max(numbers) + 1 if numbers else 1
            else:
                next_num = 1
            project_name = f"app_{next_num}"
            logger.info(f"Nombre de proyecto no especificado, usando: {project_name}")
        
        # Validar nombre del proyecto
        valid_project, project_msg = validate_module_name(project_name)
        if not valid_project:
            return {
                "status": "error",
                "success": False,
                "message": f"Nombre de proyecto inválido: {project_msg}"
            }
        
        results = []
        errors = []
        
        logger.info(f"Usuario {user_data['user']['usuario']} iniciando generación multi-tabla en proyecto '{project_name}': {len(tables)} tablas")
        
        # Procesar cada tabla
        for table_config in tables:
            table_name = table_config.get("name", "").strip()
            fields = table_config.get("fields", [])
            
            if not table_name:
                errors.append("Nombre de tabla faltante en configuración")
                continue
                
            # Validar nombre del módulo
            valid_module, module_msg = validate_module_name(table_name)
            if not valid_module:
                errors.append(f"Tabla '{table_name}': {module_msg}")
                continue
            
            # Extraer nombres y tipos de campos
            field_names = []
            field_types = []
            
            for field in fields:
                field_name = field.get("name", "").strip()
                # Buscar tanto 'field_type' como 'type' para compatibilidad
                field_type = field.get("field_type") or field.get("type", "string")
                field_type = field_type.strip() if field_type else "string"
                
                if field_name:
                    field_names.append(field_name)
                    field_types.append(field_type)
            
            if not field_names:
                errors.append(f"Tabla '{table_name}': No se especificaron campos válidos")
                continue
            
            # Validar campos
            valid_fields, fields_msg = validate_fields_data(field_names, field_types)
            if not valid_fields:
                errors.append(f"Tabla '{table_name}': {fields_msg}")
                continue
            
            try:
                # SIEMPRE generar en modo servicio dentro de Services/project_name/table_name/
                table_results = {"table": table_name, "components": []}
                
                # Generar servicio completo para esta tabla dentro del proyecto
                success = generate_multi_table_service(
                    project_name=project_name,
                    table_name=table_name,
                    field_names=field_names,
                    field_types=field_types
                )
                
                if success:
                    table_results["components"].append({
                        "type": "service_complete",
                        "success": True,
                        "description": f"Servicio completo en Services/{project_name}/{table_name}/"
                    })
                    results.append(table_results)
                else:
                    errors.append(f"Tabla '{table_name}': Error al generar servicio completo")
                
            except Exception as e:
                import traceback
                error_detail = f"Error procesando tabla '{table_name}': {str(e)}"
                logger.error(f"{error_detail}\n{traceback.format_exc()}")
                errors.append(error_detail)
        
        # Si se generaron tablas exitosamente, crear route_config del proyecto
        if results:
            try:
                generate_project_route_config(project_name, [r["table"] for r in results])
                logger.info(f"✅ route_config generado para proyecto '{project_name}'")
            except Exception as e:
                logger.warning(f"⚠️ No se pudo generar route_config del proyecto: {str(e)}")
        
        # Preparar respuesta
        if errors and not results:
            return {
                "status": "error",
                "success": False,
                "message": "No se pudo procesar ninguna tabla",
                "errors": errors
            }
        elif errors:
            return {
                "status": "partial_success", 
                "success": True,
                "message": f"Procesadas {len(results)} tablas con algunos errores en proyecto '{project_name}'",
                "results": results,
                "errors": errors,
                "project_name": project_name,
                "project_path": f"Services/{project_name}"
            }
        else:
            return {
                "status": "success",
                "success": True,
                "message": f"Generación multi-tabla completada: {len(results)} tablas en proyecto '{project_name}'",
                "results": results,
                "project_name": project_name,
                "project_path": f"Services/{project_name}"
            }
        
    except Exception as e:
        logger.error(f"Error en generación multi-tabla: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "status": "error",
            "success": False,
            "message": f"Error en la generación: {str(e)}"
        }


def create_table_in_database(service_name, table_name):
    """
    Crea físicamente la tabla en la base de datos basándose en el modelo generado.
    Utiliza SQL raw para garantizar que columnas IDENTITY se creen correctamente en SQL Server.
    
    Args:
        service_name: Nombre del servicio (ej: app_studio)
        table_name: Nombre de la tabla (ej: tabla_1)
    
    Returns:
        True si la tabla se creó exitosamente o ya existía
        
    Raises:
        Exception si hay un error al crear la tabla
    """
    import sys
    import importlib.util
    
    try:
        # Ruta al archivo de modelo
        model_path = f"Services/{service_name}/{table_name}/model_{table_name}.py"
        
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"No se encontró el modelo en {model_path}")
        
        # Cargar el módulo dinámicamente
        spec = importlib.util.spec_from_file_location(
            f"Services.{service_name}.{table_name}.model_{table_name}",
            model_path
        )
        
        if spec is None or spec.loader is None:
            raise ImportError(f"No se pudo cargar el módulo desde {model_path}")
        
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        
        # Obtener la clase del modelo
        model_class_name = table_name.capitalize()
        if not hasattr(module, model_class_name):
            raise AttributeError(f"No se encontró la clase {model_class_name} en el módulo")
        
        model_class = getattr(module, model_class_name)
        
        # Obtener información de las columnas del modelo
        table_name_full = f"{service_name}_{table_name}"
        columns = model_class.__table__.columns
        
        # Detectar si hay columna 'id' de tipo entero (requiere IDENTITY)
        has_autoincrement_id = False
        id_column = None
        
        for col in columns:
            if col.name.lower() == 'id' and str(col.type).upper() in ['INTEGER', 'INT', 'BIGINT', 'SMALLINT']:
                has_autoincrement_id = True
                id_column = col
                break
        
        logger.info(f"Creando tabla '{table_name_full}' en la base de datos...")
        
        # Si tiene columna id autoincremental, usar SQL raw para crear con IDENTITY
        if has_autoincrement_id:
            logger.info(f"⚙️ Detectada columna ID autoincremental, usando SQL Server IDENTITY")
            
            # Verificar si la tabla ya existe
            with engine.connect() as conn:
                    SELECT COUNT(*) 
                    FROM INFORMATION_SCHEMA.TABLES 
                    WHERE TABLE_NAME = :table_name
                """)
                result = conn.execute(check_query, {"table_name": table_name_full})
                table_exists = result.scalar() > 0
                
                if table_exists:
                    logger.info(f"✅ Tabla '{table_name_full}' ya existe")
                    return True
                
                # Construir CREATE TABLE con IDENTITY
                column_defs = []
                
                for col in columns:
                    col_name = col.name
                    col_type = str(col.type)
                    
                    # Mapear tipos de SQLAlchemy a SQL Server
                    if 'VARCHAR' in col_type.upper():
                        sql_type = col_type
                    elif 'INTEGER' in col_type.upper() or col_type.upper() == 'INT':
                        sql_type = 'INT'
                    elif 'BIGINT' in col_type.upper():
                        sql_type = 'BIGINT'
                    elif 'SMALLINT' in col_type.upper():
                        sql_type = 'SMALLINT'
                    elif 'BOOLEAN' in col_type.upper():
                        sql_type = 'BIT'
                    elif 'FLOAT' in col_type.upper():
                        sql_type = 'FLOAT'
                    elif 'DECIMAL' in col_type.upper() or 'NUMERIC' in col_type.upper():
                        sql_type = col_type
                    elif 'DATETIME' in col_type.upper():
                        sql_type = 'DATETIME'
                    elif 'DATE' in col_type.upper():
                        sql_type = 'DATE'
                    elif 'TEXT' in col_type.upper():
                        sql_type = 'VARCHAR(MAX)'
                    else:
                        sql_type = 'VARCHAR(255)'  # Default
                    
                    # Construir definición de columna
                    col_def = f"[{col_name}] {sql_type}"
                    
                    # Agregar IDENTITY si es la columna id
                    if col_name.lower() == 'id' and has_autoincrement_id:
                        col_def += " IDENTITY(1,1)"
                    
                    # Agregar PRIMARY KEY
                    if col.primary_key:
                        col_def += " PRIMARY KEY"
                    
                    # Agregar NOT NULL si es requerido
                    if not col.nullable and not col.primary_key:
                        col_def += " NOT NULL"
                    
                    # Agregar DEFAULT si existe
                    if col.default is not None and not col.primary_key:
                        default_value = col.default.arg
                        if isinstance(default_value, bool):
                            col_def += f" DEFAULT {1 if default_value else 0}"
                        elif isinstance(default_value, (int, float)):
                            col_def += f" DEFAULT {default_value}"
                        elif isinstance(default_value, str):
                            col_def += f" DEFAULT '{default_value}'"
                    
                    column_defs.append(col_def)
                
                # Crear la tabla
                create_table_sql = f"""
                CREATE TABLE {table_name_full} (
                    {', '.join(column_defs)}
                )
                """
                
                logger.debug(f"SQL de creación: {create_table_sql}")
                conn.commit()
                
                logger.info(f"✅ Tabla '{table_name_full}' creada exitosamente con IDENTITY")
        else:
            # Si NO tiene id autoincremental, usar método normal de SQLAlchemy
            logger.info(f"⚙️ Usando SQLAlchemy para crear tabla (sin IDENTITY)")
            model_class.__table__.create(bind=engine, checkfirst=True)
            logger.info(f"✅ Tabla '{table_name_full}' creada exitosamente")
        
        return True
        
    except Exception as e:
        logger.error(f"Error al crear tabla en la BD: {str(e)}")
        raise


@router.get("/backups/statistics")
async def get_backup_stats(
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Obtiene estadísticas de los backups del sistema
    """
    try:
        stats = get_backup_statistics()
        return {
            "status": "success",
            "statistics": stats
        }
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de backups: {str(e)}")
        return {"error": "Error al obtener estadísticas de backups"}

@router.post("/backups/cleanup")
async def cleanup_backups(
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    """
    Ejecuta limpieza manual de backups antiguos
    """
    try:
        # Log de la operación para auditoría
        logger.info(f"Usuario {user_data['user']['usuario']} ejecutando limpieza de backups")
        
        result = cleanup_old_backups()
        
        return {
            "status": "success",
            "message": "Limpieza de backups completada",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de backups: {str(e)}")
        return {"error": f"Error en la limpieza: {str(e)}"}

@router.post("/generate")
async def generate(
    request: Request,
    user_data: dict = Depends(require_auth_for_template),
    _rl: bool = Depends(rate_limit_dependency(limit=6, window_seconds=60))
) -> Dict[str, Any]:
    """
    Endpoint principal para generar componentes de la aplicación.
    Requiere autenticación y valida los datos de entrada con seguridad mejorada.
    
    Args:
        request: Request con form data (module_name, field_names, field_types, opciones)
        
    Returns:
        Diccionario con resultado de la generación
        
    Raises:
        HTTPException: Si hay error de validación o generación
    """
    try:
        form_data = await request.form()
        
        # Validación básica de datos requeridos
        if not form_data.get("module_name"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El nombre del módulo es requerido"
            )
            
        module_name = form_data["module_name"].strip()
        field_names = form_data.getlist("field_names[]")
        field_types = form_data.getlist("field_types[]")
        
        # Validaciones usando el sistema de configuración
        valid_module, module_msg = validate_module_name(module_name)
        if not valid_module:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Módulo inválido: {module_msg}"
            )
            
        valid_fields, fields_msg = validate_fields_data(field_names, field_types)
        if not valid_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Campos inválidos: {fields_msg}"
            )
        
        # Log de la operación para auditoría
        logger.info(
            "User initiating module generation",
            extra={
                "user": user_data['user']['usuario'],
                "module": module_name,
                "fields_count": len(field_names)
            }
        )
        
        # Procesar opciones elegidas por el usuario
        generate_crud = form_data.get('generate_crud') == 'true'
        generate_route_opt = form_data.get('generate_route') == 'true'
        generate_schema_opt = form_data.get('generate_schema') == 'true'
        generate_html_form_opt = form_data.get('generate_html_form') == 'true'
        generate_tests_opt = form_data.get('generate_tests') == 'true'
        agregar_rutas = form_data.get('agregar_rutas') == 'true'
        generate_service = form_data.get('generate_service') == 'true'
        
        result_message = "Generación completada exitosamente"
        
        # Si generate_service está marcado, no usamos generate_crud
        if generate_service:
            generate_crud = False
            try:
                success = generate_and_save_service(module_name, field_names, field_types)
                if success:
                    result_message += f". Servicio '{module_name}' generado y registrado."
                else:
                    raise HTTPException(
                        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                        detail=f"Error al generar el servicio '{module_name}'"
                    )
            except HTTPException:
                raise
            except Exception as e:
                logger.error(
                    f"Error generating service {module_name}",
                    extra={"user": user_data['user']['usuario']},
                    exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al generar y guardar el servicio: {str(e)}"
                )
        elif generate_crud:
            try:
                generate_and_save_crud(module_name, field_names, field_types)
                
                # Generación individual según opciones
                if generate_route_opt:
                    generate_and_save_route(module_name, field_names, field_types)
                    if agregar_rutas:
                        add_new_route_to_main(module_name)
                
                if generate_schema_opt:
                    generate_and_save_schema(module_name, field_names, field_types)
                    
                if generate_html_form_opt:
                    html_content = generate_html_form(module_name, field_names, field_types)
                    save_html_form(module_name, html_content)
                    
                if generate_tests_opt:
                    generate_and_save_tests(module_name, field_names, field_types)
                    
            except Exception as e:
                logger.error(
                    f"Error generating CRUD components for {module_name}",
                    extra={"user": user_data['user']['usuario']},
                    exc_info=True
                )
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Error al generar componentes: {str(e)}"
                )
        
        logger.info(
            "Module generation completed successfully",
            extra={
                "user": user_data['user']['usuario'],
                "module": module_name,
                "service_mode": generate_service
            }
        )
        
        return {"message": result_message}
        
    except HTTPException:
        raise
    except ValidationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.critical(
            "Unexpected error in generate endpoint",
            extra={"user": user_data.get('user', {}).get('usuario', 'unknown')},
            exc_info=True
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error inesperado al generar componentes"
        )


def generate_project_route_config(project_name, table_names):
    """
    Genera el archivo route_config a nivel del proyecto que consolida todas las rutas.
    
    Args:
        project_name: Nombre del proyecto
        table_names: Lista de nombres de tablas generadas
    """
    try:
        project_dir = f"Services/{project_name}"
        os.makedirs(project_dir, exist_ok=True)
        
        # Generar imports
        imports = []
        router_includes = []
        
        for table_name in table_names:
            table_name_lower = table_name.lower()
            imports.append(f"from Services.{project_name}.{table_name_lower}.route_{table_name_lower} import router as {table_name_lower}_router")
            # CAMBIO: Agregar prefijo del proyecto a la ruta
            router_includes.append(f'    app.include_router({table_name_lower}_router, prefix="/{project_name}/{table_name_lower}", tags=["{project_name}", "{table_name_lower}"])')
        
        # Generar contenido
        route_config_content = f'''"""
Configuración de rutas para el proyecto {project_name}
Generado automáticamente - Multi-tabla
Rutas base: /{project_name}/{{tabla}}
"""
from fastapi import FastAPI

# Imports de routers de cada tabla
{chr(10).join(imports)}

def configure_{project_name}_routes(app: FastAPI):
    """
    Configura todas las rutas del proyecto {project_name}
    
    Tablas incluidas: {", ".join(table_names)}
    
    Rutas generadas:
{chr(10).join([f"    - /{project_name}/{table.lower()}" for table in table_names])}
    """
{chr(10).join(router_includes)}
    
    return app

# Para facilitar la inclusión en main.py
def register_routes(app: FastAPI):
    """Alias para configure_{project_name}_routes"""
    return configure_{project_name}_routes(app)
'''
        
        # Guardar archivo
        route_config_path = f"{project_dir}/route_config_{project_name}.py"
        with open(route_config_path, 'w', encoding='utf-8') as f:
            f.write(route_config_content)
        
        logger.info(f"✅ route_config generado: {route_config_path}")
        
        # También generar __init__.py a nivel del proyecto
        project_init_content = f'''"""
Proyecto: {project_name}
Tablas: {", ".join(table_names)}
"""
from .route_config_{project_name} import configure_{project_name}_routes, register_routes

__all__ = ['configure_{project_name}_routes', 'register_routes']
'''
        
        with open(f"{project_dir}/__init__.py", 'w', encoding='utf-8') as f:
            f.write(project_init_content)
        
        # Generar README del proyecto
        readme_content = f'''# Proyecto: {project_name}

## Estructura del Proyecto

```
Services/{project_name}/
├── route_config_{project_name}.py  # Configuración centralizada de rutas
├── __init__.py
{chr(10).join([f"├── {table}/" for table in table_names])}
```

## Tablas Generadas

{chr(10).join([f"- **{table}**: Servicio completo con model, schema, service, route, HTML/JS" for table in table_names])}

## Uso en main.py

```python
from Services.{project_name} import register_routes

# En tu aplicación FastAPI
register_routes(app)
```

## Endpoints Generados

{chr(10).join([f"- `/{table}/`: CRUD completo para {table}" for table in table_names])}
{chr(10).join([f"- `/{table}/pagina`: Interfaz HTML para {table}" for table in table_names])}

## Generado automáticamente
Fecha: {time.strftime("%Y-%m-%d %H:%M:%S")}
'''
        
        with open(f"{project_dir}/README.md", 'w', encoding='utf-8') as f:
            f.write(readme_content)
        
        logger.info(f"✅ README generado: {project_dir}/README.md")
        
        return True
        
    except Exception as e:
        logger.error(f"Error generando route_config del proyecto: {str(e)}")
        return False


def generate_multi_table_service(project_name, table_name, field_names, field_types):
    """
    Genera un servicio completo para una tabla dentro de un proyecto multi-tabla.
    Estructura: Services/project_name/table_name/
    
    Args:
        project_name: Nombre del proyecto (ej: gestion_inventario)
        table_name: Nombre de la tabla (ej: productos)
        field_names: Lista de nombres de campos
        field_types: Lista de tipos de campos
        
    Returns:
        True si fue exitoso, False en caso contrario
    """
    try:
        table_name = table_name.lower()
        field_names = [field_name.lower() for field_name in field_names]
        field_types = [field_type.lower() for field_type in field_types]
        
        # Estructura: Services/project_name/table_name/
        table_dir = f"Services/{project_name}/{table_name}"
        os.makedirs(table_dir, exist_ok=True)
        
        logger.info(f"Generando servicio para tabla '{table_name}' en proyecto '{project_name}'")
        
        # 1. Generar modelo (con prefijo del servicio en __tablename__)
        from .Generar_Funciones.Generar_Models_service import generate_model
        model_code = generate_model(table_name, field_names, field_types, service_name=project_name)
        save_file_to_service(f"{table_dir}/model_{table_name}.py", model_code)
        
        # 2. Generar schemas
        from .Generar_Funciones.Generar_Schema_service import generate_schema
        schema_code = generate_schema(table_name, field_names, field_types)
        save_file_to_service(f"{table_dir}/schema_{table_name}.py", schema_code)
        
        # 3. Generar servicio (CRUD con SQL - con prefijo del servicio en queries)
        from .Generar_Funciones.Generar_Cruds_sql import generate_crud_functions
        service_code = generate_crud_functions(table_name, field_names, field_types, service_name=project_name)
        save_file_to_service(f"{table_dir}/service_{table_name}.py", service_code)
        
        # 4. Generar rutas
        from .Generar_Funciones.Generar_Routes_service import generate_route
        route_code = generate_route(table_name, field_names, field_types)
        save_file_to_service(f"{table_dir}/route_{table_name}.py", route_code)
        
        # 5. Generar __init__.py
        table_name_cap = table_name.capitalize()
        init_code = f"""# Servicio {table_name} del proyecto {project_name}
from .model_{table_name} import {table_name_cap}
from .schema_{table_name} import {table_name_cap}Create, {table_name_cap}Update, {table_name_cap}Read
from .service_{table_name} import *
from .route_{table_name} import router

__all__ = [
    '{table_name_cap}',
    '{table_name_cap}Create',
    '{table_name_cap}Update',
    '{table_name_cap}Read',
    'router'
]
"""
        save_file_to_service(f"{table_dir}/__init__.py", init_code)
        
        # 6. Generar HTMLs adaptados a los endpoints del servicio
        # MODIFICADO: Pasar project_name para generar rutas con prefijo
        html_content, js_content = generate_html_for_service(table_name, field_names, field_types, project_name=project_name)
        
        # Guardar HTML dentro de la carpeta del servicio
        html_dir = f"{table_dir}/templates"
        os.makedirs(html_dir, exist_ok=True)
        
        with open(f"{html_dir}/{table_name}.html", 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"HTML generado: {html_dir}/{table_name}.html")
        
        # Guardar JavaScript dentro de la carpeta del servicio
        js_dir = f"{table_dir}/static"
        os.makedirs(js_dir, exist_ok=True)
        
        with open(f"{js_dir}/{table_name}.js", 'w', encoding='utf-8') as f:
            f.write(js_content)
        logger.info(f"JavaScript generado: {js_dir}/{table_name}.js")
        
        # Copiar también a static/ principal para que sea accesible por el navegador
        public_static_dir = f"static/{table_name}"
        os.makedirs(public_static_dir, exist_ok=True)
        public_js_path = f"{public_static_dir}/{table_name}_service.js"
        
        with open(public_js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        logger.info(f"JavaScript público generado: {public_js_path}")
        
        # 7. CREAR LA TABLA EN LA BASE DE DATOS
        try:
            create_table_in_database(project_name, table_name)
            logger.info(f"✅ Tabla '{project_name}_{table_name}' creada en la base de datos")
        except Exception as e:
            logger.warning(f"⚠️ No se pudo crear la tabla en la BD (puede que ya exista): {str(e)}")
        
        logger.info(f"✅ Servicio '{table_name}' generado exitosamente en {table_dir}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error al generar servicio '{table_name}' en proyecto '{project_name}': {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False


def generate_and_save_service(module_name, field_names, field_types):
    """
    Genera y guarda un servicio completo (modelo, schema, crud, rutas).
    Devuelve True si fue exitoso, False en caso contrario.
    """
    module_name = module_name.lower()
    field_names = [field_name.lower() for field_name in field_names]
    field_types = [field_type.lower() for field_type in field_types]

    # Creamos la estructura de directorios si no existe
    service_dir = f"Services/{module_name}"
    os.makedirs(service_dir, exist_ok=True)
    
    # Generar todos los componentes dentro de la carpeta de servicios
    try:
        # 1. Generar y guardar el servicio (CRUD con SQL - con prefijo del servicio en queries)
        from .Generar_Funciones.Generar_Cruds_sql import generate_crud_functions
        service_code = generate_crud_functions(module_name, field_names, field_types, service_name=module_name)
        save_file_to_service(f"{service_dir}/service_{module_name}.py", service_code)
        
        # 2. Generar y guardar las rutas
        from .Generar_Funciones.Generar_Routes_service import generate_route
        route_code = generate_route(module_name, field_names, field_types)
        save_file_to_service(f"{service_dir}/route_{module_name}.py", route_code)
        
        # 3. Generar y guardar los schemas
        from .Generar_Funciones.Generar_Schema_service import generate_schema
        schema_code = generate_schema(module_name, field_names, field_types)
        save_file_to_service(f"{service_dir}/schema_{module_name}.py", schema_code)
        
        # 4. Generar y guardar el modelo (con prefijo del servicio en __tablename__)
        from .Generar_Funciones.Generar_Models_service import generate_model
        model_code = generate_model(module_name, field_names, field_types, service_name=module_name)
        save_file_to_service(f"{service_dir}/model_{module_name}.py", model_code)
        
        # 5. Generar archivo __init__.py para hacer el servicio importable
        module_name_cap = module_name.capitalize()
        init_code = generate_init_file(module_name, module_name_cap)
        save_file_to_service(f"{service_dir}/__init__.py", init_code)
        
        # 6. Generar el archivo HTML y JS para la ruta /pagina
        # Para servicios sin proyecto, no se usa prefijo
        html_content, js_content = generate_html_for_service(module_name, field_names, field_types, project_name=None)
        
        # Crear directorio específico para el módulo dentro de static
        module_dir = f"sql_app/static/{module_name}"
        os.makedirs(module_dir, exist_ok=True)
        
        # Guardar el archivo HTML en la carpeta específica del módulo
        html_path = f"{module_dir}/index.html"
        
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"Archivo HTML {html_path} generado para la ruta /pagina")
        
        # Guardar el archivo JavaScript en la carpeta específica del módulo
        js_path = f"{module_dir}/{module_name}_service.js"
        
        with open(js_path, 'w', encoding='utf-8') as f:
            f.write(js_content)
        logger.info(f"Archivo JavaScript {js_path} generado para complementar la interfaz")
        
        # 7. Generar el archivo route_config para unificar las rutas del servicio
        route_config_content = generate_route_config_file(module_name)
        save_file_to_service(f"{service_dir}/route_config_{module_name}.py", route_config_content)
        
        # 8. Registrar el servicio en el gestor de servicios
        register_service_in_manager(module_name)
        
        logger.info(f"Servicio completo generado exitosamente en {service_dir}")
        return True
    except Exception as e:
        logger.error(f"Error al generar el servicio completo: {str(e)}")
        traceback.print_exc()
        return False

def save_file_to_service(file_path, content):
    """
    Guarda el contenido en el archivo especificado, creando directorios si es necesario.
    Incluye validaciones de seguridad y manejo robusto de errores.
    """
    try:
        # Validar que el contenido no esté vacío
        if not content or not content.strip():
            logger.error(f"Contenido vacío para archivo {file_path}")
            return False
            
        # Sanitizar la ruta para prevenir ataques de directory traversal
        file_path = sanitize_path(file_path)
        if not file_path:
            logger.error(f"Ruta de archivo inválida después de sanitización")
            return False
        
        # Asegurar que exista el directorio
        dir_path = os.path.dirname(file_path)
        os.makedirs(dir_path, exist_ok=True)
        
        # Verificar permisos de escritura
        if os.path.exists(file_path) and not os.access(file_path, os.W_OK):
            logger.error(f"Sin permisos de escritura para {file_path}")
            return False
            
        # Crear backup si el archivo ya existe
        if os.path.exists(file_path):
            backup_path = f"{file_path}.backup"
            import shutil
            shutil.copy2(file_path, backup_path)
            logger.info(f"Backup creado: {backup_path}")
        
        # Escribir el archivo
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Archivo {file_path} guardado exitosamente")
        return True
        
    except PermissionError as e:
        logger.error(f"Sin permisos para escribir el archivo {file_path}: {str(e)}")
        return False
    except OSError as e:
        logger.error(f"Error del sistema al guardar {file_path}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Error inesperado al guardar el archivo {file_path}: {str(e)}")
        return False

def register_service_in_manager(module_name):
    """
    Registra el nuevo servicio en el ServicesManager
    """
    try:
        # Importamos el gestor de servicios
        from routers.config import service_manager
        
        # El ID del servicio según la convención del gestor
        service_id = f"{module_name}.route_{module_name}"
        
        if service_manager.services_manager is None:
            logger.warning("El gestor de servicios no está inicializado")
            return False
            
        # También registrar en ServicesManager para su gestión futura
        services_manager = service_manager.services_manager
        
        # Forzar un nuevo escaneo para detectar el nuevo servicio
        services_manager.scan_services()
        
        # Registrar y activar el servicio
        if service_id not in services_manager.active_services:
            services_manager.active_services[service_id] = True
            
        # Intentar registrar el servicio inmediatamente
        try:
            success = services_manager.register_service(service_id)
            logger.info(f"Servicio {service_id} registro inmediato: {'exitoso' if success else 'fallido'}")
        except Exception as e:
            logger.warning(f"No se pudo registrar inmediatamente el servicio {service_id}: {str(e)}")
            
        # Guardar el estado actualizado
        services_manager.save_state()
        
        logger.info(f"Servicio {service_id} registrado en el gestor de servicios")
        return True
    except Exception as e:
        logger.error(f"Error al registrar el servicio en el gestor: {str(e)}")
        traceback.print_exc()
        return False

def generate_init_file(module_name, module_name_cap):
    """
    Genera el contenido del archivo __init__.py para el servicio
    """
    init_code = f"""# Archivo __init__.py para el servicio {module_name}
# Este archivo permite importar componentes del servicio desde otras partes de la aplicación

from .model_{module_name} import {module_name_cap}
from .schema_{module_name} import {module_name_cap}Create, {module_name_cap}Update, {module_name_cap}Read
from .service_{module_name} import (
    create_{module_name}, 
    get_{module_name}, 
    gets_{module_name},
    update_{module_name},
    delete_{module_name}
)
from .route_{module_name} import router

# Para facilitar la inclusión del router en la aplicación principal
{module_name}_router = router

__all__ = [
    '{module_name_cap}',
    '{module_name_cap}Create',
    '{module_name_cap}Update', 
    '{module_name_cap}Read',
    'create_{module_name}',
    'get_{module_name}',
    'gets_{module_name}',
    'update_{module_name}',
    'delete_{module_name}',
    'router',
    '{module_name}_router'
]
"""
    return init_code

def generate_route_config_file(module_name):
    """
    Genera el contenido del archivo route_config para unificar las rutas del servicio
    """
    module_name_cap = module_name.capitalize()
    
    route_config_content = f"""# Imports de terceros
from fastapi import FastAPI

# Imports del proyecto
from Services.{module_name}.route_{module_name} import router as {module_name}_router

def configure_{module_name}_routes(app: FastAPI):
    \"\"\"
    Configura todas las rutas relacionadas con el módulo de {module_name}
    
    Args:
        app: Instancia de FastAPI donde se registrarán las rutas
    \"\"\"
    # Incluir el router del servicio {module_name}
    app.include_router({module_name}_router, prefix="/{module_name}")
    
    return app
"""
    return route_config_content

def generate_and_save_route(module_name, field_names, field_types):
    """
    Genera y guarda rutas con manejo mejorado de errores.
    """
    try:
        module_name = module_name.lower()
        field_names = [field_name.lower() for field_name in field_names]
        field_types = [field_type.lower() for field_type in field_types]

        route_code = generate_route(module_name, field_names, field_types)

        file_path = f"routers/Maestros/Route_{module_name}.py"

        if os.path.exists(file_path):
            logger.warning(f"El archivo {file_path} ya existe.")
            return False
        else:
            # Asegurar que exista el directorio
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(route_code)
                logger.info(f"Archivo {file_path} creado con éxito.")
                return True
                
    except Exception as e:
        logger.error(f"Error al generar y guardar ruta {module_name}: {e}")
        return False

def generate_and_save_crud(module_name, field_names, field_types):
    """
    Genera y guarda funciones CRUD con manejo mejorado de errores.
    """
    try:
        module_name = module_name.lower()
        field_names = [field_name.lower() for field_name in field_names]
        field_types = [field_type.lower() for field_type in field_types]

        crud_code = generate_crud_functions(module_name, field_names, field_types)

        file_path = f"db/crud/Maestro/Crud_{module_name}.py"

        if os.path.exists(file_path):
            logger.warning(f"El archivo {file_path} ya existe.")
            return False
        else:
            # Asegurar que exista el directorio
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(crud_code)
                logger.info(f"Archivo {file_path} creado con éxito.")
                return True
                
    except Exception as e:
        logger.error(f"Error al generar y guardar CRUD {module_name}: {e}")
        return False

def generate_and_save_schema(module_name, field_names, field_types):
    module_name = module_name.lower()
    field_names = [field_name.lower() for field_name in field_names]
    field_types = [field_type.lower() for field_type in field_types]

    schema_code = generate_schema(module_name, field_names, field_types)

    file_path = f"db/schemas/Maestro/Schema_{module_name}.py"

    if os.path.exists(file_path):
        print(f"El archivo {file_path} ya existe.")
    else:
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(schema_code)
                print(f"Archivo {file_path} creado con éxito.")
        except Exception as e:
            print(f"Error al guardar el archivo {file_path}: {e}")

def generate_and_save_model(module_name, field_names, field_types):
    """
    LEGACY: Función antigua que genera modelos en db/models/
    Mantenida por compatibilidad, pero se recomienda usar generate_multi_table_service
    """
    module_name = module_name.lower()
    field_names = [field_name.lower() for field_name in field_names]
    field_types = [field_type.lower() for field_type in field_types]

    # Usar la versión _service con el module_name como service_name
    from .Generar_Funciones.Generar_Models_service import generate_model
    model_code = generate_model(module_name, field_names, field_types, service_name=module_name)

    file_path = f"db/models/{module_name}.py"

    if os.path.exists(file_path):
        print(f"El archivo {file_path} ya existe.")
    else:
        try:
            with open(file_path, 'w') as file:
                file.write(model_code)
                print(f"Archivo {file_path} creado con éxito.")
        except Exception as e:
            print(f"Error al guardar el archivo {file_path}: {e}")

def save_html_form(module_name, html_content):
    import os
    output_dir = "sql_app/static/html"
    os.makedirs(output_dir, exist_ok=True)  # Crear el directorio si no existe

    file_path = f"{output_dir}/{module_name}.html"

    if os.path.exists(file_path):
        print(f"El archivo {file_path} ya existe.")
    else:
        try:
            with open(file_path, 'w', encoding='utf-8') as file:
                file.write(html_content)
                print(f"Archivo {file_path} creado con éxito.")
        except Exception as e:
            print(f"Error al guardar el archivo {file_path}: {e}")

def generate_and_save_tests(module_name, field_names, field_types):
    module_name = module_name.lower()
    field_names = [field_name.lower() for field_name in field_names]
    field_types = [field_type.lower() for field_type in field_types]

    test_code = generate_tests(module_name, field_names, field_types)

    file_path = f"tests/test_{module_name}.py"

    if os.path.exists(file_path):
        print(f"El archivo {file_path} ya existe.")
    else:
        try:
            with open(file_path, 'w') as file:
                file.write(test_code)
                print(f"Archivo {file_path} creado con éxito.")
        except Exception as e:
            print(f"Error al guardar el archivo {file_path}: {e}")

def add_new_route_to_main(new_route):
    try:
        with fileinput.FileInput('main.py', inplace=False) as file:
            lines = list(file)
        last_maestros_index = None
        for i, line in enumerate(lines):
            if line.strip().startswith('from routers.Maestros import'):
                if f'Route_{new_route}' not in line:



                    lines[i] = line.strip() + f', Route_{new_route}\n'
            if '#Maestros' in line:
                last_maestros_index = i
        if last_maestros_index is not None:
            lines.insert(last_maestros_index + 1, f'app.include_router(Route_{new_route}.router)\n')
        with open('main.py', 'w') as file:
            file.writelines(lines)
    except Exception as e:
        print(f"Error al agregar la nueva ruta al main.py: {e}")


@router.post("/generate-from-editor-visual")
async def generate_from_editor_visual(
    request: Request,
    user_data: dict = Depends(require_auth_for_template),
    _rl: bool = Depends(rate_limit_dependency(limit=4, window_seconds=60))
):
    """
    Endpoint específico para procesar el JSON del Editor Visual.
    Convierte el formato del editor visual al formato esperado por el sistema.
    """
    try:
        # Obtener el JSON del request
        json_data = await request.json()
        
        # Validar que el JSON tiene la estructura esperada del editor visual
        if not json_data.get("service_name") or not json_data.get("tables"):
            return {"error": "Formato JSON inválido. Se requiere 'service_name' y 'tables'"}
        
        service_name = json_data["service_name"].strip().lower()
        tables = json_data.get("tables", [])
        
        if not tables:
            return {"error": "No se encontraron tablas en el JSON"}
        
        logger.info(f"Usuario {user_data['user']['usuario']} generando servicio desde Editor Visual: {service_name}")
        
        # Procesar cada tabla del JSON del editor visual
        services_generated = []
        
        for table in tables:
            table_name = table.get("name", "").strip().lower()
            if not table_name:
                continue
                
            # Extraer campos de la tabla
            fields = table.get("fields", [])
            if not fields:
                logger.warning(f"Tabla {table_name} no tiene campos definidos")
                continue
                
            field_names = []
            field_types = []
            
            for field in fields:
                field_name = field.get("name", "").strip().lower()
                field_type = field.get("type", "string").strip().lower()
                
                if field_name:
                    field_names.append(field_name)
                    # Mapear tipos del editor visual a tipos del sistema
                    mapped_type = map_editor_visual_type_to_system(field_type)
                    field_types.append(mapped_type)
            
            if not field_names:
                logger.warning(f"Tabla {table_name} no tiene campos válidos")
                continue
            
            # Generar el servicio para esta tabla
            try:
                success = generate_and_save_service(table_name, field_names, field_types)
                if success:
                    services_generated.append(table_name)
                    logger.info(f"Servicio generado exitosamente: {table_name}")
                else:
                    logger.error(f"Error al generar servicio: {table_name}")
            except Exception as e:
                logger.error(f"Error al generar servicio {table_name}: {str(e)}")
                continue
        
        if services_generated:
            return {
                "success": True,
                "message": f"Servicios generados exitosamente desde Editor Visual",
                "services_generated": services_generated,
                "total_services": len(services_generated)
            }
        else:
            return {
                "error": "No se pudo generar ningún servicio desde el JSON del Editor Visual"
            }
            
    except Exception as e:
        logger.error(f"Error procesando JSON del Editor Visual: {str(e)}")
        traceback.print_exc()
        return {"error": f"Error procesando el JSON del Editor Visual: {str(e)}"}


def map_editor_visual_type_to_system(editor_type):
    """
    Mapea los tipos de datos del editor visual a los tipos esperados por el sistema.
    """
    type_mapping = {
        "string": "string",
        "text": "string", 
        "varchar": "string",
        "char": "string",
        "int": "integer",
        "integer": "integer",
        "number": "integer",
        "float": "float",
        "decimal": "float",
        "bool": "boolean",
        "boolean": "boolean",
        "date": "date",
        "datetime": "datetime",
        "timestamp": "datetime",
        "time": "time"
    }
    
    return type_mapping.get(editor_type.lower(), "string")


@router.get("/simple-tables", response_class=HTMLResponse)
async def simple_tables(request: Request):
    """
    Devuelve la lista de tablas dinámicas en formato JSON si la petición lo solicita,
    o la página HTML si es una petición de navegador.
    """
    accept = request.headers.get("accept", "")
    # Si la petición espera JSON, devolver JSON
    if "application/json" in accept:
        try:
            tablas = await db_service.list_user_tables()
            return JSONResponse({"status": "success", "tables": tablas})
        except Exception as e:
            return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
    # Si no, devolver la página HTML
    from fastapi import Depends
    from security.auth_middleware import require_auth_for_template
    import os
    user_data = {}
    try:
        user_data = await require_auth_for_template(request)
    except Exception:
        pass
    template_path = "static/html/simple-tables.html"
    if os.path.exists(template_path):
        return templates.TemplateResponse("html/simple-tables.html", {
            "request": request,
            **user_data
        })
    else:
        return HTMLResponse('''
        <html><head><title>Simple Tables</title></head>
        <body>
            <h1>Gestión de Tablas Simples</h1>
            <p>Página en construcción. Crea el archivo <b>static/html/simple-tables.html</b> para personalizar esta vista.</p>
        </body></html>
        ''', status_code=200)

@router.get("/simple-tables", response_class=JSONResponse)
async def simple_tables_api(request: Request):
    """
    Devuelve la lista de tablas dinámicas en formato JSON si la petición lo solicita.
    """
    accept = request.headers.get("accept", "")
    if "application/json" in accept:
        # Aquí deberías obtener la lista real de tablas dinámicas
        # Por ahora, ejemplo simulado:
        tablas = await db_service.list_user_tables()
        return {"status": "success", "tables": tablas}
    # Si no es petición JSON, delega al handler HTML
    # Ya no se usa simple_tables_page, la lógica está fusionada arriba
    return HTMLResponse("Ruta no encontrada", status_code=404)
