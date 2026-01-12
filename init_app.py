"""
Initialization utilities for the application
"""
import os
import logging
from typing import Callable

logger = logging.getLogger(__name__)

def create_all_tables(create_tables_func: Callable, logger: logging.Logger):
    """
    Create all database tables - placeholder for MongoDB/Beanie
    Since Beanie handles collections automatically, this is a no-op
    """
    logger.info("[OK] MongoDB collections will be created automatically by Beanie")
    return True

def ensure_directories():
    """
    Ensure necessary directories exist
    """
    directories = [
        "static/uploads",
        "static/img",
        "logs",
        "temp"
    ]

    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"[OK] Created directory: {directory}")
            else:
                logger.debug(f"Directory already exists: {directory}")
        except OSError as e:
            if e.errno == 30:  # Read-only file system
                logger.warning(f"[WARN] Cannot create directory {directory} on read-only file system: {e}")
            else:
                logger.error(f"[ERROR] Failed to create directory {directory}: {e}")

async def create_admin_user():
    from models.models_beanie import Usuario
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    # Crear admin principal
    admin = await Usuario.find_one(Usuario.username == "admin")
    if not admin:
        hashed_password = pwd_context.hash("admin123")
        admin = Usuario(
            username="admin",
            email="admin@sysne.com",
            hashed_password=hashed_password,
            role="admin",
            is_active=True
        )
        await admin.insert()
        logger.info("[OK] Usuario admin creado")
    else:
        logger.info("[OK] Usuario admin ya existe")
    
    # Crear admin2
    admin2 = await Usuario.find_one(Usuario.username == "admin2")
    if not admin2:
        hashed_password = pwd_context.hash("admin123")
        admin2 = Usuario(
            username="admin2",
            email="admin2@sysne.com",
            hashed_password=hashed_password,
            role="admin",
            is_active=True
        )
        await admin2.insert()
        logger.info("[OK] Usuario admin2 creado")
    else:
        logger.info("[OK] Usuario admin2 ya existe")
