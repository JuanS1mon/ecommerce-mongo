from beanie import Document
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime

class EcomerceCarritos(Document):
    # Campo sin tipo estricto para permitir valores legacy
    id_usuario: Any = Field(default=None)
    estado: str = Field(default="activo")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    activo: bool = Field(default=True)
    items: List[Dict[str, Any]] = Field(default_factory=list)

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=False  # Desactivar validación en asignaciones
    )

    class Settings:
        name = "ecomerce_carritos"
