"""
Router para administración de categorías de ecommerce
"""
from fastapi import APIRouter, Depends, HTTPException, status, Form, UploadFile, File
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
import os
import shutil
from datetime import datetime

from Projects.ecomerce.models.categorias import EcomerceCategorias
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
    id: int
    nombre: str
    descripcion: Optional[str]
    imagen_url: Optional[str]
    id_padre: int
    active: bool
    created_at: Optional[datetime]

router = APIRouter(
    prefix="/admin/categorias",
    tags=["admin-categorias"],
)

# Directorio para guardar imágenes de categorías
UPLOAD_DIR = "static/img/categorias"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.get("/")
async def categorias_admin_page(
    request: dict,
    user_data: dict = Depends(require_admin_for_template),
):
    """Página de administración de categorías"""
    try:
        # Obtener todas las categorías
        categorias = db.query(EcomerceCategorias).order_by(EcomerceCategorias.nombre).all()

        categorias_list = []
        for cat in categorias:
            categorias_list.append({
                "id": cat.id,
                "nombre": cat.nombre,
                "descripcion": cat.descripcion,
                "imagen_url": cat.imagen_url,
                "id_padre": cat.id_padre,
                "active": cat.active,
                "created_at": cat.created_at
            })

        template_data = {
            "request": request,
            **user_data,
            "categorias": categorias_list,
            "total_categorias": len(categorias_list)
        }

        # Como no tenemos template específico, devolver JSON por ahora
        return JSONResponse(content=template_data)

    except Exception as e:
        print(f"Error obteniendo categorías admin: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/")
async def create_categoria(
    nombre: str = Form(...),
    descripcion: str = Form(""),
    imagen: Optional[UploadFile] = File(None),
    id_padre: int = Form(0),
    active: bool = Form(False),
):
    """Crear una nueva categoría"""
    try:
        # Procesar imagen si se proporcionó
        imagen_url = None
        if imagen and imagen.filename:
            # Generar nombre único para la imagen
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

        db.add(nueva_categoria)
        db.commit()
        db.refresh(nueva_categoria)

        return {
            "success": True,
            "message": "Categoría creada exitosamente",
            "categoria": {
                "id": nueva_categoria.id,
                "nombre": nueva_categoria.nombre,
                "descripcion": nueva_categoria.descripcion,
                "imagen_url": nueva_categoria.imagen_url,
                "active": nueva_categoria.active
            }
        }

    except Exception as e:
        db.rollback()
        print(f"Error creando categoría: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al crear la categoría: {str(e)}"
        )

@router.put("/{categoria_id}")
async def update_categoria(
    categoria_id: int,
    nombre: Optional[str] = Form(None),
    descripcion: Optional[str] = Form(None),
    imagen: Optional[UploadFile] = File(None),
    id_padre: Optional[int] = Form(None),
    active: Optional[bool] = Form(None),
):
    """Actualizar una categoría existente"""
    try:
        categoria = db.query(EcomerceCategorias).filter(EcomerceCategorias.id == categoria_id).first()
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

        db.commit()
        db.refresh(categoria)

        return {
            "success": True,
            "message": "Categoría actualizada exitosamente",
            "categoria": {
                "id": categoria.id,
                "nombre": categoria.nombre,
                "descripcion": categoria.descripcion,
                "imagen_url": categoria.imagen_url,
                "active": categoria.active
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        print(f"Error actualizando categoría: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al actualizar la categoría: {str(e)}"
        )

@router.delete("/{categoria_id}")
def delete_categoria(categoria_id: int):
    """Eliminar una categoría"""
    try:
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        # Eliminar imagen asociada si existe
        if categoria.imagen_url:
            image_path = categoria.imagen_url.replace("/static/", "static/")
            if os.path.exists(image_path):
                os.remove(image_path)

        # Verificar si hay productos usando esta categoría
        result = db.execute("""
            SELECT COUNT(*) FROM ecomerce_productos
            WHERE id_categoria = :categoria_id
        """, {"categoria_id": categoria_id})

        productos_count = result.scalar()
        if productos_count > 0:
            raise HTTPException(
                status_code=400,
                detail=f"No se puede eliminar la categoría porque tiene {productos_count} productos asociados"
            )

        db.delete(categoria)
        db.commit()

        return {
            "success": True,
            "message": "Categoría eliminada exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error eliminando categoría {categoria_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Error al eliminar la categoría: {str(e)}"
        )

@router.get("/{categoria_id}")
def get_categoria(categoria_id: int):
    """Obtener una categoría específica"""
    try:
        categoria = db.query(EcomerceCategorias).filter(EcomerceCategorias.id == categoria_id).first()
        if not categoria:
            raise HTTPException(status_code=404, detail="Categoría no encontrada")

        return {
            "id": categoria.id,
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
