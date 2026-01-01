"""
Router de Gestión de Configuración del Sistema
Permite editar configuraciones desde el panel admin
"""
import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.middleware.admin_auth import require_admin
from Projects.Admin.utils.template_helpers import render_admin_template
from Projects.Admin.models.marketing_beanie import MarketingConfig

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/configuracion",
    tags=["admin-configuracion"]
)


@router.get("/", response_class=HTMLResponse)
async def configuracion_view(request: Request):
    """Vista de gestión de configuración"""
    try:
        return render_admin_template(
            "configuracion.html",
            request,
            active_page="configuracion"
        )
    except Exception as e:
        logger.error(f"Error cargando configuración: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando configuración"
        )


@router.get("/api/config")
async def obtener_configuracion(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """API para obtener todas las configuraciones del sistema"""
    try:
        # Obtener configuración de marketing
        config_obj = await MarketingConfig.find_one()
        if config_obj:
            # Convertir el objeto Beanie a diccionario
            config = {
                "google_ai_api_key": config_obj.google_ai_api_key,
                "facebook_app_id": config_obj.facebook_app_id,
                "facebook_app_secret": config_obj.facebook_app_secret,
                "facebook_access_token": config_obj.facebook_access_token,
                "instagram_access_token": config_obj.instagram_access_token,
                "modelo_ia": config_obj.modelo_ia,
                "max_tokens_por_request": config_obj.max_tokens_por_request,
                "temperatura": config_obj.temperatura,
                "max_campanas_por_dia": config_obj.max_campanas_por_dia,
                "max_campanas_por_mes": config_obj.max_campanas_por_mes,
                "activo": config_obj.activo
            }
        else:
            # Crear configuración por defecto
            config = {
                "google_ai_api_key": "",
                "facebook_app_id": "",
                "facebook_app_secret": "",
                "facebook_access_token": "",
                "instagram_access_token": "",
                "modelo_ia": "gemini-1.5-flash",
                "max_tokens_por_request": 1000,
                "temperatura": 0.7,
                "max_campanas_por_dia": 10,
                "max_campanas_por_mes": 100,
                "activo": True
            }
        
        # Configuraciones con formato compatible con la plantilla
        configuraciones = {
            "aplicacion": [
                {
                    "clave": "PROJECT_NAME",
                    "valor": os.getenv("PROJECT_NAME", "E-commerce"),
                    "descripcion": "Nombre del proyecto",
                    "es_sensible": False
                },
                {
                    "clave": "ENVIRONMENT",
                    "valor": os.getenv("ENVIRONMENT", "development"),
                    "descripcion": "Entorno de ejecución (development/production)",
                    "es_sensible": False
                },
                {
                    "clave": "DEBUG",
                    "valor": os.getenv("DEBUG", "False"),
                    "descripcion": "Modo debug activado",
                    "es_sensible": False
                },
            ],
            "empresa": [
                {
                    "clave": "DATABASE_NAME",
                    "valor": os.getenv("DATABASE_NAME", "ecommerce"),
                    "descripcion": "Nombre de la base de datos",
                    "es_sensible": False
                },
                {
                    "clave": "MONGODB_URL",
                    "valor": "***hidden***" if os.getenv("MONGODB_URL") else "",
                    "descripcion": "URL de conexión MongoDB",
                    "es_sensible": True
                },
                {
                    "clave": "SECRET_KEY",
                    "valor": "***hidden***" if os.getenv("SECRET_KEY") else "",
                    "descripcion": "Clave secreta JWT",
                    "es_sensible": True
                },
                {
                    "clave": "ALGORITHM",
                    "valor": os.getenv("ALGORITHM", "HS256"),
                    "descripcion": "Algoritmo de encriptación JWT",
                    "es_sensible": False
                },
                {
                    "clave": "ACCESS_TOKEN_EXPIRE_MINUTES",
                    "valor": os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"),
                    "descripcion": "Tiempo de expiración del token (minutos)",
                    "es_sensible": False
                },
            ],
            "correo": [
                {
                    "clave": "MAIL_ENABLED",
                    "valor": os.getenv("MAIL_ENABLED", "False"),
                    "descripcion": "Habilitar envío de correos",
                    "es_sensible": False
                },
                {
                    "clave": "MAIL_FROM",
                    "valor": os.getenv("MAIL_FROM", ""),
                    "descripcion": "Email remitente",
                    "es_sensible": False
                },
                {
                    "clave": "MAIL_FROM_NAME",
                    "valor": os.getenv("MAIL_FROM_NAME", ""),
                    "descripcion": "Nombre del remitente",
                    "es_sensible": False
                },
                {
                    "clave": "MAIL_SERVER",
                    "valor": os.getenv("MAIL_SERVER", ""),
                    "descripcion": "Servidor SMTP",
                    "es_sensible": False
                },
                {
                    "clave": "MAIL_PORT",
                    "valor": os.getenv("MAIL_PORT", "587"),
                    "descripcion": "Puerto SMTP",
                    "es_sensible": False
                },
                {
                    "clave": "MAIL_USERNAME",
                    "valor": os.getenv("MAIL_USERNAME", ""),
                    "descripcion": "Usuario SMTP",
                    "es_sensible": False
                },
                {
                    "clave": "MAIL_PASSWORD",
                    "valor": "***hidden***" if os.getenv("MAIL_PASSWORD") else "",
                    "descripcion": "Contraseña SMTP",
                    "es_sensible": True
                },
            ],
            "oauth": [
                {
                    "clave": "GOOGLE_CLIENT_ID",
                    "valor": os.getenv("GOOGLE_CLIENT_ID", ""),
                    "descripcion": "Google OAuth Client ID",
                    "es_sensible": False
                },
                {
                    "clave": "GOOGLE_CLIENT_SECRET",
                    "valor": "***hidden***" if os.getenv("GOOGLE_CLIENT_SECRET") else "",
                    "descripcion": "Google OAuth Client Secret",
                    "es_sensible": True
                },
                {
                    "clave": "GOOGLE_REDIRECT_URI",
                    "valor": os.getenv("GOOGLE_REDIRECT_URI", ""),
                    "descripcion": "URI de redirección OAuth",
                    "es_sensible": False
                },
            ],
            "marketing": [
                {
                    "clave": "GOOGLE_AI_API_KEY",
                    "valor": "***hidden***" if config["google_ai_api_key"] else "",
                    "descripcion": "API Key de Google Gemini (obtén en https://makersuite.google.com/app/apikey)",
                    "es_sensible": True
                },
                {
                    "clave": "MODELO_IA",
                    "valor": config["modelo_ia"],
                    "descripcion": "Modelo de IA a usar (gemini-1.5-flash, gemini-1.5-pro)",
                    "es_sensible": False
                },
                {
                    "clave": "MAX_TOKENS_POR_REQUEST",
                    "valor": str(config["max_tokens_por_request"]),
                    "descripcion": "Máximo de tokens por request de IA",
                    "es_sensible": False
                },
                {
                    "clave": "TEMPERATURA_IA",
                    "valor": str(config["temperatura"]),
                    "descripcion": "Creatividad de la IA (0.0-1.0, más alto = más creativo)",
                    "es_sensible": False
                },
                {
                    "clave": "MAX_CAMPANAS_POR_DIA",
                    "valor": str(config["max_campanas_por_dia"]),
                    "descripcion": "Límite de campañas por día",
                    "es_sensible": False
                },
                {
                    "clave": "MAX_CAMPANAS_POR_MES",
                    "valor": str(config["max_campanas_por_mes"]),
                    "descripcion": "Límite de campañas por mes",
                    "es_sensible": False
                },
                {
                    "clave": "MARKETING_ACTIVO",
                    "valor": "True" if config["activo"] else "False",
                    "descripcion": "Habilitar sistema de marketing con IA",
                    "es_sensible": False
                },
            ]
        }
        
        return {
            "success": True,
            "data": configuraciones,
            "usuario": admin_user.usuario
        }
    except Exception as e:
        logger.error(f"Error obteniendo configuraciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error: {str(e)}"
        )


@router.post("/api/config")
async def actualizar_configuracion(
    # Aplicación
    project_name: Optional[str] = Form(None),
    environment: Optional[str] = Form(None),
    debug: Optional[str] = Form(None),
    
    # Empresa/Base de datos
    database_name: Optional[str] = Form(None),
    mongodb_url: Optional[str] = Form(None),
    secret_key: Optional[str] = Form(None),
    algorithm: Optional[str] = Form(None),
    access_token_expire_minutes: Optional[str] = Form(None),
    
    # Correo
    mail_enabled: Optional[str] = Form(None),
    mail_from: Optional[str] = Form(None),
    mail_from_name: Optional[str] = Form(None),
    mail_server: Optional[str] = Form(None),
    mail_port: Optional[str] = Form(None),
    mail_username: Optional[str] = Form(None),
    mail_password: Optional[str] = Form(None),
    
    # OAuth
    google_client_id: Optional[str] = Form(None),
    google_client_secret: Optional[str] = Form(None),
    google_redirect_uri: Optional[str] = Form(None),
    
    # Marketing
    google_ai_api_key: Optional[str] = Form(None),
    modelo_ia: Optional[str] = Form(None),
    max_tokens_por_request: Optional[str] = Form(None),
    temperatura_ia: Optional[str] = Form(None),
    max_campanas_por_dia: Optional[str] = Form(None),
    max_campanas_por_mes: Optional[str] = Form(None),
    marketing_activo: Optional[str] = Form(None),
    
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """API para actualizar configuraciones del sistema"""
    try:
        # Actualizar variables de entorno de aplicación
        if project_name is not None:
            os.environ["PROJECT_NAME"] = project_name
        if environment is not None:
            os.environ["ENVIRONMENT"] = environment
        if debug is not None:
            os.environ["DEBUG"] = debug
            
        # Actualizar variables de empresa
        if database_name is not None:
            os.environ["DATABASE_NAME"] = database_name
        if mongodb_url is not None:
            os.environ["MONGODB_URL"] = mongodb_url
        if secret_key is not None:
            os.environ["SECRET_KEY"] = secret_key
        if algorithm is not None:
            os.environ["ALGORITHM"] = algorithm
        if access_token_expire_minutes is not None:
            os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = access_token_expire_minutes
            
        # Actualizar variables de correo
        if mail_enabled is not None:
            os.environ["MAIL_ENABLED"] = mail_enabled
        if mail_from is not None:
            os.environ["MAIL_FROM"] = mail_from
        if mail_from_name is not None:
            os.environ["MAIL_FROM_NAME"] = mail_from_name
        if mail_server is not None:
            os.environ["MAIL_SERVER"] = mail_server
        if mail_port is not None:
            os.environ["MAIL_PORT"] = mail_port
        if mail_username is not None:
            os.environ["MAIL_USERNAME"] = mail_username
        if mail_password is not None:
            os.environ["MAIL_PASSWORD"] = mail_password
            
        # Actualizar variables OAuth
        if google_client_id is not None:
            os.environ["GOOGLE_CLIENT_ID"] = google_client_id
        if google_client_secret is not None:
            os.environ["GOOGLE_CLIENT_SECRET"] = google_client_secret
        if google_redirect_uri is not None:
            os.environ["GOOGLE_REDIRECT_URI"] = google_redirect_uri
            
        # Actualizar configuración de marketing
        config = await MarketingConfig.find_one()
        if not config:
            config = MarketingConfig()
            
        if google_ai_api_key is not None:
            config.google_ai_api_key = google_ai_api_key
        if modelo_ia is not None:
            config.modelo_ia = modelo_ia
        if max_tokens_por_request is not None:
            try:
                config.max_tokens_por_request = int(max_tokens_por_request)
            except ValueError:
                pass
        if temperatura_ia is not None:
            try:
                config.temperatura = float(temperatura_ia)
            except ValueError:
                pass
        if max_campanas_por_dia is not None:
            try:
                config.max_campanas_por_dia = int(max_campanas_por_dia)
            except ValueError:
                pass
        if max_campanas_por_mes is not None:
            try:
                config.max_campanas_por_mes = int(max_campanas_por_mes)
            except ValueError:
                pass
        if marketing_activo is not None:
            config.activo = marketing_activo.lower() == "true"
            
        await config.save()
        
        return {
            "success": True,
            "message": "Configuraciones actualizadas correctamente"
        }
        
    except Exception as e:
        logger.error(f"Error actualizando configuraciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando configuraciones: {str(e)}"
        )


@router.put("/api/config/multiple")
async def actualizar_configuraciones_multiples(
    configuraciones: Dict[str, Any],
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """API para actualizar múltiples configuraciones del sistema"""
    try:
        logger.info(f"Actualizando {len(configuraciones)} configuraciones")

        # Variables de aplicación
        project_name = configuraciones.get("PROJECT_NAME")
        environment = configuraciones.get("ENVIRONMENT")
        debug = configuraciones.get("DEBUG")
        database_name = configuraciones.get("DATABASE_NAME")
        mongodb_url = configuraciones.get("MONGODB_URL")
        secret_key = configuraciones.get("SECRET_KEY")
        algorithm = configuraciones.get("ALGORITHM")
        access_token_expire_minutes = configuraciones.get("ACCESS_TOKEN_EXPIRE_MINUTES")

        # Variables de correo
        mail_enabled = configuraciones.get("MAIL_ENABLED")
        mail_from = configuraciones.get("MAIL_FROM")
        mail_from_name = configuraciones.get("MAIL_FROM_NAME")
        mail_server = configuraciones.get("MAIL_SERVER")
        mail_port = configuraciones.get("MAIL_PORT")
        mail_username = configuraciones.get("MAIL_USERNAME")
        mail_password = configuraciones.get("MAIL_PASSWORD")

        # Variables OAuth
        google_client_id = configuraciones.get("GOOGLE_CLIENT_ID")
        google_client_secret = configuraciones.get("GOOGLE_CLIENT_SECRET")
        google_redirect_uri = configuraciones.get("GOOGLE_REDIRECT_URI")

        # Variables de marketing
        google_ai_api_key = configuraciones.get("GOOGLE_AI_API_KEY")
        modelo_ia = configuraciones.get("MODELO_IA")
        max_tokens_por_request = configuraciones.get("MAX_TOKENS_POR_REQUEST")
        temperatura_ia = configuraciones.get("TEMPERATURA")
        max_campanas_por_dia = configuraciones.get("MAX_CAMPANAS_POR_DIA")
        max_campanas_por_mes = configuraciones.get("MAX_CAMPANAS_POR_MES")
        marketing_activo = configuraciones.get("ACTIVO")

        # Actualizar variables de entorno
        if project_name is not None:
            os.environ["PROJECT_NAME"] = project_name
        if environment is not None:
            os.environ["ENVIRONMENT"] = environment
        if debug is not None:
            os.environ["DEBUG"] = debug
        if database_name is not None:
            os.environ["DB_NAME"] = database_name
        if mongodb_url is not None:
            os.environ["MONGODB_URL"] = mongodb_url
        if secret_key is not None:
            os.environ["SECRET_KEY"] = secret_key
        if algorithm is not None:
            os.environ["ALGORITHM"] = algorithm
        if access_token_expire_minutes is not None:
            os.environ["ACCESS_TOKEN_EXPIRE_MINUTES"] = access_token_expire_minutes

        # Actualizar variables de correo
        if mail_enabled is not None:
            os.environ["MAIL_ENABLED"] = mail_enabled
        if mail_from is not None:
            os.environ["MAIL_FROM"] = mail_from
        if mail_from_name is not None:
            os.environ["MAIL_FROM_NAME"] = mail_from_name
        if mail_server is not None:
            os.environ["MAIL_SERVER"] = mail_server
        if mail_port is not None:
            os.environ["MAIL_PORT"] = mail_port
        if mail_username is not None:
            os.environ["MAIL_USERNAME"] = mail_username
        if mail_password is not None:
            os.environ["MAIL_PASSWORD"] = mail_password

        # Actualizar variables OAuth
        if google_client_id is not None:
            os.environ["GOOGLE_CLIENT_ID"] = google_client_id
        if google_client_secret is not None:
            os.environ["GOOGLE_CLIENT_SECRET"] = google_client_secret
        if google_redirect_uri is not None:
            os.environ["GOOGLE_REDIRECT_URI"] = google_redirect_uri

        # Actualizar configuración de marketing
        config = await MarketingConfig.find_one()
        if not config:
            config = MarketingConfig()

        if google_ai_api_key is not None:
            config.google_ai_api_key = google_ai_api_key
        if modelo_ia is not None:
            config.modelo_ia = modelo_ia
        if max_tokens_por_request is not None:
            try:
                config.max_tokens_por_request = int(max_tokens_por_request)
            except ValueError:
                pass
        if temperatura_ia is not None:
            try:
                config.temperatura = float(temperatura_ia)
            except ValueError:
                pass
        if max_campanas_por_dia is not None:
            try:
                config.max_campanas_por_dia = int(max_campanas_por_dia)
            except ValueError:
                pass
        if max_campanas_por_mes is not None:
            try:
                config.max_campanas_por_mes = int(max_campanas_por_mes)
            except ValueError:
                pass
        if marketing_activo is not None:
            config.activo = str(marketing_activo).lower() == "true"

        await config.save()

        return {
            "success": True,
            "message": "Configuraciones actualizadas correctamente",
            "nota": "Los cambios requieren reiniciar el servidor para tomar efecto"
        }

    except Exception as e:
        logger.error(f"Error actualizando configuraciones múltiples: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando configuraciones: {str(e)}"
        )


@router.post("/api/inicializar")
async def inicializar_configuraciones(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """API para inicializar configuraciones desde variables de entorno (.env)"""
    try:
        logger.info("Inicializando configuraciones desde variables de entorno")

        # Obtener configuración de marketing actual o crear nueva
        config = await MarketingConfig.find_one()
        if not config:
            config = MarketingConfig()

        # Actualizar configuración de marketing desde variables de entorno
        google_ai_api_key = os.getenv("GOOGLE_AI_API_KEY")
        if google_ai_api_key:
            config.google_ai_api_key = google_ai_api_key

        modelo_ia = os.getenv("MODELO_IA", "gemini-1.5-flash")
        config.modelo_ia = modelo_ia

        max_tokens_str = os.getenv("MAX_TOKENS_POR_REQUEST", "1000")
        try:
            config.max_tokens_por_request = int(max_tokens_str)
        except ValueError:
            config.max_tokens_por_request = 1000

        temperatura_str = os.getenv("TEMPERATURA_IA", "0.7")
        try:
            config.temperatura = float(temperatura_str)
        except ValueError:
            config.temperatura = 0.7

        max_campanas_dia_str = os.getenv("MAX_CAMPANAS_POR_DIA", "10")
        try:
            config.max_campanas_por_dia = int(max_campanas_dia_str)
        except ValueError:
            config.max_campanas_por_dia = 10

        max_campanas_mes_str = os.getenv("MAX_CAMPANAS_POR_MES", "100")
        try:
            config.max_campanas_por_mes = int(max_campanas_mes_str)
        except ValueError:
            config.max_campanas_por_mes = 100

        marketing_activo_str = os.getenv("MARKETING_ACTIVO", "true")
        config.activo = marketing_activo_str.lower() in ("true", "1", "yes", "on")

        # Guardar configuración
        await config.save()

        logger.info("Configuraciones inicializadas correctamente desde .env")

        return {
            "success": True,
            "message": "Configuraciones inicializadas correctamente desde el archivo .env"
        }

    except Exception as e:
        logger.error(f"Error inicializando configuraciones: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inicializando configuraciones: {str(e)}"
        )

