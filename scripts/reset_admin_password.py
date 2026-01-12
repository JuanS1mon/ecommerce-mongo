"""
Script para resetear la contraseña del admin
"""
import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document
from pydantic import Field, EmailStr
from datetime import datetime
from typing import Optional, Any
from passlib.context import CryptContext

# Configurar bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def encriptar_clave(clave: str) -> str:
    """Encripta contraseña usando bcrypt"""
    if not clave:
        raise ValueError("La contraseña no puede estar vacía")
    clave_bytes = clave.encode('utf-8')
    if len(clave_bytes) > 72:
        clave = clave_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(clave)

# Definir modelo AdminUsuarios
class AdminUsuarios(Document):
    usuario: str
    nombre: str
    mail: EmailStr
    clave_hash: str
    activo: bool = Field(default=True)
    imagen_perfil: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "admin_usuarios"

async def reset_admin_password():
    """Resetea la contraseña del usuario admin"""
    print("🔐 Reseteando contraseña del admin...")

    # Conectar a la base de datos
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("MONGO_DB_NAME", "db_sysne")
    client = AsyncIOMotorClient(MONGO_URL)
    db = client[DB_NAME]

    # Inicializar Beanie
    await init_beanie(database=db, document_models=[AdminUsuarios])

    # Buscar usuario admin
    admin_user = await AdminUsuarios.find_one(AdminUsuarios.mail == "juan@admin.com")
    if not admin_user:
        print("❌ Usuario admin no encontrado. Creando uno nuevo...")
        # Crear usuario admin
        password_hash = encriptar_clave("qwe123")
        admin_user = AdminUsuarios(
            usuario="juan",
            nombre="Juan Admin",
            mail="juan@admin.com",
            clave_hash=password_hash,
            activo=True
        )
        await admin_user.insert()
        print("✅ Usuario admin creado: juan@admin.com / qwe123")
    else:
        # Resetear contraseña
        password_hash = encriptar_clave("qwe123")
        admin_user.clave_hash = password_hash
        admin_user.updated_at = datetime.utcnow()
        await admin_user.save()
        print("✅ Contraseña del admin reseteada: juan@admin.com / qwe123")

    print("🎉 Proceso completado!")

if __name__ == "__main__":
    asyncio.run(reset_admin_password())