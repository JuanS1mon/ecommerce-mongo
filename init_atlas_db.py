#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script para inicializar la base de datos en MongoDB Atlas con Beanie
"""

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Cargar variables de entorno
load_dotenv()

# Importar modelos
from models.models_beanie import (
    Usuario,
    AdminUsuarios,
    Servicio,
    Producto,
    Presupuesto,
    Contrato,
    Configuracion
)

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("MONGO_DB_NAME")

print(f"🗄️  INICIALIZANDO BASE DE DATOS EN ATLAS")
print(f"=" * 70)
print(f"URL: {MONGO_URL[:80]}...")
print(f"BD:  {DB_NAME}")
print(f"=" * 70)


async def init_database():
    """Inicializa la base de datos con Beanie"""
    
    client = AsyncIOMotorClient(MONGO_URL)
    
    try:
        # Verificar conexión
        print("\n🔗 Verificando conexión con Atlas...")
        await client.admin.command('ping')
        print("✓ Conexión exitosa")
        
        # Obtener base de datos
        db = client[DB_NAME]
        
        # Inicializar Beanie con todos los modelos
        print("\n📦 Inicializando Beanie con modelos...")
        await init_beanie(
            database=db,
            document_models=[
                Usuario,
                AdminUsuarios,
                Servicio,
                Producto,
                Presupuesto,
                Contrato,
                Configuracion
            ]
        )
        print("✓ Beanie inicializado")
        
        # Listar colecciones
        print("\n📋 Colecciones creadas:")
        collections = await db.list_collection_names()
        for col in collections:
            count = await db[col].count_documents({})
            print(f"   - {col}: {count} documentos")
        
        # Crear datos iniciales si es necesario
        print("\n📝 Verificando datos iniciales...")
        
        # Verificar si hay configuraciones
        config_count = await Configuracion.find_all().count()
        if config_count == 0:
            print("   Creando configuraciones iniciales...")
            initial_configs = [
                Configuracion(key="site_name", value="Sysne Ecommerce"),
                Configuracion(key="site_description", value="Plataforma de ecommerce inteligente"),
                Configuracion(key="currency", value="ARS"),
            ]
            await Configuracion.insert_many(initial_configs)
            print(f"   ✓ {len(initial_configs)} configuraciones creadas")
        
        # Verificar si hay servicios
        service_count = await Servicio.find_all().count()
        if service_count == 0:
            print("   Creando servicios iniciales...")
            initial_services = [
                Servicio(
                    nombre="Desarrollo Web",
                    descripcion="Creación de sitios web modernos",
                    tipo_servicio="creación web",
                    precio_base=5000
                ),
                Servicio(
                    nombre="Ecommerce",
                    descripcion="Plataforma de venta online",
                    tipo_servicio="ecommerce",
                    precio_base=10000
                ),
                Servicio(
                    nombre="Consultoría IA",
                    descripcion="Consultoría en inteligencia artificial",
                    tipo_servicio="consultoría",
                    precio_base=2000
                ),
            ]
            await Servicio.insert_many(initial_services)
            print(f"   ✓ {len(initial_services)} servicios creados")
        
        # Verificar si hay admin
        admin_count = await AdminUsuarios.find_all().count()
        if admin_count == 0:
            print("   Creando usuario administrador...")
            from passlib.context import CryptContext
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            admin = AdminUsuarios(
                usuario="admin",
                nombre="Administrador",
                mail="fjuansimon@gmail.com",
                clave_hash=pwd_context.hash("admin123"),
                activo=True
            )
            await admin.insert()
            print(f"   ✓ Usuario admin creado")
        
        print(f"\n{'='*70}")
        print(f"✅ BASE DE DATOS INICIALIZADA")
        print(f"{'='*70}")
        
    except Exception as e:
        print(f"\n❌ Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        client.close()
        print("\n🔌 Conexión cerrada")
    
    return True


if __name__ == "__main__":
    success = asyncio.run(init_database())
    exit(0 if success else 1)
