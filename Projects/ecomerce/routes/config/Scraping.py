# scraping.py
"""
Router de Scraping - Sistema de extracción de datos web
======================================================

RUTAS PARA PLANTILLAS HTML (usan middleware de autenticación):
- GET /scraping/admin - Panel de administración de scraping
- GET /scraping/nuevo - Página para crear nuevo scraping

RUTAS PARA API (usan JWT token en header Authorization):
- POST /scraping/test-extraction - Probar extracción de datos
- POST /scraping/validate-selector - Validar selectores CSS
- POST /scraping/debug-payload - Debug de estructura JSON (sin auth)

AUTENTICACIÓN:
- Rutas HTML: Middleware automático con redirección a login
- Rutas API: Token JWT en header "Authorization: Bearer <token>"
"""

# Imports de bibliotecas estándar
from datetime import datetime
from io import BytesIO
import json
import logging
import os

# Imports de terceros
from bs4 import BeautifulSoup
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from urllib.parse import urlparse
import pandas as pd
import requests

# Imports del proyecto
# from ...Services.scraping.scraping import extract_with_beautifulsoup, extract_with_selenium
from db.schemas.Scraping import ScraperTestConfig
from security.jwt_auth import get_current_user
from security.auth_middleware import require_auth_for_template

# Funciones stub temporales
def extract_with_beautifulsoup(config):
    """Función temporal stub para extract_with_beautifulsoup"""
    return []

def extract_with_selenium(config):
    """Función temporal stub para extract_with_selenium"""
    return []
from db.models.logs.activity_log import ActivityLog
from db.schemas.config.Usuarios import UserDB

# Configuración de logging
logging.basicConfig(
    filename='logs/scraping.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Ajustar el directorio de las plantillas
templates = Jinja2Templates(directory="static")

# Router configuration
router = APIRouter(
    include_in_schema=False,  # Oculta todas las rutas de este router en la documentación
    prefix="/scraping",
    tags=["Scraping"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "ruta no encontrada"}}
)

# Modelo básico para validaciones simples (si se necesita en el futuro)
class ScrapingRequest(BaseModel):
    url: str
    selector: str = None
    max_pages: int = 1


@router.get("/admin")
async def scraping_admin(
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    """Página de administración de scraping"""
    # Añadir datos específicos de scraping a los datos del usuario
    scraping_data = {
        "scraper_count": 0,  # TODO: Contar scrapers reales
        "scraping_runs": 0,  # TODO: Contar ejecuciones reales
        "extracted_data_count": 0,  # TODO: Contar datos extraídos
        "last_run_date": "Ninguna",  # TODO: Obtener fecha real
    }
    
    return templates.TemplateResponse("html/scraping/scraping_admin.html", {
        "request": request,
        **user_data,  # Incluye user, user_count, activities, etc.
        **scraping_data  # Incluye datos específicos de scraping
    })


@router.get("/nuevo")
async def scraping_nuevo(
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    """Página para crear nuevo scraping"""
    return templates.TemplateResponse("html/scraping/scraping_new.html", {
        "request": request,
        **user_data  # Incluye user, user_count, activities, etc.
    })

@router.post("/test-extraction", response_class=JSONResponse)
async def test_extraction(
    config: ScraperTestConfig,
    current_user: UserDB = Depends(get_current_user)
):
    """Endpoint API para probar extracción de datos - Requiere token JWT en header Authorization"""
    try:
        # Validar URL
        from urllib.parse import urlparse
        parsed_url = urlparse(config.url)
        if not parsed_url.scheme or not parsed_url.netloc:
            return JSONResponse(
                status_code=400,
                content={"error": "URL inválida. Debe incluir protocolo (http/https)"}
            )
        
        # Validar que haya al menos un selector
        if not config.selectors or len(config.selectors) == 0:
            return JSONResponse(
                status_code=400,
                content={"error": "Debe proporcionar al menos un selector"}
            )
        
        # Registrar la actividad
        logging.info(f"Usuario {current_user.usuario} iniciando prueba de extracción: {config.url}")
        
        # Ejecutar la extracción según la tecnología seleccionada
        if config.technology == "beautifulsoup":
            results = extract_with_beautifulsoup(config)
        elif config.technology == "selenium":
            results = extract_with_selenium(config)
        #elif config.technology == "scrapy":
            #results = extract_with_scrapy(config)
        else:
            return JSONResponse(
                status_code=400,
                content={"error": f"Tecnología no soportada: {config.technology}"}
            )
            
        # Devolver los resultados
        return JSONResponse(
            content={
                "success": True,
                "message": "Extracción completada con éxito",
                "results": results,
                "count": len(results),
                "url": config.url,
                "technology": config.technology
            }
        )
        
    except ValueError as e:
        logging.error(f"Error de validación en extracción: {str(e)}")
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "error": str(e),
                "message": "Error de validación en los datos proporcionados"
            }
        )
    except requests.exceptions.RequestException as e:
        logging.error(f"Error de conexión en extracción: {str(e)}")
        return JSONResponse(
            status_code=503,
            content={
                "success": False,
                "error": str(e),
                "message": "Error de conexión al sitio web"
            }
        )
    except Exception as e:
        logging.error(f"Error en prueba de extracción: {str(e)}")
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e),
                "message": "Error interno al realizar la extracción"
            }
        )
