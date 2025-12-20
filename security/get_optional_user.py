"""
Funciones de autenticación opcional para casos donde el usuario puede o no estar autenticado
"""

from fastapi import Request, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import os
import logging

# Configurar logging
logger = logging.getLogger("security")

# Obtener configuración
SECRET = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = os.getenv("ALGORITHM", "HS256")

# Local UserDB for compatibility
from pydantic import BaseModel, EmailStr
from typing import Optional

class UserDB(BaseModel):
    id: Optional[str] = None
    nombre: str
    apellido: str
    email: EmailStr
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    provincia: Optional[str] = None
    pais: Optional[str] = None
    active: bool = True
    roles: Optional[list] = None

# Import Beanie model
from Projects.ecomerce.models.usuarios import EcomerceUsuarios

security = HTTPBearer(auto_error=False)

async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """
    Obtiene el usuario actual de forma opcional, sin lanzar excepciones si no está autenticado

    Args:
        credentials: Credenciales del header Authorization

    Returns:
        UserDB | None: Objeto de usuario autenticado o None si no está autenticado
    """
    try:
        if not credentials or not credentials.credentials:
            logger.info("No hay token disponible para autenticación opcional")
            return None

        token = credentials.credentials

        # Decodificar token
        try:
            payload = jwt.decode(token, SECRET, algorithms=[ALGORITHM])
            email: str = payload.get("sub")

            if not email:
                logger.info("Token no contiene email válido")
                return None

            # Obtener usuario de MongoDB usando Beanie
            user = await EcomerceUsuarios.find_one(
                EcomerceUsuarios.email == email,
                EcomerceUsuarios.active == True
            )

            if not user:
                logger.info(f"Usuario no encontrado en la base de datos: {email}")
                return None

            # Convertir a UserDB
            user_db = UserDB(
                id=str(user.id),
                nombre=user.nombre,
                apellido=user.apellido,
                email=user.email,
                telefono=user.telefono,
                direccion=user.direccion,
                ciudad=user.ciudad,
                provincia=user.provincia,
                pais=user.pais,
                active=user.active,
                roles=user.roles or []
            )

            logger.debug(f"Usuario autenticado opcionalmente: {email}")
            return user_db

        except JWTError as e:
            logger.info(f"Token JWT inválido en autenticación opcional: {str(e)}")
            return None

    except Exception as e:
        logger.error(f"Error en autenticación opcional: {str(e)}")
        return None
