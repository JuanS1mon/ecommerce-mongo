from fastapi import APIRouter, HTTPException, status, Depends, Request
from fastapi.responses import HTMLResponse
from typing import List, Optional, Dict, Any
from pathlib import Path
from db.database import get_db
from security.ecommerce_auth import get_current_ecommerce_user
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy import text
# from db.schemas.config.Usuarios import UserDB
import logging
import traceback

# Imports locales del servicio
try:
    from ..schemas.carrito_items import Carrito_itemsCreate, Carrito_itemsUpdate, Carrito_itemsRead, Carrito_itemsSimpleCreate
except Exception:
    from Projects.ecomerce.schemas.carrito_items import Carrito_itemsCreate, Carrito_itemsUpdate, Carrito_itemsRead, Carrito_itemsSimpleCreate
try:
    from ..models.carrito_items import EcomerceCarrito_items
except Exception:
    from Projects.ecomerce.models.carrito_items import EcomerceCarrito_items

try:
    from ..Controllers.carrito_items import (
        create_carrito_items,
        get_carrito_items,
        gets_carrito_items,
        update_carrito_items,
        delete_carrito_items
    )
except Exception:
    # El módulo Controllers.carrito_items no está disponible en contextos de test aislados.
    # Definir stubs mínimos para que la importación del módulo funcione.
    def create_carrito_items(*args, **kwargs):
        raise NotImplementedError("Controllers.carrito_items no disponible en el entorno de test")

    def get_carrito_items(*args, **kwargs):
        raise NotImplementedError("Controllers.carrito_items no disponible en el entorno de test")

    def gets_carrito_items(*args, **kwargs):
        raise NotImplementedError("Controllers.carrito_items no disponible en el entorno de test")

    def update_carrito_items(*args, **kwargs):
        raise NotImplementedError("Controllers.carrito_items no disponible en el entorno de test")

    def delete_carrito_items(*args, **kwargs):
        raise NotImplementedError("Controllers.carrito_items no disponible en el entorno de test")
# Importaciones Beanie se hacen de manera lazy para evitar conflictos de inicialización
try:
    from ..Controllers.carritos_beanie import (
        get_cart_items,
        update_cart_item,
        delete_cart_item,
        add_simple_item_to_cart
    )
except Exception:
    from Projects.ecomerce.Controllers.carritos_beanie import (
        get_cart_items,
        update_cart_item,
        delete_cart_item,
        add_simple_item_to_cart
    )
from pydantic import BaseModel, ConfigDict

# Modelos Pydantic para validación de carrito_items Beanie
class AddToCartRequest(BaseModel):
    product_id: int
    quantity: int = 1
    price: float = 0.0
    variant_data: Optional[Dict[str, Any]] = None
    model_config = ConfigDict(from_attributes=True)

class UpdateCartItemRequest(BaseModel):
    cantidad: int
    model_config = ConfigDict(from_attributes=True)

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["carrito_items"],
    responses={status.HTTP_404_NOT_FOUND: {"message": "ruta no encontrada"}}
)

security = HTTPBearer()

