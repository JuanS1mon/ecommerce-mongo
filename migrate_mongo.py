import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
import os

async def migrate_db():
    # Conexión local
    local_client = AsyncIOMotorClient('mongodb://localhost:27017')
    local_db = local_client['db_ecomerce']

    # Conexión Azure Cosmos DB
    azure_uri = "mongodb+srv://dbadmin:Pantone123@ecommerce-db.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
    azure_client = AsyncIOMotorClient(azure_uri)
    azure_db = azure_client['db_ecomerce']

    # Obtener todas las colecciones
    collections = await local_db.list_collection_names()
    print(f"Colecciones a migrar: {collections}")

    for coll_name in collections:
        local_coll = local_db[coll_name]
        azure_coll = azure_db[coll_name]

        # Dropear colección en Azure si existe
        await azure_db.drop_collection(coll_name)
        print(f"Colección {coll_name} droppeada en Azure")

        # Contar documentos
        count = await local_coll.count_documents({})
        print(f"Migrando colección {coll_name} con {count} documentos")

        # Migrar documentos en lotes
        batch_size = 100
        cursor = local_coll.find({})
        batch = []
        migrated = 0

        async for doc in cursor:
            batch.append(doc)
            if len(batch) >= batch_size:
                await azure_coll.insert_many(batch)
                migrated += len(batch)
                print(f"Migrados {migrated} documentos en {coll_name}")
                batch = []

        # Insertar el resto
        if batch:
            await azure_coll.insert_many(batch)
            migrated += len(batch)
            print(f"Migrados {migrated} documentos en {coll_name}")

        print(f"Colección {coll_name} migrada completamente")

    print("Migración completada")

if __name__ == "__main__":
    asyncio.run(migrate_db())