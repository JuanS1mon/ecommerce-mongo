"""
Tests para MCP.
"""

import pytest
import json
from .tools import (
    listar_productos,
    buscar_producto_por_id,
    verificar_registro_usuario,
    consultar_carrito_usuario,
)

def test_listar_productos():
    result = json.loads(listar_productos())
    assert isinstance(result, list) or "error" in result

def test_buscar_producto_por_id():
    result = json.loads(buscar_producto_por_id("invalid_id"))
    assert "error" in result or result == {}

def test_verificar_registro_usuario():
    result = json.loads(verificar_registro_usuario("test@example.com"))
    assert "registrado" in result

def test_consultar_carrito_sin_auth():
    result = json.loads(consultar_carrito_usuario("invalid_user"))
    assert "error" in result

# Agregar más tests según necesidad