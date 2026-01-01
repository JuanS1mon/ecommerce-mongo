"""
Router para administración de categorías de ecommerce (MongoDB/Beanie)
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
from datetime import datetime

from Projects.ecomerce.models.categorias_beanie import EcomerceCategorias
from security.auth_middleware import require_admin_for_template

# Pydantic models
class CategoriaCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    id_padre: Optional[int] = 0
    active: Optional[bool] = False

class CategoriaUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    id_padre: Optional[int] = None
    active: Optional[bool] = None

class CategoriaResponse(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str]
    imagen_url: Optional[str]
    id_padre: int
    active: bool
    created_at: Optional[datetime]

# Modelo simple para crear/actualizar desde el modal de productos
class CategoriaSimple(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    imagen_url: Optional[str] = None
    id_padre: int = 0
    activo: bool = True

router = APIRouter(
    prefix="/api/categorias",
    tags=["admin-categorias"],
)

# Directorio para guardar imágenes de categorías
UPLOAD_DIR = "static/img/categorias"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/")
async def get_all_categorias():
    """Obtener todas las categorías"""
    try:
        categorias = await EcomerceCategorias.find().sort("nombre").to_list()
        
        print(f"DEBUG: Total categorías encontradas: {len(categorias)}")
        for cat in categorias:
            print(f"DEBUG: ID={cat.id}, Nombre={cat.nombre}, Active={cat.active}")
        
        resultado = [
            {
                "id": str(cat.id),
                "nombre": cat.nombre,
                "descripcion": cat.descripcion,
                "imagen_url": cat.imagen_url,
                "id_padre": cat.id_padre,
                "activo": cat.active,  # Usar 'activo' en lugar de 'active' para el frontend
                "created_at": cat.created_at
            }
            for cat in categorias
        ]
        
        print(f"DEBUG: Resultado JSON: {resultado}")
        return resultado
        
    except Exception as e:
        print(f"Error obteniendo categorías: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/", status_code=201)
async def create_categoria_json(categoria: CategoriaSimple):
    """Crear una nueva categoría desde JSON"""
    try:
        nueva_categoria = EcomerceCategorias(
            nombre=categoria.nombre,
            descripcion=categoria.descripcion,
            imagen_url=categoria.imagen_url,
            id_padre=categoria.id_padre,
            active=categoria.activo
        )
        
        await nueva_categoria.insert()
        
        return {
            "id": str(nueva_categoria.id),
            "nombre": nueva_categoria.nombre,
            "descripcion": nueva_categoria.descripcion,
            "imagen_url": nueva_categoria.imagen_url,
            "id_padre": nueva_categoria.id_padre,
            "activo": nueva_categoria.active
        }
    except Exception as e:
        print(f"Error creando categoría: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la categoría: {str(e)}"
        )

@router.post("/upload")
async def create_categoria_form(
    nombre: str = Form(...),
    descripcion: str = Form(""),
    imagen: Optional[UploadFile] = File(None),
    id_padre: int = Form(0),
    active: bool = Form(False)
):
    """Crear una nueva categoría con imagen (Form data)"""
    try:
        # Procesar imagen si se proporcionó
        imagen_url = None
        if imagen and imagen.filename:
            # Generar nombre único para la imagen
            file_extension = os.path.splitext(imagen.filename)[1]
            filename = f"categoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Guardar archivo
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(imagen.file, buffer)

            imagen_url = f"/static/img/categorias/{filename}"

        # Crear categoría
        nueva_categoria = EcomerceCategorias(
            nombre=nombre,
            descripcion=descripcion if descripcion else None,
            imagen_url=imagen_url,
            id_padre=id_padre,
            active=active
        )

        await nueva_categoria.insert()

        return {
            "success": True,
            "message": "Categoría creada exitosamente",
            "categoria": {
                "id": str(nueva_categoria.id),
                "nombre": nueva_categoria.nombre,
                "descripcion": nueva_categoria.descripcion,
                "imagen_url": nueva_categoria.imagen_url,
                "active": nueva_categoria.active
            }
        }

    except Exception as e:
        print(f"Error creando categoría: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la categoría: {str(e)}"
        )

@router.put("/{categoria_id}")
async def update_categoria_json(
    categoria_id: str,
    categoria: CategoriaSimple
):
    """Actualizar una categoría desde JSON"""
    try:
        cat = await EcomerceCategorias.get(categoria_id)
        if not cat:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")
        
        cat.nombre = categoria.nombre
        cat.descripcion = categoria.descripcion
        cat.imagen_url = categoria.imagen_url
        cat.id_padre = categoria.id_padre
        cat.active = categoria.activo
        
        await cat.save()
        
        return {
            "id": str(cat.id),
            "nombre": cat.nombre,
            "descripcion": cat.descripcion,
            "imagen_url": cat.imagen_url,
            "id_padre": cat.id_padre,
            "activo": cat.active
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error actualizando categoría: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar la categoría: {str(e)}"
        )

@router.put("/{categoria_id}/upload")
async def update_categoria_form(
    categoria_id: str,
    nombre: Optional[str] = Form(None),
    descripcion: Optional[str] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    id_padre: Optional[int] = Form(None),
    active: Optional[bool] = Form(None)
):
    """Actualizar una categoría con imagen (Form data)"""
    try:
        categoria = await EcomerceCategorias.get(categoria_id)
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        # Procesar imagen si se proporcionó
        if imagen and imagen.filename:
            # Eliminar imagen anterior si existe
            if categoria.imagen_url:
                old_path = categoria.imagen_url.replace("/static/", "static/")
                if os.path.exists(old_path):
                    os.remove(old_path)

            # Generar nombre único para la nueva imagen
            file_extension = os.path.splitext(imagen.filename)[1]
            filename = f"categoria_{datetime.now().strftime('%Y%m%d_%H%M%S')}{file_extension}"
            file_path = os.path.join(UPLOAD_DIR, filename)

            # Guardar archivo
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(imagen.file, buffer)

            categoria.imagen_url = f"/static/img/categorias/{filename}"

        # Actualizar campos
        if nombre is not None:
            categoria.nombre = nombre
        if descripcion is not None:
            categoria.descripcion = descripcion if descripcion else None
        if id_padre is not None:
            categoria.id_padre = id_padre
        if active is not None:
            categoria.active = active

        await categoria.save()

        return {
            "success": True,
            "message": "Categoría actualizada exitosamente",
            "categoria": {
                "id": str(categoria.id),
                "nombre": categoria.nombre,
                "descripcion": categoria.descripcion,
                "imagen_url": categoria.imagen_url,
                "active": categoria.active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error actualizando categoría: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar la categoría: {str(e)}"
        )

@router.delete("/{categoria_id}")
async def delete_categoria(categoria_id: str):
    """Eliminar una categoría"""
    try:
        categoria = await EcomerceCategorias.get(categoria_id)
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        # Eliminar imagen asociada si existe
        if categoria.imagen_url:
            image_path = categoria.imagen_url.replace("/static/", "static/")
            if os.path.exists(image_path):
                os.remove(image_path)

        # Verificar si hay productos usando esta categoría
        from Projects.ecomerce.models.productos_beanie import EcomerceProductos
        productos_count = await EcomerceProductos.find(
            EcomerceProductos.id_categoria == str(categoria.id)
        ).count()

        if productos_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede eliminar la categoría porque tiene {productos_count} productos asociados"
            )

        await categoria.delete()

        return {
            "success": True,
            "message": "Categoría eliminada exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error eliminando categoría: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la categoría: {str(e)}"
        )

@router.get("/{categoria_id}")
async def get_categoria(categoria_id: str):
    """Obtener una categoría específica"""
    try:
        categoria = await EcomerceCategorias.get(categoria_id)
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        return {
            "id": str(categoria.id),
            "nombre": categoria.nombre,
            "descripcion": categoria.descripcion,
            "imagen_url": categoria.imagen_url,
            "id_padre": categoria.id_padre,
            "active": categoria.active,
            "created_at": categoria.created_at
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error obteniendo categoría {categoria_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )
