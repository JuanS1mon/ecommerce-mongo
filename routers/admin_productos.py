# routers/admin_productos.py
from fastapi import APIRouter, HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorClient
from routers.productos import ProductoCreate, ProductoUpdate, Producto
from routers.admin_auth import get_current_admin_user
from typing import List
from datetime import datetime
from bson import ObjectId

router = APIRouter()

# Cliente MongoDB
client = AsyncIOMotorClient('mongodb://localhost:27017')
db = client.db_sysne

@router.get("/productos", response_model=List[Producto])
async def listar_productos_admin(current_admin=Depends(get_current_admin_user)):
    productos = []
    cursor = db.productos.find({})
    async for producto in cursor:
        producto['id'] = str(producto['_id'])
        del producto['_id']
        productos.append(Producto(**producto))
    return productos

@router.post("/productos")
async def crear_producto(producto: ProductoCreate, current_admin=Depends(get_current_admin_user)):
    print(f"DEBUG: Endpoint crear_producto llamado con admin: {current_admin}")
    print(f"DEBUG: Recibiendo datos del producto: {producto.dict()}")
    print(f"DEBUG: Tipo de precio: {type(producto.precio)}, valor: {producto.precio}")
    print(f"DEBUG: Tipo de stock: {type(producto.stock)}, valor: {producto.stock}")
    try:
        nuevo_producto = {
            **producto.dict(),
            "activo": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        }
        print(f"DEBUG: Insertando producto: {nuevo_producto}")
        result = await db.productos.insert_one(nuevo_producto)
        nuevo_producto['id'] = str(result.inserted_id)
        print(f"DEBUG: Producto insertado con ID: {nuevo_producto['id']}")
        
        # Crear objeto Producto para validar
        producto_obj = Producto(**nuevo_producto)
        print(f"DEBUG: Producto validado: {producto_obj}")
        
        return producto_obj
    except Exception as e:
        print(f"ERROR: Excepción en crear_producto: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@router.put("/productos/{producto_id}", response_model=Producto)
async def actualizar_producto(
    producto_id: str,
    producto_update: ProductoUpdate,
    current_admin=Depends(get_current_admin_user)
):
    update_data = producto_update.dict(exclude_unset=True)
    if update_data:
        update_data["updated_at"] = datetime.utcnow()
        result = await db.productos.update_one(
            {"_id": ObjectId(producto_id)},
            {"$set": update_data}
        )
        if result.matched_count == 0:
            raise HTTPException(status_code=404, detail="Producto no encontrado")
    
    # Obtener el producto actualizado
    producto = await db.productos.find_one({"_id": ObjectId(producto_id)})
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    producto['id'] = str(producto['_id'])
    del producto['_id']
    return Producto(**producto)

@router.delete("/productos/{producto_id}")
async def eliminar_producto(producto_id: str, current_admin=Depends(get_current_admin_user)):
    result = await db.productos.delete_one({"_id": ObjectId(producto_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return {"message": "Producto eliminado exitosamente"}