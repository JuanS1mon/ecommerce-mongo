# routers/productos.py
from fastapi import APIRouter, HTTPException
from motor.motor_asyncio import AsyncIOMotorClient
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime

router = APIRouter()

class ProductoCreate(BaseModel):
    nombre: str
    descripcion: str
    precio: float
    categoria: str
    imagen_url: Optional[str] = None
    stock: int = 0

class ProductoUpdate(BaseModel):
    nombre: str = None
    descripcion: str = None
    precio: float = None
    categoria: str = None
    imagen_url: Optional[str] = None
    stock: int = None
    activo: bool = None

class Producto(BaseModel):
    id: str
    nombre: str
    descripcion: str
    precio: float
    categoria: str
    imagen_url: Optional[str] = None
    stock: int = 0
    activo: bool = True
    created_at: datetime
    updated_at: datetime

# Cliente MongoDB
client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client.db_sysne

@router.get("/productos/publicos", response_model=List[Producto])
async def listar_productos_publicos(limit: int = 100):
    productos = []
    cursor = db.productos.find({"activo": True}).limit(limit)
    async for producto in cursor:
        producto['id'] = str(producto['_id'])
        del producto['_id']
        productos.append(Producto(**producto))
    return productos

@router.get("/productos/{producto_id}", response_model=Producto)
async def obtener_producto(producto_id: str):
    from bson import ObjectId
    producto = await db.productos.find_one({"_id": ObjectId(producto_id)})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto['id'] = str(producto['_id'])
    del producto['_id']
    return Producto(**producto)

@router.get("/categorias/publicas")
async def listar_categorias():
    # Obtener categorías únicas de productos activos usando agregación
    pipeline = [
        {"$match": {"activo": True}},
        {"$group": {"_id": "$categoria", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}}
    ]
    categorias = []
    cursor = db.productos.aggregate(pipeline)
    async for cat in cursor:
        categorias.append({"nombre": cat["_id"], "count": cat["count"]})
    return categorias