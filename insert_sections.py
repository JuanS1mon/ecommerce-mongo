import asyncio
import os
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from models.models_beanie import Configuracion

async def insert_index_sections():
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("MONGO_DB_NAME", "db_sysne")
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    await init_beanie(database=database, document_models=[Configuracion])

    index_sections = {
        "hero": {
            "titulo": "Transformamos datos en decisiones inteligentes.",
            "subtitulo": "En sysne, ayudamos a las empresas a potenciar su crecimiento mediante soluciones digitales impulsadas por inteligencia artificial. Desde la automatización hasta la analítica avanzada, convertimos tus datos en estrategias que generan resultados reales.",
            "imagen": "/static/img/logo.png",
            "contenido": ""
        },
        "servicios": {
            "titulo": "⚙️ Servicios",
            "subtitulo": "Ofrecemos soluciones tecnológicas avanzadas para impulsar tu negocio.",
            "imagen": "",
            "contenido": ""
        }
    }

    import json
    config = Configuracion(key="index_sections", value=json.dumps(index_sections, ensure_ascii=False))
    await config.insert()
    print("Inserted index_sections")

asyncio.run(insert_index_sections())
