# ============================================================================
# MODELO BEANIE: TABLA1
# ============================================================================
"""
Modelo Beanie para tabla1 (MongoDB)
Parte del servicio: mi_sistema
Convertido de SQLAlchemy a Beanie para NoSQL
"""

from beanie import Document
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class Tabla1(Document):
    """
    Modelo Beanie para tabla1
    Documento en MongoDB para mi_sistema
    """
    id: Optional[int] = None

    class Settings:
        name = "tabla1"  # Nombre de la colección en MongoDB

    def __repr__(self):
        return f"<Tabla1(id={self.id})">
