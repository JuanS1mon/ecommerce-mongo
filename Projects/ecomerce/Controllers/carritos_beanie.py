"""
Controller para operaciones de carritos usando Beanie/MongoDB
"""
from typing import Optional, Dict, Any, List
from datetime import datetime
from ..models.carritos_beanie import EcomerceCarritos
import logging

logger = logging.getLogger(__name__)


async def get_carritos(cart_id: str) -> EcomerceCarritos:
    """
    Obtiene un carrito por su ID
    """
    carrito = await EcomerceCarritos.get(cart_id)
    if not carrito:
        raise ValueError(f"Carrito {cart_id} no encontrado")
    return carrito


async def get_cart_items(cart_id: str) -> List[Dict[str, Any]]:
    """
    Obtiene los items de un carrito con índices
    """
    carrito = await get_carritos(cart_id)
    if not carrito:
        return []
    
    # Agregar índice a cada item para poder identificarlo
    items_with_index = []
    for i, item in enumerate(carrito.items):
        item_copy = item.copy()
        item_copy["item_index"] = i
        items_with_index.append(item_copy)
    
    return items_with_index


async def add_simple_item_to_cart(
    user_id: str,
    product_id: int,
    quantity: int = 1,
    price: float = 0.0,
    variant_data: Optional[Dict[str, Any]] = None
) -> EcomerceCarritos:
    """
    Agrega un item al carrito del usuario de forma simple.
    Si el producto con la misma variante ya existe, incrementa la cantidad.
    Si no, crea un nuevo item.
    """
    try:
        # Buscar carrito activo del usuario
        carrito = await EcomerceCarritos.find_one(
            EcomerceCarritos.id_usuario == user_id,
            EcomerceCarritos.activo == True
        )

        # Si no existe, crear nuevo carrito
        if not carrito:
            logger.info(f"Creando nuevo carrito para usuario {user_id}")
            carrito = EcomerceCarritos(
                id_usuario=user_id,
                estado="activo",
                activo=True,
                items=[]
            )
            await carrito.insert()

        # Buscar si el item ya existe (mismo product_id y variant_data)
        existing_item = None
        for i, item in enumerate(carrito.items):
            # Comparar product_id y variant_data
            if (item.get("product_id") == product_id and 
                item.get("variant_data") == variant_data):
                existing_item = i
                break

        if existing_item is not None:
            # Item existe, incrementar cantidad
            logger.info(f"Item encontrado en índice {existing_item}, incrementando cantidad")
            carrito.items[existing_item]["quantity"] += quantity
        else:
            # Item no existe, agregar nuevo
            logger.info(f"Agregando nuevo item al carrito: product_id={product_id}, variant_data={variant_data}")
            new_item = {
                "product_id": product_id,
                "quantity": quantity,
                "price": price,
                "variant_data": variant_data,
                "added_at": datetime.utcnow()
            }
            carrito.items.append(new_item)

        # Guardar carrito
        await carrito.save()
        logger.info(f"Carrito actualizado exitosamente. Total items: {len(carrito.items)}")
        
        return carrito

    except Exception as e:
        logger.error(f"Error en add_simple_item_to_cart: {e}")
        raise


async def update_cart_item(
    cart_id: str,
    item_index: int,
    quantity: int
) -> EcomerceCarritos:
    """
    Actualiza la cantidad de un item del carrito
    """
    try:
        carrito = await get_carritos(cart_id)
        
        if item_index < 0 or item_index >= len(carrito.items):
            raise ValueError(f"Índice de item inválido: {item_index}")

        carrito.items[item_index]["quantity"] = quantity
        await carrito.save()
        
        return carrito

    except Exception as e:
        logger.error(f"Error en update_cart_item: {e}")
        raise


async def delete_cart_item(
    cart_id: str,
    item_index: int
) -> EcomerceCarritos:
    """
    Elimina un item del carrito
    """
    try:
        carrito = await get_carritos(cart_id)
        
        if item_index < 0 or item_index >= len(carrito.items):
            raise ValueError(f"Índice de item inválido: {item_index}")

        carrito.items.pop(item_index)
        await carrito.save()
        
        return carrito

    except Exception as e:
        logger.error(f"Error en delete_cart_item: {e}")
        raise
