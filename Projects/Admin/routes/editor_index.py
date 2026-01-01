"""
Router de Editor Visual del Index
Permite gestionar secciones y contenido de la página principal
"""
import logging
import os
import json
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form, Body
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.middleware.admin_auth import require_admin

logger = logging.getLogger(__name__)

templates = Jinja2Templates(directory="Projects/Admin/templates")

router = APIRouter(
    prefix="/admin/editor-index",
    tags=["admin-editor-index"]
)

# Rutas de archivos
INDEX_FILE_PATH = os.path.join(os.getcwd(), "static", "index.html")
CONFIG_FILE_PATH = os.path.join(os.getcwd(), "static", "index_config.json")


def leer_index_html() -> str:
    """Lee el contenido actual del index.html"""
    try:
        if os.path.exists(INDEX_FILE_PATH):
            with open(INDEX_FILE_PATH, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            logger.warning("Archivo index.html no encontrado")
            return ""
    except Exception as e:
        logger.error(f"Error leyendo index.html: {str(e)}")
        raise


def escribir_index_html(contenido: str) -> bool:
    """Escribe el contenido en el index.html"""
    try:
        # Hacer backup antes de modificar
        backup_path = INDEX_FILE_PATH + f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if os.path.exists(INDEX_FILE_PATH):
            with open(INDEX_FILE_PATH, 'r', encoding='utf-8') as f:
                backup_content = f.read()
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(backup_content)
        
        # Escribir nuevo contenido
        with open(INDEX_FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(contenido)
        
        logger.info(f"Index.html actualizado. Backup guardado en: {backup_path}")
        return True
        
    except Exception as e:
        logger.error(f"Error escribiendo index.html: {str(e)}")
        return False


def leer_configuracion_secciones() -> Dict[str, Any]:
    """
    Lee la configuración de secciones del index
    Si no existe, crea una configuración por defecto
    """
    try:
        if os.path.exists(CONFIG_FILE_PATH):
            with open(CONFIG_FILE_PATH, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            # Configuración por defecto
            return {
                "secciones": [
                    {
                        "id": "hero",
                        "nombre": "Hero / Banner Principal",
                        "activo": True,
                        "orden": 1,
                        "tipo": "hero",
                        "contenido": {
                            "titulo": "Bienvenido a nuestro eCommerce",
                            "subtitulo": "Los mejores productos al mejor precio",
                            "imagen": "/static/img/hero-banner.jpg",
                            "boton_texto": "Ver Productos",
                            "boton_url": "/ecomerce/productos"
                        }
                    },
                    {
                        "id": "productos-destacados",
                        "nombre": "Productos Destacados",
                        "activo": True,
                        "orden": 2,
                        "tipo": "productos",
                        "contenido": {
                            "titulo": "Productos Destacados",
                            "cantidad": 8,
                            "categoria_id": None,
                            "ordenar_por": "mas_vendidos"
                        }
                    },
                    {
                        "id": "categorias",
                        "nombre": "Categorías",
                        "activo": True,
                        "orden": 3,
                        "tipo": "categorias",
                        "contenido": {
                            "titulo": "Explora por Categorías",
                            "mostrar_imagenes": True,
                            "columnas": 4
                        }
                    },
                    {
                        "id": "nosotros",
                        "nombre": "Sobre Nosotros",
                        "activo": True,
                        "orden": 4,
                        "tipo": "texto",
                        "contenido": {
                            "titulo": "Sobre Nosotros",
                            "texto": "Somos una empresa dedicada a...",
                            "imagen": "/static/img/about.jpg"
                        }
                    },
                    {
                        "id": "contacto",
                        "nombre": "Contacto",
                        "activo": True,
                        "orden": 5,
                        "tipo": "contacto",
                        "contenido": {
                            "titulo": "Contáctanos",
                            "mostrar_mapa": True,
                            "mostrar_formulario": True,
                            "email": "contacto@tienda.com",
                            "telefono": "+54 11 1234-5678",
                            "direccion": "Calle Ejemplo 123, Buenos Aires"
                        }
                    }
                ],
                "configuracion_general": {
                    "logo": "/static/img/logo.png",
                    "color_primario": "#3498db",
                    "color_secundario": "#2c3e50",
                    "fuente": "Arial, sans-serif"
                }
            }
            
    except Exception as e:
        logger.error(f"Error leyendo configuración de secciones: {str(e)}")
        raise


def guardar_configuracion_secciones(config: Dict[str, Any]) -> bool:
    """Guarda la configuración de secciones"""
    try:
        with open(CONFIG_FILE_PATH, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info("Configuración de secciones guardada correctamente")
        return True
        
    except Exception as e:
        logger.error(f"Error guardando configuración: {str(e)}")
        return False


@router.get("/", response_class=HTMLResponse)
async def editor_index_view(
    request: Request,
    db: Session = Depends(get_db)
):
    """Vista del editor visual del index (autenticación en frontend)"""
    try:
        return templates.TemplateResponse(
            "editor_index.html",
            {
                "request": request
            }
        )
    except Exception as e:
        logger.error(f"Error cargando editor: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando editor"
        )


@router.get("/api/secciones")
async def obtener_secciones(
    admin_user: Usuarios = Depends(require_admin)
):
    """Obtener todas las secciones configuradas"""
    try:
        config = leer_configuracion_secciones()
        return config
    except Exception as e:
        logger.error(f"Error obteniendo secciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error obteniendo secciones"
        )


@router.put("/api/secciones/orden")
async def actualizar_orden_secciones(
    admin_user: Usuarios = Depends(require_admin),
    orden: List[str] = Body(...)
):
    """
    Actualizar el orden de las secciones
    
    Body: ["hero", "productos-destacados", "categorias", ...]
    """
    try:
        config = leer_configuracion_secciones()
        
        # Crear un mapa de secciones por ID
        secciones_map = {s["id"]: s for s in config["secciones"]}
        
        # Reorganizar según el nuevo orden
        nuevas_secciones = []
        for i, seccion_id in enumerate(orden, start=1):
            if seccion_id in secciones_map:
                seccion = secciones_map[seccion_id]
                seccion["orden"] = i
                nuevas_secciones.append(seccion)
        
        config["secciones"] = nuevas_secciones
        
        if guardar_configuracion_secciones(config):
            logger.info(f"Orden de secciones actualizado por {admin_user.usuario}")
            return {
                "message": "Orden actualizado exitosamente",
                "secciones": nuevas_secciones
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando configuración"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando orden: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando orden"
        )


@router.put("/api/secciones/{seccion_id}/toggle")
async def toggle_seccion(
    seccion_id: str,
    admin_user: Usuarios = Depends(require_admin)
):
    """Activar/desactivar una sección"""
    try:
        config = leer_configuracion_secciones()
        
        # Buscar la sección
        seccion_encontrada = None
        for seccion in config["secciones"]:
            if seccion["id"] == seccion_id:
                seccion["activo"] = not seccion["activo"]
                seccion_encontrada = seccion
                break
        
        if not seccion_encontrada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sección no encontrada"
            )
        
        if guardar_configuracion_secciones(config):
            logger.info(
                f"Sección {seccion_id} {'activada' if seccion_encontrada['activo'] else 'desactivada'} "
                f"por {admin_user.usuario}"
            )
            return {
                "message": f"Sección {'activada' if seccion_encontrada['activo'] else 'desactivada'}",
                "seccion_id": seccion_id,
                "activo": seccion_encontrada["activo"]
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando configuración"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error toggleando sección: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando sección"
        )


@router.put("/api/secciones/{seccion_id}")
async def actualizar_contenido_seccion(
    seccion_id: str,
    admin_user: Usuarios = Depends(require_admin),
    contenido: Dict[str, Any] = Body(...)
):
    """Actualizar el contenido de una sección específica"""
    try:
        config = leer_configuracion_secciones()
        
        # Buscar y actualizar la sección
        seccion_actualizada = None
        for seccion in config["secciones"]:
            if seccion["id"] == seccion_id:
                seccion["contenido"] = contenido
                seccion_actualizada = seccion
                break
        
        if not seccion_actualizada:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sección no encontrada"
            )
        
        if guardar_configuracion_secciones(config):
            logger.info(f"Contenido de sección {seccion_id} actualizado por {admin_user.usuario}")
            return {
                "message": "Contenido actualizado exitosamente",
                "seccion": seccion_actualizada
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando configuración"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando contenido: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error actualizando contenido"
        )


@router.post("/api/secciones")
async def crear_seccion(
    admin_user: Usuarios = Depends(require_admin),
    seccion: Dict[str, Any] = Body(...)
):
    """Crear una nueva sección"""
    try:
        config = leer_configuracion_secciones()
        
        # Validar que no exista una sección con el mismo ID
        if any(s["id"] == seccion["id"] for s in config["secciones"]):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe una sección con ese ID"
            )
        
        # Asignar orden al final
        max_orden = max([s["orden"] for s in config["secciones"]], default=0)
        seccion["orden"] = max_orden + 1
        seccion["activo"] = seccion.get("activo", True)
        
        # Agregar la sección
        config["secciones"].append(seccion)
        
        if guardar_configuracion_secciones(config):
            logger.info(f"Sección {seccion['id']} creada por {admin_user.usuario}")
            return {
                "message": "Sección creada exitosamente",
                "seccion": seccion
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando configuración"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando sección: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error creando sección"
        )


@router.delete("/api/secciones/{seccion_id}")
async def eliminar_seccion(
    seccion_id: str,
    admin_user: Usuarios = Depends(require_admin)
):
    """Eliminar una sección"""
    try:
        config = leer_configuracion_secciones()
        
        # Filtrar la sección
        secciones_filtradas = [s for s in config["secciones"] if s["id"] != seccion_id]
        
        if len(secciones_filtradas) == len(config["secciones"]):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sección no encontrada"
            )
        
        config["secciones"] = secciones_filtradas
        
        if guardar_configuracion_secciones(config):
            logger.info(f"Sección {seccion_id} eliminada por {admin_user.usuario}")
            return {
                "message": "Sección eliminada exitosamente",
                "seccion_id": seccion_id
            }
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error guardando configuración"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando sección: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error eliminando sección"
        )


