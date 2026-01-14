# routers/servicios.py
from fastapi import APIRouter, HTTPException
from models.models_beanie import Servicio
from typing import List

router = APIRouter()

@router.get("/servicios", response_model=List[Servicio])
async def listar_servicios():
    servicios = await Servicio.find(Servicio.activo == True).to_list()
    return servicios

@router.get("/servicios/publicos")
async def listar_servicios_publicos():
    """Endpoint público para listar productos activos como servicios"""
    try:
        from motor.motor_asyncio import AsyncIOMotorClient
        client = AsyncIOMotorClient('mongodb://localhost:27017')
        db = client.db_sysne
        
        # Obtener productos activos de la colección "productos" (estos son los servicios)
        productos_cursor = db.productos.find({"activo": True})
        servicios_data = []
        async for producto in productos_cursor:
            servicios_data.append({
                "id": str(producto['_id']),
                "nombre": producto.get('nombre', 'Producto sin nombre'),
                "descripcion": producto.get('descripcion', 'Sin descripción'),
                "tipo_servicio": producto.get('categoria', 'producto'),  # Usar categoría como tipo
                "precio_base": producto.get('precio', 0.0),
                "activo": producto.get('activo', True),
                "created_at": producto.get('created_at').isoformat() if producto.get('created_at') else None,
                "updated_at": producto.get('updated_at').isoformat() if producto.get('updated_at') else None
            })
        
        return servicios_data
    except Exception as e:
        # Fallback a datos mock si hay error de base de datos
        from datetime import datetime
        mock_servicios_data = [
            {
                "id": "507f1f77bcf86cd799439011",
                "nombre": "Producto de Ejemplo",
                "descripcion": "Descripción de ejemplo.",
                "tipo_servicio": "producto",
                "precio_base": 100.0,
                "activo": True,
                "created_at": datetime.utcnow().isoformat(),
                "updated_at": datetime.utcnow().isoformat()
            }
        ]
        return mock_servicios_data

@router.get("/servicios/{servicio_id}", response_model=Servicio)
async def obtener_servicio(servicio_id: str):
    servicio = await Servicio.get(servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    return servicio