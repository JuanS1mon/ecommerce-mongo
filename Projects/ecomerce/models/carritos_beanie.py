from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class EcomerceCarritos(Document):
    id_usuario: str = Field(default="")
    estado: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    activo: bool = Field(default=True)
    items: List[Dict[str, Any]] = Field(default_factory=list)

    class Settings:
        name = "ecomerce_carritos"
