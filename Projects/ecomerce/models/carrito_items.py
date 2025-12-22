from db.database import Base
from sqlalchemy import Column, Integer, String

class EcomerceCarrito_items(Base):
    __tablename__ = 'ecomerce_carrito_items'

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    id_carrito = Column(String(255), default="")
    id_producto = Column(Integer, default=0)
    cantidad = Column(Integer, default=0)
    precio_unitario = Column(Integer, default=0)
