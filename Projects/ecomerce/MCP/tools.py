"""
Herramientas MCP para acceder a datos del e-commerce.
Usa modelos directos: Beanie para MongoDB (productos/carritos), SQLAlchemy para usuarios.
"""

import json
from datetime import datetime
from ..models.productos_beanie import EcomerceProductos
from ..models.carritos_beanie import EcomerceCarritos
from ..models.usuarios import EcomerceUsuarios
from ..models.pedidos_beanie import EcomercePedidos  # Asumiendo que ventas son pedidos
# from ..models.presupuesto import Presupuesto  # No existe, comentar
from db.database import get_db  # Para SQL

def listar_productos() -> str:
    """Lista todos los productos."""
    try:
        productos = EcomerceProductos.find_all().to_list()
        return json.dumps([p.dict() for p in productos], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def buscar_producto_por_id(product_id: str) -> str:
    """Busca producto por ID."""
    try:
        producto = EcomerceProductos.get(product_id)
        return json.dumps(producto.dict() if producto else {"error": "Producto no encontrado"}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def buscar_producto_por_nombre(nombre: str) -> str:
    """Busca productos por nombre (contiene)."""
    try:
        productos = EcomerceProductos.find({"nombre": {"$regex": nombre, "$options": "i"}}).to_list()
        return json.dumps([p.dict() for p in productos], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def buscar_producto_por_categoria(categoria: str) -> str:
    """Busca productos por categoría."""
    try:
        productos = EcomerceProductos.find({"categoria": categoria}).to_list()
        return json.dumps([p.dict() for p in productos], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def consultar_carrito_usuario(user_id: str) -> str:
    """Consulta carrito de usuario."""
    try:
        carrito = EcomerceCarritos.find_one({"id_usuario": user_id})
        return json.dumps(carrito.dict() if carrito else {"error": "Carrito no encontrado"}, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def calcular_total_carrito(user_id: str) -> str:
    """Calcula total del carrito."""
    try:
        carrito = EcomerceCarritos.find_one({"id_usuario": user_id})
        if not carrito:
            return json.dumps({"total": 0})
        total = sum(item['precio'] * item['cantidad'] for item in carrito.items)
        return json.dumps({"total": total})
    except Exception as e:
        return json.dumps({"error": str(e)})

def verificar_registro_usuario(email: str) -> str:
    """Verifica si usuario está registrado."""
    try:
        db = next(get_db())
        usuario = db.query(EcomerceUsuarios).filter(EcomerceUsuarios.email == email).first()
        return json.dumps({"registrado": bool(usuario)})
    except Exception as e:
        return json.dumps({"error": str(e)})

def consultar_presupuestos_historicos(user_id: str) -> str:
    """Consulta presupuestos históricos."""
    try:
        presupuestos = Presupuesto.find({"id_usuario": user_id}).to_list()
        return json.dumps([p.dict() for p in presupuestos], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def consultar_ventas_por_usuario(user_id: str) -> str:
    """Consulta ventas (pedidos) por usuario."""
    try:
        ventas = EcomercePedidos.find({"id_usuario": user_id}).to_list()
        return json.dumps([v.dict() for v in ventas], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})

def consultar_ventas_por_fecha(fecha: str) -> str:
    """Consulta ventas por fecha."""
    try:
        fecha_obj = datetime.strptime(fecha, "%Y-%m-%d")
        ventas = EcomercePedidos.find({"fecha": {"$gte": fecha_obj, "$lt": fecha_obj.replace(hour=23, minute=59, second=59)}}).to_list()
        return json.dumps([v.dict() for v in ventas], default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})