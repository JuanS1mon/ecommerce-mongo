#!/usr/bin/env python3
"""
Versión simplificada de main.py para debugging de rutas de producto
"""
import sys
import os
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import Response
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Crear app FastAPI
app = FastAPI()

# Configurar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configurar templates
templates = Jinja2Templates(directory="templates")

@app.get("/ecomerce/productos/{producto_id}")
async def producto_detail_page(request: Request, producto_id: str):
    """Servir la página de detalle de producto"""
    logger.info(f"Accediendo a producto: {producto_id}")

    try:
        # Fetch product from database
        from bson import ObjectId
        from motor.motor_asyncio import AsyncIOMotorClient

        logger.info(f"Conectando a base de datos para producto: {producto_id}")
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.db_sysne

        producto = await db.productos.find_one({"_id": ObjectId(producto_id)})
        if not producto:
            logger.warning(f"Producto no encontrado: {producto_id}")
            return Response(status_code=404, content="Producto no encontrado")

        logger.info(f"Producto encontrado: {producto.get('nombre', 'Sin nombre')}")

        # Convert ObjectId to string
        producto['id'] = str(producto['_id'])
        del producto['_id']

        # Convert datetime objects to strings for JSON serialization
        if 'created_at' in producto and producto['created_at']:
            producto['created_at'] = producto['created_at'].isoformat()
        if 'updated_at' in producto and producto['updated_at']:
            producto['updated_at'] = producto['updated_at'].isoformat()

        logger.info(f"Renderizando template para producto: {producto.get('nombre', 'Sin nombre')}")
        return templates.TemplateResponse("producto.html", {
            "request": request,
            "product": producto
        })
    except Exception as e:
        logger.error(f"Error loading product {producto_id}: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return Response(status_code=500, content="Error interno del servidor")

@app.get("/")
async def root():
    """Página de inicio simple"""
    return {"message": "Servidor funcionando"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8004)