"""
Servidor API simple para e-commerce (simulando MCP).
Expone endpoints para consultar productos, carritos, usuarios, presupuestos y ventas.
"""

from fastapi import FastAPI, HTTPException, Depends
from .tools import (
    listar_productos,
    buscar_producto_por_id,
    buscar_producto_por_nombre,
    buscar_producto_por_categoria,
    consultar_carrito_usuario,
    calcular_total_carrito,
    verificar_registro_usuario,
    consultar_presupuestos_historicos,
    consultar_ventas_por_usuario,
    consultar_ventas_por_fecha,
)
from .auth import validar_token

app = FastAPI(title="E-commerce API Server", version="1.0.0")

@app.get("/productos")
def get_productos():
    """Lista todos los productos."""
    return listar_productos()

@app.get("/productos/{product_id}")
def get_producto_por_id(product_id: str):
    """Busca producto por ID."""
    return buscar_producto_por_id(product_id)

@app.get("/productos/buscar/nombre")
def get_productos_por_nombre(nombre: str):
    """Busca productos por nombre."""
    return buscar_producto_por_nombre(nombre)

@app.get("/productos/buscar/categoria")
def get_productos_por_categoria(categoria: str):
    """Busca productos por categoría."""
    return buscar_producto_por_categoria(categoria)

@app.get("/carrito")
def get_carrito(token: str):
    """Consulta carrito de usuario (requiere auth)."""
    user_id = validar_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    return consultar_carrito_usuario(user_id)

@app.get("/carrito/total")
def get_total_carrito(token: str):
    """Calcula total del carrito (requiere auth)."""
    user_id = validar_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    return calcular_total_carrito(user_id)

@app.get("/usuarios/verificar")
def verificar_usuario(email: str):
    """Verifica si usuario está registrado."""
    return verificar_registro_usuario(email)

@app.get("/presupuestos")
def get_presupuestos(token: str):
    """Consulta presupuestos históricos (requiere auth)."""
    user_id = validar_token(token)
    if not user_id:
        raise HTTPException(status_code=401, detail="Token inválido")
    return consultar_presupuestos_historicos(user_id)

@app.get("/ventas/usuario/{user_id}")
def get_ventas_por_usuario(user_id: str):
    """Consulta ventas por usuario."""
    return consultar_ventas_por_usuario(user_id)

@app.get("/ventas/fecha")
def get_ventas_por_fecha(fecha: str):
    """Consulta ventas por fecha."""
    return consultar_ventas_por_fecha(fecha)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)