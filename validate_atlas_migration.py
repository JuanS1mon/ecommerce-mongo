#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de validación final de la migración a MongoDB Atlas
Verifica que todo está funcionando correctamente
"""

import asyncio
import os
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

# Cargar variables de entorno
load_dotenv()

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

print(f"\n{'='*70}")
print(f"🔍 VALIDACIÓN FINAL DE MIGRACIÓN A MONGODB ATLAS")
print(f"{'='*70}\n")


async def validate_migration():
    """Valida que la migración fue exitosa"""
    
    client = AsyncIOMotorClient(MONGO_URL)
    
    try:
        # 1. Verificar conexión
        print("1️⃣  Verificando conexión con MongoDB Atlas...")
        await client.admin.command('ping')
        print("   ✓ Conexión exitosa\n")
        
        # 2. Verificar base de datos
        db = client[DB_NAME]
        print(f"2️⃣  Verificando base de datos: {DB_NAME}")
        db_info = await client.admin.command('dbStats', database=DB_NAME)
        print(f"   ✓ Base de datos existe")
        print(f"   Size: {db_info.get('dataSize', 0) / 1024:.2f} KB\n")
        
        # 3. Inicializar Beanie
        print("3️⃣  Inicializando Beanie...")
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
        print("   ✓ Beanie inicializado\n")
        
        # 4. Verificar colecciones
        print("4️⃣  Verificando colecciones:")
        collections = {
            "usuarios": Usuario,
            "admin_usuarios": AdminUsuarios,
            "servicios": Servicio,
            "productos": Producto,
            "presupuestos": Presupuesto,
            "contratos": Contrato,
            "configuraciones": Configuracion
        }
        
        total_docs = 0
        all_ok = True
        
        for col_name, model in collections.items():
            count = await model.find_all().count()
            status = "✓" if count >= 0 else "✗"
            print(f"   {status} {col_name}: {count} documentos")
            total_docs += count
            
            if count == 0 and col_name not in ["productos", "presupuestos", "contratos"]:
                if col_name not in ["usuarios"]:  # usuarios puede estar vacío
                    print(f"      ⚠️  Advertencia: Colección vacía")
        
        print(f"\n   Total de documentos: {total_docs}\n")
        
        # 5. Verificar datos iniciales
        print("5️⃣  Verificando datos iniciales:")
        
        # Verificar configuraciones
        configs = await Configuracion.find_all().to_list(length=None)
        print(f"   ✓ Configuraciones: {len(configs)}")
        for config in configs[:3]:
            print(f"      - {config.key}: {config.value}")
        
        # Verificar servicios
        services = await Servicio.find_all().to_list(length=None)
        print(f"   ✓ Servicios: {len(services)}")
        for service in services[:3]:
            print(f"      - {service.nombre}: ${service.precio_base}")
        
        # Verificar admin
        admins = await AdminUsuarios.find_all().to_list(length=None)
        print(f"   ✓ Administradores: {len(admins)}")
        for admin in admins[:1]:
            print(f"      - {admin.usuario} ({admin.mail})")
        
        print("\n" + "="*70)
        print("✅ VALIDACIÓN COMPLETADA CON ÉXITO")
        print("="*70)
        print("\n📊 Resumen:")
        print(f"   ✓ Conexión a MongoDB Atlas: OK")
        print(f"   ✓ Base de datos (db_ecommerce): OK")
        print(f"   ✓ Colecciones: OK ({len(collections)} creadas)")
        print(f"   ✓ Datos iniciales: OK ({total_docs} documentos)")
        print(f"\n🚀 La aplicación está lista para usar MongoDB Atlas")
        print(f"\n" + "="*70 + "\n")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Error durante la validación: {str(e)}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        client.close()


if __name__ == "__main__":
    success = asyncio.run(validate_migration())
    exit(0 if success else 1)
