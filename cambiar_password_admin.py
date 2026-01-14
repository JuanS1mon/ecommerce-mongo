"""
Script para cambiar la contraseña del usuario admin@sysneg.com en el servidor remoto (puerto 8000)
"""
import asyncio
import bcrypt
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios


async def main():
    # Conectar a MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    
    # Inicializar Beanie
    await init_beanie(
        database=client.db_ecomerce,
        document_models=[AdminUsuarios]
    )
    
    # Buscar usuario
    usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == "admin@sysneg.com")
    
    if not usuario:
        print("❌ Usuario no encontrado")
        return
    
    print(f"✅ Usuario encontrado: {usuario.mail}")
    print(f"   Hash actual: {usuario.clave_hash[:50]}...")
    
    # Nueva contraseña
    nueva_password = "nuevapassword123"
    
    # Generar nuevo hash
    nuevo_hash = bcrypt.hashpw(nueva_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # Actualizar
    usuario.clave_hash = nuevo_hash
    await usuario.save()
    
    print(f"\n🔄 Contraseña actualizada")
    print(f"   Nueva password: {nueva_password}")
    print(f"   Nuevo hash: {nuevo_hash[:50]}...")
    print(f"\n✅ Cambio completado")
    print(f"\n📝 Ahora intenta hacer login en el servidor 8001 con:")
    print(f"   Username: admin")
    print(f"   Password: {nueva_password}")


if __name__ == "__main__":
    asyncio.run(main())
