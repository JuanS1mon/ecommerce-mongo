# Imports de bibliotecas estándar
from dotenv import dotenv_values
import json
import logging

# Imports de terceros
from fastapi import APIRouter, Body, Depends, FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates

# Imports del proyecto
from security.security import get_current_user

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="static")

router = APIRouter(
    include_in_schema=False,  # Oculta todas las rutas de este router en la documentación
    prefix="/configdb",
    tags=["configdb"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "ruta no encontrada"}}
)

# Ruta existente
@router.get("/")
async def configdb(request: Request, current_user: dict = Depends(get_current_user)):
    env_values = get_env_values()
    # Pasar los valores a la plantilla
    return templates.TemplateResponse("html/configdb.html", {"request": request, "env_values": env_values, "current_user": current_user})

# Nueva ruta para actualizar variables de entorno individualmente
@router.put("/env/{key}", include_in_schema=False)
async def update_env_value(
    key: str,
    data: dict = Body(...),
    current_user: dict = Depends(get_current_user)
):
    try:
        # Verificar que el usuario tiene permisos (podrías añadir verificación adicional aquí)
        if not current_user:
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "No tienes permisos para modificar la configuración"}
            )
        
        # Verificar que la clave existe en las variables de entorno permitidas
        allowed_keys = [
            "DB_USER", "DB_PASSWORD", "DB_HOST", "DB_NAME", "DB_DRIVER",
            "POOL_SIZE", "MAX_OVERFLOW", "POOL_TIMEOUT", "POOL_PRE_PING", "POOL_RECYCLE"
        ]
        
        if key not in allowed_keys:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": f"La variable {key} no está permitida para modificación"}
            )
        
        # Obtiene el nuevo valor
        value = data.get("value")
        if value is None:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"detail": "Debe proporcionar un valor para actualizar"}
            )
        
        # Actualizar la variable específica en el archivo .env
        success = update_single_env_value(key, value)
        
        if not success:
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": f"No se pudo actualizar la variable {key}"}
            )
        
        logger.info(f"Variable {key} actualizada correctamente a {value}")
        return {"key": key, "value": value, "updated": True}
        
    except Exception as e:
        logger.error(f"Error al actualizar variable de entorno {key}: {str(e)}")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": f"Error al actualizar: {str(e)}"}
        )

def get_env_values():
    env_values = dotenv_values()
    return env_values

def update_single_env_value(key, new_value):
    try:
        with open('.env', 'r') as file:
            lines = file.readlines()

        updated_lines = []
        key_found = False
        
        for line in lines:
            if '=' in line:
                line_key, line_value = line.strip().split('=', 1)
                if line_key == key:
                    updated_lines.append(f'{key}={new_value}\n')
                    key_found = True
                else:
                    updated_lines.append(line)
            else:
                updated_lines.append(line)
        
        # Si la clave no existe, añadirla al final
        if not key_found:
            updated_lines.append(f'{key}={new_value}\n')
        
        with open('.env', 'w') as file:
            file.writelines(updated_lines)
        
        return True
    except Exception as e:
        logger.error(f"Error actualizando variable {key} en .env: {str(e)}")
        return False

def update_env_values(data):
    try:
        with open('.env', 'r') as file:
            lines = file.readlines()

        updated_lines = []
        for line in lines:
            if '=' in line:
                key, value = line.strip().split('=', 1)
                if key in data:
                    value = data[key]
                updated_lines.append(f'{key}={value}\n')
            else:
                updated_lines.append(line)

        with open('.env', 'w') as file:
            file.writelines(updated_lines)
        return True
    except Exception as e:
        logger.error(f"Error actualizando .env: {str(e)}")
        return False
