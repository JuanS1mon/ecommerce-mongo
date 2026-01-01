#!/usr/bin/env python3
"""
Migrar datos de MongoDB local a Azure Cosmos DB
"""

import asyncio
from motor.motor_asyncio import AsyncIOMotorClient

# Conexión local
LOCAL_URI = "mongodb://localhost:27017"
# Azure Cosmos DB
AZURE_URI = "mongodb+srv://dbadmin:Pantone123@ecommerce-db.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
DB_NAME = "db_ecomerce"

async def migrate():
    print("🔄 Iniciando migración de datos...")
    
    # Conectar a MongoDB local
    local_client = AsyncIOMotorClient(LOCAL_URI)
    local_db = local_client[DB_NAME]
    
    # Conectar a Azure Cosmos DB con timeouts aumentados
    azure_client = AsyncIOMotorClient(
        AZURE_URI,
        serverSelectionTimeoutMS=30000,
        connectTimeoutMS=30000,
        socketTimeoutMS=30000,
        retryWrites=False
    )
    azure_db = azure_client[DB_NAME]
    
    try:
        # Obtener lista de colecciones locales
        collections = await local_db.list_collection_names()
        print(f"📦 Colecciones encontradas: {collections}")
        
        for collection_name in collections:
            if collection_name.startswith("system."):
                continue
            
            local_collection = local_db[collection_name]
            azure_collection = azure_db[collection_name]
            
            # Contar documentos
            count = await local_collection.count_documents({})
            print(f"\n📄 {collection_name}: {count} documentos")
            
            if count == 0:
                print(f"   ⏭️ Saltando colección vacía")
                continue
            
            # Obtener todos los documentos
            documents = await local_collection.find({}).to_list(None)
            
            # Insertar en Azure con upsert para manejar duplicados
            for doc in documents:
                try:
                    # Intentar insertar, si falla por duplicado, actualizar
                    await azure_collection.replace_one(
                        {'_id': doc['_id']}, 
                        doc, 
                        upsert=True
                    )
                except Exception as e:
                    print(f"   ⚠️ Error con documento {doc.get('_id', 'sin_id')}: {e}")
                    continue
            
            print(f"   ✅ {len(documents)} documentos procesados")
        
        print("\n✨ Migración completada exitosamente")
        
    except Exception as e:
        print(f"\n❌ Error durante la migración: {e}")
    finally:
        local_client.close()
        azure_client.close()

if __name__ == "__main__":
    asyncio.run(migrate())
