from beanie import Document
from pydantic import Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class EcomercePedidos(Document):
    id_usuario: str = Field(default="")
    items: List[Dict[str, Any]] = Field(default_factory=list)
    total: float = 0.0
    estado: str = Field(default="pendiente")  # pendiente, presupuesto, confirmado, cancelado
    metodo_pago: Optional[str] = None
    external_reference: Optional[str] = None  # para MercadoPago u otros
    contacto: Optional[Dict[str, Any]] = None
    datos_envio: Optional[Dict[str, Any]] = None  # Datos de envío del usuario
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ecomerce_pedidos"
