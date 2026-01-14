"""
Eliminar usuario admin@sysneg.com para probar sincronización automática
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto


async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    
    await init_beanie(
        database=client.db_ecomerce,
        document_models=[AdminUsuarios, Proyecto, UsuarioProyecto]
    )
    
    # Buscar usuario
    usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == "admin@sysneg.com")
    
    if not usuario:
        print("❌ Usuario no encontrado")
        return
    
    print(f"✅ Usuario encontrado: {usuario.mail}")
    print(f"   ID: {usuario.id}")
    
    # Eliminar vinculaciones
    vinculaciones = await UsuarioProyecto.find(UsuarioProyecto.usuario_id == usuario.id).to_list()
    for vinc in vinculaciones:
        await vinc.delete()
        print(f"   🗑️  Vinculación eliminada")
    
    # Eliminar usuario
    await usuario.delete()
    print(f"✅ Usuario eliminado")
    print(f"\n📝 Ahora intenta hacer login con:")
    print(f"   Username: admin@sysneg.com")
    print(f"   Password: admin123")
    print(f"\nEl sistema debería sincronizar automáticamente el usuario desde el servidor remoto")


if __name__ == "__main__":
    asyncio.run(main())