@router.post("/debug-payload", response_class=JSONResponse)
async def debug_payload(payload: dict):
    """Endpoint para depurar la estructura JSON recibida - Sin autenticación para debug"""
    return JSONResponse(
        content={
            "received": payload,
            "expected_structure": {
                "url": "string",
                "technology": "string (beautifulsoup, selenium, etc)",
                "selectors": [
                    {
                        "name": "string",
                        "path": "string",
                        "type": "string",
                        "attribute": "string (opcional)",
                        "multiple": "boolean"
                    }
                ],
                "container_selector": "string (opcional)",
                "request_delay": "integer",
                "request_timeout": "integer",
                "proxy": {
                    "enabled": "boolean",
                    "address": "string (opcional)",
                    "proxy_type": "string (opcional)"
                },
                "pagination": {
                    "enabled": "boolean",
                    "type": "string (opcional)",
                    "next_selector": "string (opcional)",
                    "page_parameter": "string (opcional)",
                    "max_pages": "integer",
                    "load_more_selector": "string (opcional)"
                },
                "javascript": {
                    "enabled": "boolean",
                    "code": "string (opcional)"
                }
            }
        }
    )
@router.post("/validate-selector", response_class=JSONResponse)
async def validate_selector(
    request_data: dict,
    current_user: UserDB = Depends(get_current_user)
):
    """Endpoint API para validar selectores CSS - Requiere token JWT en header Authorization"""
    try:
        url = request_data.get("url")
        selector = request_data.get("selector")
        
        if not url or not selector:
            return JSONResponse(
                status_code=400,
                content={"error": "URL y selector son requeridos"}
            )
        
        # Realizar solicitud simple
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        
        # Parsear y buscar elementos
        soup = BeautifulSoup(response.text, 'html.parser')
        elements = soup.select(selector)
        
        # Retornar información sobre los elementos encontrados
        return JSONResponse(content={
            "success": True,
            "found": len(elements),
            "selector": selector,
        })
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(e)
            }
        )
@router.get("/debug")
async def scraping_debug(
    request: Request,
    user_data: dict = Depends(require_auth_for_template)
):
    """Endpoint de debug para verificar que la autenticación funciona"""
    try:
        return {
            "message": "Autenticación de scraping funcionando correctamente",
            "user_data_keys": list(user_data.keys()),
            "user": user_data.get("user", {}),
            "path": str(request.url.path),
            "is_authenticated": user_data.get("is_authenticated", False)
        }
    except Exception as e:
        return {
            "error": str(e),
            "message": "Error en debug de scraping"
        }
