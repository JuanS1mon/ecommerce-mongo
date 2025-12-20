from beanie import Document
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class EcomerceListaDeseos(Document):
    id_usuario: str
    nombre_lista: str = Field(default="Mi Lista de Deseos")
    productos: List[dict] = Field(default_factory=list)  # Lista de {id_producto, fecha_agregado, precio_al_agregar}
    publica: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "ecomerce_lista_deseos"

class ListaDeseosCreate(BaseModel):
    nombre_lista: Optional[str] = "Mi Lista de Deseos"
    publica: bool = False

class AgregarProductoLista(BaseModel):
    id_producto: str