"""
Modelo de Datos para Campañas de Marketing con IA
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from beanie import Document
from pydantic import BaseModel, Field


class ConversacionIAMessage(BaseModel):
    """Mensaje individual en la conversación con IA"""
    role: str  # "user" o "assistant"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class MarketingCampaign(Document):
    """Campaña de marketing generada con IA"""
    producto_id: str  # ID del producto seleccionado
    producto_nombre: str
    producto_descripcion: str
    producto_precio: float
    producto_imagen_url: str

    # Conversación con IA
    conversacion: List[ConversacionIAMessage] = Field(default_factory=list)

    # Contenido generado
    titulo_campana: str = ""
    texto_para_redes: str = ""
    hashtags: List[str] = Field(default_factory=list)
    imagen_final_url: str = ""  # Puede ser diferente a la original

    # Publicación
    plataformas: List[str] = Field(default_factory=list)  # ["facebook", "instagram"]
    estado: str = "borrador"  # "borrador", "generado", "publicado", "programado"
    fecha_publicacion: Optional[datetime] = None

    # Métricas (después de publicar)
    metricas: Optional[Dict[str, Any]] = None

    # Metadata
    creado_por: str  # usuario admin que creó la campaña
    fecha_creacion: datetime = Field(default_factory=datetime.utcnow)
    fecha_actualizacion: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "marketing_campaigns"
        indexes = [
            "producto_id",
            "estado",
            "creado_por",
            "fecha_creacion"
        ]


class MarketingConfig(Document):
    """Configuración del sistema de marketing"""
    google_ai_api_key: str = ""
    facebook_app_id: str = ""
    facebook_app_secret: str = ""
    facebook_access_token: str = ""
    instagram_access_token: str = ""

    # Configuración de IA
    modelo_ia: str = "gemini-1.5-flash"  # Modelo de Google Gemini
    max_tokens_por_request: int = 1000
    temperatura: float = 0.7

    # Límites
    max_campanas_por_dia: int = 10
    max_campanas_por_mes: int = 100

    # Activo
    activo: bool = True

    class Settings:
        name = "marketing_config"