async def get_current_ecommerce_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(HTTPBearer(auto_error=False)),
    db: Session = Depends(get_db)
):
    """
    Dependencia para obtener el usuario ecommerce actual
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token de autenticación requerido"
        )

    user = await get_current_ecommerce_user(credentials.credentials)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido o expirado"
        )

    return user

@router.post("/", response_model=Carrito_itemsRead, status_code=status.HTTP_201_CREATED)
async def routes_post_carrito_items(carrito_items: Carrito_itemsCreate, request: Request, user: dict = Depends(get_current_ecommerce_user_dependency), db: Session = Depends(get_db)):
    try:
        # Convertir a dict y limpiar valores None/unset (especialmente PK autoincrement)
        carrito_items_payload = carrito_items.model_dump(exclude_unset=True, exclude_none=True)

        # Eliminar explícitamente 'id' si existe y es None (PK autoincrement)
        if 'id' in carrito_items_payload and carrito_items_payload['id'] is None:
            del carrito_items_payload['id']

        # Crear user_data dict para compatibilidad con el controlador
        user_data = {
            "codigo": user["id"],  # Usar 'id' en lugar de 'codigo' para usuarios ecommerce
            "usuario": user["email"],  # Usar email como usuario
            "nombre": user["nombre"],
            "email": user["email"],
            "roles": []  # Usuarios ecommerce no tienen roles del sistema
        }

        db_carrito_items = create_carrito_items(db=db, carrito_items=carrito_items_payload, user_data=user_data, request=request)
        return Carrito_itemsRead.model_validate(db_carrito_items)
    except Exception as e:
        logger.error(f"Error al crear Carrito_items: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al crear el registro.")


@router.post("/simple", response_model=Carrito_itemsRead, status_code=status.HTTP_201_CREATED)
async def routes_post_carrito_items_simple(
    item_data: Carrito_itemsSimpleCreate,
    request: Request,
    user: dict = Depends(get_current_ecommerce_user_dependency),
    db: Session = Depends(get_db)
):
    """
    Ruta simplificada para agregar productos al carrito.
    Crea automáticamente el carrito si no existe uno activo.
    """
    try:
        logger.info(f"Datos recibidos en /simple: {item_data}")
        logger.info(f"Tipos de datos: product_id={type(item_data.product_id)}, quantity={type(item_data.quantity)}, price={type(item_data.price)}")

        product_id = item_data.product_id
        quantity = item_data.quantity
        price = item_data.price

        logger.info(f"Valores extraídos: product_id={product_id}, quantity={quantity}, price={price}")

        # Validaciones adicionales
        if not isinstance(product_id, int) or product_id <= 0:
            logger.error(f"product_id inválido: {product_id} (tipo: {type(product_id)})")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de producto inválido")

        if not isinstance(quantity, int) or quantity <= 0:
            logger.error(f"quantity inválido: {quantity} (tipo: {type(quantity)})")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cantidad inválida")

        if not isinstance(price, (int, float)) or price < 0:
            logger.error(f"price inválido: {price} (tipo: {type(price)})")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Precio inválido")

        # Convertir precio a int para compatibilidad con el modelo
        price_int = int(price) if price else 0

        logger.info(f"Usando valores finales: product_id={product_id}, quantity={quantity}, price_int={price_int}")

        # Usar la nueva clase Cart
        import sys
        import os
        sys.path.append(os.path.join(os.path.dirname(__file__), '../../..'))
        from Services.cart_service import Cart

        cart = Cart(db, user["id"])  # Usar user["id"] para usuarios ecommerce
        item = cart.add_item(product_id, quantity, price_int)

        logger.info(f"Item agregado exitosamente: {item}")

        # Crear objeto de respuesta
        from ..models.carrito_items import EcomerceCarrito_items
        db_item = EcomerceCarrito_items()
        db_item.id = item['id']
        db_item.id_carrito = item['id_carrito']
        db_item.id_producto = item['id_producto']
        db_item.cantidad = item['cantidad']
        db_item.precio_unitario = item['precio_unitario']

        return Carrito_itemsRead.model_validate(db_item)

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al agregar producto al carrito: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al agregar producto al carrito.")


@router.get("/id/{id}", response_model=Carrito_itemsRead)
async def routes_get_carrito_items_id(id: int, db: Session = Depends(get_db)):
    try:
        db_carrito_items = get_carrito_items(db, id)
        if not db_carrito_items:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Route: carrito_items no encontrado")
        return Carrito_itemsRead.model_validate(db_carrito_items)
    except Exception as e:
        logger.error(f"Error al obtener Carrito_items: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener el registro.")


@router.get("/", response_model=List[Carrito_itemsRead])
async def routes_gets_carrito_items_all(db: Session = Depends(get_db)):
    try:
        db_carrito_items = gets_carrito_items(db)
        # Una lista vacía es un resultado válido, no un error
        return [Carrito_itemsRead.model_validate(carrito_items) for carrito_items in db_carrito_items]
    except Exception as e:
        logger.error(f"Error al obtener registros de Carrito_items: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener los registros.")


@router.delete("/id/{id}", response_model=Carrito_itemsRead)
async def routes_delete_carrito_items_numero(id: int, request: Request, user: dict = Depends(get_current_ecommerce_user_dependency), db: Session = Depends(get_db)):
    try:
        # Verificar que el item pertenece al usuario actual
        item_result = db.execute(
            text("""
                SELECT ci.id, ci.id_carrito, ci.id_producto, ci.cantidad, ci.precio_unitario
                FROM ecomerce_carrito_items ci
                INNER JOIN ecomerce_carritos c ON ci.id_carrito = c.id
                WHERE ci.id = :item_id AND c.id_usuario = :user_id AND c.estado = 'activo'
            """),
            {"item_id": id, "user_id": user["id"]}  # Usar user["id"] para usuarios ecommerce
        ).first()

        if not item_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado o no pertenece al usuario")

        # Eliminar el item
        delete_query = text("""
            DELETE FROM ecomerce_carrito_items
            OUTPUT DELETED.id, DELETED.id_carrito, DELETED.id_producto, DELETED.cantidad, DELETED.precio_unitario
            WHERE id = :item_id
        """)
        result = db.execute(delete_query, {"item_id": id})
        row = result.first()

        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar el item")

        db.commit()

        # Crear objeto de respuesta (compatibilidad frontend)
        item_obj = {
            'id': row[0],
            'id_carrito': row[1],
            'id_producto': row[2],
            'cantidad': row[3],
            'precio_unitario': row[4],
            'product_id': row[2],
            'quantity': row[3],
            'price': row[4]
        }

        return item_obj
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al eliminar Carrito_items: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al eliminar el registro.")


@router.put("/id/{id}", response_model=Carrito_itemsRead)
async def routes_update_carrito_items(id: int, carrito_items: Carrito_itemsUpdate, request: Request, user: dict = Depends(get_current_ecommerce_user_dependency), db: Session = Depends(get_db)):
    logger.info(f"Actualizando Carrito_items con id = {id}")
    try:
        # Verificar que el item pertenece al usuario actual
        item_result = db.execute(
            text("""
                SELECT ci.id, ci.id_carrito, ci.id_producto, ci.cantidad, ci.precio_unitario
                FROM ecomerce_carrito_items ci
                INNER JOIN ecomerce_carritos c ON ci.id_carrito = c.id
                WHERE ci.id = :item_id AND c.id_usuario = :user_id AND c.estado = 'activo'
            """),
            {"item_id": id, "user_id": user["id"]}  # Usar user["id"] para usuarios ecommerce
        ).first()

        if not item_result:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item no encontrado o no pertenece al usuario")

        # Actualizar la cantidad
        new_quantity = carrito_items.cantidad
        if new_quantity <= 0:
            # Si la cantidad es 0 o menor, eliminar el item
            return await routes_delete_carrito_items_numero(id, request, user, db)

        update_query = text("""
            UPDATE ecomerce_carrito_items
            SET cantidad = :quantity
            OUTPUT INSERTED.id, INSERTED.id_carrito, INSERTED.id_producto, INSERTED.cantidad, INSERTED.precio_unitario
            WHERE id = :item_id
        """)
        result = db.execute(update_query, {"quantity": new_quantity, "item_id": id})
        row = result.first()

        if not row:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar el item")

        db.commit()

        # Crear objeto de respuesta (compatibilidad frontend)
        item_obj = {
            'id': row[0],
            'id_carrito': row[1],
            'id_producto': row[2],
            'cantidad': row[3],
            'precio_unitario': row[4],
            'product_id': row[2],
            'quantity': row[3],
            'price': row[4]
        }

        return item_obj
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error al actualizar Carrito_items: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al actualizar el registro.")


@router.get("/pagina", response_class=HTMLResponse)
async def get_pagina():
    try:
        # Buscar solo en la carpeta templates del proyecto
        script_dir = Path(__file__).resolve().parent
        html_path = script_dir.parent / "templates" / f"carrito_items.html"
        if not html_path.exists():
            raise FileNotFoundError(f"No se encontró la página HTML: {html_path}")
        html_content = html_path.read_text(encoding="utf-8")
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error al obtener la pagina HTML: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener la pagina HTML.")


@router.get("/carrito/{carrito_id}", response_model=List[Carrito_itemsRead])
def routes_get_carrito_items_por_carrito(carrito_id: str, user: dict = Depends(get_current_ecommerce_user_dependency), db: Session = Depends(get_db)):
    try:
        # Obtener items del carrito usando SQL directo
        result = db.execute(
            text("SELECT id, id_carrito, id_producto, cantidad, precio_unitario FROM ecomerce_carrito_items WHERE id_carrito = :carrito_id"),
            {"carrito_id": carrito_id}
        )

        items = []
        for row in result.fetchall():
            # Construir objeto de respuesta incluyendo campos amigables para frontend:
            # id_producto -> product_id, cantidad -> quantity, precio_unitario -> price
            item_obj = {
                'id': row[0],
                'id_carrito': row[1],
                'id_producto': row[2],
                'cantidad': row[3],
                'precio_unitario': row[4],
                # Campos adicionales para compatibilidad con frontend JS
                'product_id': row[2],
                'quantity': row[3],
                'price': row[4]
            }
            items.append(item_obj)

        return items
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error al obtener items del carrito: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error al obtener los items del carrito.")

# =============================
# CARRITO_ITEMS - Rutas Beanie
# =============================

@router.get("/carrito/{cart_id}")
async def get_carrito_items_beanie(
    cart_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Obtiene todos los items de un carrito específico usando Beanie/MongoDB
    """
    try:
        # Import lazy para evitar conflictos de inicialización
        from ..Controllers.carritos_beanie import get_carritos, get_cart_items

        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        # Verificar que el carrito pertenece al usuario
        carrito = await get_carritos(cart_id)
        if str(carrito.id_usuario) != str(user['id']):
            raise HTTPException(status_code=403, detail="No autorizado para acceder a este carrito")

        # Obtener items del carrito
        items = await get_cart_items(cart_id)

        # Enriquecer items con información del producto (simulado por ahora)
        enriched_items = []
        for item in items:
            enriched_item = item.copy()
            # Aquí podríamos agregar lógica para obtener info del producto desde MongoDB
            # Por ahora, usamos valores por defecto
            enriched_item.update({
                "id": item.get("item_index", 0),  # Usar el índice como ID temporal
                "id_carrito": cart_id,
                "id_producto": item.get("product_id", 0),
                "cantidad": item.get("quantity", 1),
                "precio_unitario": item.get("price", 0.0),
                "product_name": f"Producto {item.get('product_id', 'N/A')}",
                "product_image": "/static/img/logo.png",
                "product_codigo": f"P{item.get('product_id', '000')}",
                "variant_data": item.get("variant_data"),  # Incluir variant_data del item
                "created_at": item.get("added_at"),
                "updated_at": None
            })
            enriched_items.append(enriched_item)

        return enriched_items

    except Exception as e:
        logger.error(f"Error obteniendo items del carrito {cart_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.post("/simple")
async def add_to_cart_simple_beanie(
    cart_request: AddToCartRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Agrega un producto al carrito de forma simple usando Beanie/MongoDB
    """
    try:
        # Import lazy para evitar conflictos de inicialización
        from ..Controllers.carritos_beanie import add_simple_item_to_cart

        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        # Agregar item al carrito
        carrito = await add_simple_item_to_cart(
            user_id=str(user['id']),
            product_id=cart_request.product_id,
            quantity=cart_request.quantity,
            price=cart_request.price,
            variant_data=cart_request.variant_data
        )

        return {
            "message": "Producto agregado al carrito exitosamente",
            "carrito_id": str(carrito.id),
            "total_items": len(carrito.items)
        }

    except Exception as e:
        logger.error(f"Error agregando producto al carrito: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/id/{item_index}")
async def update_carrito_item_beanie(
    item_index: int,
    cart_update: UpdateCartItemRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Actualiza la cantidad de un item del carrito usando Beanie/MongoDB
    """
    try:
        # Import lazy para evitar conflictos de inicialización
        from ..Controllers.carritos_beanie import get_or_create_active_cart, update_cart_item, delete_cart_item

        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        # Obtener carrito activo del usuario
        carrito_activo = await get_or_create_active_cart(str(user['id']))
        cart_id = str(carrito_activo.id)

        # Verificar que el índice del item es válido
        if item_index < 0 or item_index >= len(carrito_activo.items):
            raise HTTPException(status_code=404, detail="Item no encontrado en el carrito")

        cantidad = cart_update.cantidad

        if cantidad <= 0:
            # Si cantidad es 0 o negativa, eliminar el item
            carrito = await delete_cart_item(cart_id, item_index)
            return {
                "message": "Item eliminado del carrito",
                "carrito_id": str(carrito.id),
                "total_items": len(carrito.items)
            }
        else:
            # Actualizar cantidad del item
            update_data = {"quantity": cantidad}
            carrito = await update_cart_item(cart_id, item_index, update_data)
            return {
                "message": "Item actualizado exitosamente",
                "carrito_id": str(carrito.id),
                "item_index": item_index,
                "new_quantity": cantidad,
                "total_items": len(carrito.items)
            }

    except Exception as e:
        logger.error(f"Error actualizando item {item_index} del carrito: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/id/{item_index}")
async def delete_carrito_item_beanie(
    item_index: int,
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """
    Elimina un item del carrito usando Beanie/MongoDB
    """
    try:
        # Import lazy para evitar conflictos de inicialización
        from ..Controllers.carritos_beanie import get_or_create_active_cart, delete_cart_item

        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        # Obtener carrito activo del usuario
        carrito_activo = await get_or_create_active_cart(str(user['id']))
        cart_id = str(carrito_activo.id)

        # Eliminar el item
        carrito = await delete_cart_item(cart_id, item_index)

        return {
            "message": "Item eliminado del carrito exitosamente",
            "carrito_id": str(carrito.id),
            "total_items": len(carrito.items)
        }

    except Exception as e:
        logger.error(f"Error eliminando item {item_index} del carrito: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
