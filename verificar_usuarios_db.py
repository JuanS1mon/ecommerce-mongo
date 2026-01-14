"""
Script para verificar usuarios en la base de datos
"""
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import os
import sys

# Configurar path
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
    
    print("=" * 80)
    print("VERIFICACIÓN DE USUARIOS EN BASE DE DATOS")
    print("=" * 80)
    
    # Buscar todos los usuarios
    todos = await AdminUsuarios.find_all().to_list()
    print(f"\n📊 Total de usuarios en la base de datos: {len(todos)}")
    
    if todos:
        print("\n" + "=" * 80)
        print("LISTADO DE USUARIOS:")
        print("=" * 80)
        for idx, user in enumerate(todos, 1):
            print(f"\n{idx}. Email: {user.mail}")
            print(f"   Username: {user.usuario}")
            print(f"   Nombre: {user.nombre}")
            print(f"   Activo: {user.activo}")
            print(f"   Proyectos: {user.proyectos if hasattr(user, 'proyectos') else 'N/A'}")
            print(f"   Proyecto Nombre: {user.proyecto_nombre if hasattr(user, 'proyecto_nombre') else 'N/A'}")
            print(f"   Fecha Vencimiento: {user.fecha_vencimiento if hasattr(user, 'fecha_vencimiento') else 'N/A'}")
    
    # Buscar usuarios específicos
    print("\n" + "=" * 80)
    print("BÚSQUEDA DE USUARIOS SINCRONIZADOS:")
    print("=" * 80)
    
    admin_user = await AdminUsuarios.find_one(AdminUsuarios.mail == "admin@sysneg.com")
    if admin_user:
        print(f"\n✅ Usuario admin@sysneg.com encontrado:")
        print(f"   ID: {admin_user.id}")
        print(f"   Username: {admin_user.usuario}")
        print(f"   Activo: {admin_user.activo}")
        print(f"   Proyectos: {admin_user.proyectos if hasattr(admin_user, 'proyectos') else 'N/A'}")
    else:
        print(f"\n❌ Usuario admin@sysneg.com NO encontrado")
    
    fjuan_user = await AdminUsuarios.find_one(AdminUsuarios.mail == "fjuansimon@gmail.com")
    if fjuan_user:
        print(f"\n✅ Usuario fjuansimon@gmail.com encontrado:")
        print(f"   ID: {fjuan_user.id}")
        print(f"   Username: {fjuan_user.usuario}")
        print(f"   Activo: {fjuan_user.activo}")
        print(f"   Proyectos: {fjuan_user.proyectos if hasattr(fjuan_user, 'proyectos') else 'N/A'}")
    else:
        print(f"\n❌ Usuario fjuansimon@gmail.com NO encontrado")
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
