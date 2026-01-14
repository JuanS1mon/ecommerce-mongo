"""
Verificar usuarios duplicados con admin@sysneg.com
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios


async def main():
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    
    await init_beanie(
        database=client.db_ecomerce,
        document_models=[AdminUsuarios]
    )
    
    # Buscar TODOS los usuarios con este email
    usuarios = await AdminUsuarios.find(AdminUsuarios.mail == "admin@sysneg.com").to_list()
    
    print(f"📊 Total usuarios con admin@sysneg.com: {len(usuarios)}")
    print("=" * 80)
    
    for idx, u in enumerate(usuarios, 1):
        print(f"\n{idx}. ID: {u.id}")
        print(f"   Email: {u.mail}")
        print(f"   Username: {u.usuario}")
        print(f"   Nombre: {u.nombre}")
        print(f"   Activo: {u.activo}")
        print(f"   Proyecto: {u.proyecto_nombre}")
        print(f"   Hash: {u.clave_hash[:50]}...")


if __name__ == "__main__":
    asyncio.run(main())