@router.get("/api/preview")
async def preview_index(
    admin_user: Usuarios = Depends(require_admin)
):
    """Obtener una vista previa del index con la configuración actual"""
    try:
        config = leer_configuracion_secciones()
        
        # Filtrar solo secciones activas y ordenarlas
        secciones_activas = sorted(
            [s for s in config["secciones"] if s["activo"]],
            key=lambda x: x["orden"]
        )
        
        return {
            "secciones": secciones_activas,
            "config_general": config.get("configuracion_general", {})
        }
        
    except Exception as e:
        logger.error(f"Error generando preview: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error generando preview"
        )


@router.get("/api/backups")
async def listar_backups(
    admin_user: Usuarios = Depends(require_admin)
):
    """Listar todos los backups del index.html"""
    try:
        static_dir = os.path.dirname(INDEX_FILE_PATH)
        backups = []
        
        for filename in os.listdir(static_dir):
            if filename.startswith("index.html.backup_"):
                filepath = os.path.join(static_dir, filename)
                timestamp = os.path.getmtime(filepath)
                backups.append({
                    "filename": filename,
                    "fecha": datetime.fromtimestamp(timestamp).isoformat(),
                    "size": os.path.getsize(filepath)
                })
        
        # Ordenar por fecha descendente
        backups.sort(key=lambda x: x["fecha"], reverse=True)
        
        return {"backups": backups}
        
    except Exception as e:
        logger.error(f"Error listando backups: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error listando backups"
        )
