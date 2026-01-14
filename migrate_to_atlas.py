#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Script de migración de MongoDB local a MongoDB Atlas (Vercel)
Este script copia todos los documentos de la base de datos local
a la base de datos remota en MongoDB Atlas.
"""

import asyncio
import os
import sys
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración de conexiones
LOCAL_MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
LOCAL_DB_NAME = os.getenv("MONGO_DB_NAME", "db_sysne")

# MongoDB Atlas (Vercel)
ATLAS_MONGO_URL = "mongodb+srv://Vercel-Admin-db_sysne:lhAv2Av7NrwGxv6l@db-sysne.neh4dci.mongodb.net/?retryWrites=true&w=majority"
ATLAS_DB_NAME = "db_ecommerce"

print(f"📦 CONFIGURACIÓN DE MIGRACIÓN")
print(f"=" * 60)
print(f"Origen:  {LOCAL_MONGO_URL}")
print(f"Base:    {LOCAL_DB_NAME}")
print(f"Destino: {ATLAS_MONGO_URL[:80]}...")
print(f"Base:    {ATLAS_DB_NAME}")
print(f"=" * 60)


async def migrate_database():
    """Migra todas las colecciones de la base de datos local a Atlas"""
    
    # Conexiones
    local_client = AsyncIOMotorClient(LOCAL_MONGO_URL)
    atlas_client = AsyncIOMotorClient(ATLAS_MONGO_URL)
    
    try:
        # Verificar conexiones
        print("\n🔗 Verificando conexiones...")
        await local_client.admin.command('ping')
        print("✓ Conexión local OK")
        
        await atlas_client.admin.command('ping')
        print("✓ Conexión Atlas OK")
        
        # Obtener bases de datos
        local_db = local_client[LOCAL_DB_NAME]
        atlas_db = atlas_client[ATLAS_DB_NAME]
        
        # Obtener nombres de colecciones locales
        collections = await local_db.list_collection_names()
        
        if not collections:
            print("\n⚠️  No hay colecciones en la base de datos local")
            return
        
        print(f"\n📋 Colecciones encontradas: {len(collections)}")
        for col in collections:
            print(f"   - {col}")
        
        # Migrar cada colección
        print(f"\n🚀 Iniciando migración...")
        total_docs = 0
        
        for collection_name in collections:
            local_collection = local_db[collection_name]
            atlas_collection = atlas_db[collection_name]
            
            # Contar documentos
            count = await local_collection.count_documents({})
            
            if count == 0:
                print(f"\n  ⊘ {collection_name}: 0 documentos (saltando)")
                continue
            
            print(f"\n  📝 {collection_name}: {count} documentos")
            
            # Obtener todos los documentos
            cursor = local_collection.find({})
            documents = await cursor.to_list(length=count)
            
            if documents:
                # Eliminar los IDs para que MongoDB genere nuevos (opcional)
                # o mantenerlos si quieres preservar las referencias
                # for doc in documents:
                #     del doc['_id']
                
                # Insertar en Atlas
                result = await atlas_collection.insert_many(documents)
                print(f"     ✓ {len(result.inserted_ids)} documentos insertados")
                total_docs += len(result.inserted_ids)
        
        print(f"\n{'='*60}")
        print(f"✅ MIGRACIÓN COMPLETADA")
        print(f"Total de documentos migrados: {total_docs}")
        print(f"{'='*60}")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {str(e)}")
        sys.exit(1)
        
    finally:
        # Cerrar conexiones
        local_client.close()
        atlas_client.close()
        print("\n🔌 Conexiones cerradas")


async def verify_migration():
    """Verifica que la migración fue exitosa"""
    print(f"\n🔍 Verificando migración...")
    
    atlas_client = AsyncIOMotorClient(ATLAS_MONGO_URL)
    
    try:
        atlas_db = atlas_client[ATLAS_DB_NAME]
        collections = await atlas_db.list_collection_names()
        
        print(f"\n📊 Colecciones en Atlas ({ATLAS_DB_NAME}):")
        total = 0
        
        for col in collections:
            count = await atlas_db[col].count_documents({})
            total += count
            print(f"   - {col}: {count} documentos")
        
        print(f"\nTotal en Atlas: {total} documentos")
        
    finally:
        atlas_client.close()


if __name__ == "__main__":
    print("\n🔄 Ejecutando migración a MongoDB Atlas...\n")
    
    # Ejecutar migración
    asyncio.run(migrate_database())
    
    # Verificar resultados
    asyncio.run(verify_migration())
    
    print("\n✨ ¡Proceso completado!")
