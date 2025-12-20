from fastapi import APIRouter, HTTPException, Depends, Form, Request, Body
from fastapi.responses import JSONResponse
from db.database import get_database
import logging
from datetime import datetime
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from security.ecommerce_auth import get_current_ecommerce_user
from pydantic import BaseModel, ConfigDict
from typing import Optional
from Projects.ecomerce.models.carritos_beanie import EcomerceCarritos
from Projects.ecomerce.models.productos_beanie import EcomerceProductos

logger = logging.getLogger(__name__)

router = APIRouter()
security = HTTPBearer()

# Modelos Pydantic para validación
class AddToCartRequest(BaseModel):
    product_id: str  # ID del producto (ObjectId)
    quantity: int = 1
    price: float = 0.0
    variant_data: Optional[dict] = None
    model_config = ConfigDict(from_attributes=True)

class UpdateCartItemRequest(BaseModel):
    cantidad: int
    model_config = ConfigDict(from_attributes=True)

# =============================
# CARRITO - Rutas principales
# =============================

@router.post("/test")
async def test_endpoint(
    data: dict = Body(...)
):
    """
    Endpoint de prueba para verificar parsing JSON
    """
    print(f"Received data: {data}")
    return {"received": data, "status": "ok"}

@router.post("/carrito_items/simple")
async def add_to_cart_simple(
    cart_request: AddToCartRequest = Body(...),
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Agrega un producto al carrito de forma simple (crea carrito si no existe)
    """
    try:
        logger.info(f"📥 Recibiendo solicitud de agregar al carrito: {cart_request.dict()}")
        
        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        user_id = user['id']
        product_id = cart_request.product_id
        quantity = cart_request.quantity
        price = cart_request.price
        variant_data = cart_request.variant_data

        # Verificar que el producto existe y está activo
        from beanie import PydanticObjectId
        product = None
        
        # Intentar primero como ObjectId
        try:
            product = await EcomerceProductos.get(PydanticObjectId(product_id))
        except:
            # Si no es ObjectId válido, buscar por código
            product = await EcomerceProductos.find_one(
                EcomerceProductos.codigo == product_id,
                EcomerceProductos.active == True
            )
        
        if not product:
            raise HTTPException(status_code=404, detail="Producto no encontrado")

        # Si hay variant_data, intentar validar la variante (pero no es obligatorio que exista)
        if variant_data:
            from Projects.ecomerce.models.productos_beanie import EcomerceProductosVariantes
            
            # Construir query dinámica para buscar la variante
            query_conditions = [
                EcomerceProductosVariantes.product_id == str(product.id),
                EcomerceProductosVariantes.active == True
            ]
            
            # Agregar condiciones para cada campo de variant_data
            for key, value in variant_data.items():
                if key == 'color' and hasattr(EcomerceProductosVariantes, 'color'):
                    query_conditions.append(EcomerceProductosVariantes.color == value)
                elif key == 'tipo' and hasattr(EcomerceProductosVariantes, 'tipo'):
                    query_conditions.append(EcomerceProductosVariantes.tipo == value)
                elif key == 'talla' and hasattr(EcomerceProductosVariantes, 'talla'):
                    query_conditions.append(EcomerceProductosVariantes.talla == value)
            
            # Intentar encontrar la variante
            try:
                variant = await EcomerceProductosVariantes.find_one(*query_conditions)
                
                if variant:
                    logger.info(f"✅ Variante encontrada: {variant.dict()}")
                    # Validar stock solo si encontramos la variante
                    if variant.stock < quantity:
                        raise HTTPException(status_code=400, detail=f"Stock insuficiente para la variante seleccionada. Disponible: {variant.stock}")
                    
                    # Ajustar precio con precio adicional de la variante
                    price += variant.precio_adicional
                else:
                    # No se encontró la variante exacta, pero permitir agregar el producto base
                    logger.warning(f"⚠️ Variante no encontrada para producto {product_id} con datos: {variant_data}")
                    logger.info(f"✅ Permitiendo agregar producto base sin variante específica")
            except Exception as e:
                # Si hay algún error buscando la variante, simplemente usar el producto base
                logger.warning(f"⚠️ Error buscando variante: {e}")
                logger.info(f"✅ Usando producto base")
        else:
            # Si no hay variante pero el producto tiene variantes, usar el producto base
            # Las variantes son opcionales - el usuario puede agregar el producto base sin variante
            from Projects.ecomerce.models.productos_beanie import EcomerceProductosVariantes
            variants = await EcomerceProductosVariantes.find(
                EcomerceProductosVariantes.product_id == str(product.id),
                EcomerceProductosVariantes.active == True
            ).to_list()
            # No lanzar error - permitir agregar producto sin variante
            # Las variantes son una opción, no un requisito

        # Usar el precio del producto si no se especificó uno
        if price <= 0:
            price = product.precio

        # Buscar carrito activo del usuario
        cart = await EcomerceCarritos.find_one(
            EcomerceCarritos.id_usuario == user_id,
            EcomerceCarritos.estado == "activo"
        )

        if not cart:
            # Crear nuevo carrito
            cart = EcomerceCarritos(
                id_usuario=user_id,
                estado="activo",
                items=[]
            )

        # Verificar si el producto ya está en el carrito (considerando variante)
        existing_item = next((item for item in cart.items if 
                            item.get("product_id") == str(product.id) and 
                            item.get("variant_data") == variant_data), None)

        if existing_item:
            # Validar stock antes de actualizar cantidad (solo si hay variante y se puede validar)
            if variant_data:
                from Projects.ecomerce.models.productos_beanie import EcomerceProductosVariantes
                
                # Construir query dinámica similar a la búsqueda anterior
                query_conditions = [
                    EcomerceProductosVariantes.product_id == str(product.id),
                    EcomerceProductosVariantes.active == True
                ]
                
                for key, value in variant_data.items():
                    if key == 'color' and hasattr(EcomerceProductosVariantes, 'color'):
                        query_conditions.append(EcomerceProductosVariantes.color == value)
                    elif key == 'tipo' and hasattr(EcomerceProductosVariantes, 'tipo'):
                        query_conditions.append(EcomerceProductosVariantes.tipo == value)
                    elif key == 'talla' and hasattr(EcomerceProductosVariantes, 'talla'):
                        query_conditions.append(EcomerceProductosVariantes.talla == value)
                
                try:
                    variant = await EcomerceProductosVariantes.find_one(*query_conditions)
                    if variant and variant.stock > 0:
                        nueva_cantidad = existing_item["quantity"] + quantity
                        if nueva_cantidad > variant.stock:
                            raise HTTPException(status_code=400, detail=f"No hay suficiente stock. Disponible: {variant.stock - existing_item['quantity']}")
                except Exception as e:
                    # Si no se puede validar stock, permitir agregar de todas formas
                    logger.warning(f"⚠️ No se pudo validar stock para variante: {e}")

            # Actualizar cantidad existente
            existing_item["quantity"] += quantity
            logger.info(f"✅ Cantidad actualizada para producto existente. Nueva cantidad: {existing_item['quantity']}")
        else:
            # Agregar nuevo item
            import uuid
            item_id = str(uuid.uuid4())
            cart.items.append({
                "id": item_id,  # unique item id
                "product_id": str(product.id),
                "quantity": quantity,
                "price": price,
                "variant_data": variant_data,
                "product_name": product.nombre or f"Producto {product_id}",
                "product_image": product.imagen_url or "/static/img/logo.png",
                "product_codigo": product.codigo or ""
            })

        await cart.save()

        return {
            "message": "Producto agregado al carrito",
            "cart_id": str(cart.id),
            "product_id": str(product.id),
            "quantity": quantity,
            "variant_data": variant_data
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error agregando producto al carrito: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/carrito_items/carrito/{cart_id}")
async def get_carrito_items(
    cart_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Obtiene todos los items de un carrito específico
    """
    try:
        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        # Buscar el carrito
        from beanie import PydanticObjectId
        cart = await EcomerceCarritos.find_one(
            EcomerceCarritos.id == PydanticObjectId(cart_id),
            EcomerceCarritos.id_usuario == user['id']
        )

        if not cart:
            raise HTTPException(status_code=404, detail="Carrito no encontrado")

        # Retornar los items
        items = []
        for item in cart.items:
            # Handle both old (id_producto) and new (product_id) field names
            product_id = item.get("product_id") or item.get("id_producto")
            items.append({
                "id": item.get("id"),
                "cart_id": cart_id,
                "product_id": product_id,
                "quantity": item.get("quantity") or item.get("cantidad", 0),
                "price": item.get("price") or item.get("precio_unitario", 0),
                "variant_data": item.get("variant_data"),
                "product_name": item.get("product_name", ""),
                "product_image": item.get("product_image", ""),
                "product_codigo": item.get("product_codigo", "")
            })

        return items

    except Exception as e:
        logger.error(f"Error obteniendo items del carrito {cart_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.put("/carrito_items/id/{item_id}")
async def update_carrito_item(
    item_id: str,
    cart_update: UpdateCartItemRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Actualiza la cantidad de un item del carrito
    """
    try:
        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        cantidad = cart_update.cantidad

        # Buscar carrito activo del usuario
        cart = await EcomerceCarritos.find_one(
            EcomerceCarritos.id_usuario == user['id'],
            EcomerceCarritos.estado == "activo"
        )

        if not cart:
            raise HTTPException(status_code=404, detail="Carrito no encontrado")

        # Encontrar el item
        item = next((i for i in cart.items if i.get("id") == item_id), None)

        if not item:
            raise HTTPException(status_code=404, detail="Item no encontrado")

        if cantidad <= 0:
            # Eliminar el item
            cart.items = [i for i in cart.items if i.get("id") != item_id]
        else:
            # Actualizar cantidad
            item["quantity"] = cantidad

        await cart.save()
        return {"message": "Item actualizado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error actualizando item {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.delete("/carrito_items/id/{item_id}")
async def delete_carrito_item(
    item_id: str,
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Elimina un item del carrito
    """
    try:
        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        # Buscar carrito activo del usuario
        cart = await EcomerceCarritos.find_one(
            EcomerceCarritos.id_usuario == user['id'],
            EcomerceCarritos.estado == "activo"
        )

        if not cart:
            raise HTTPException(status_code=404, detail="Carrito no encontrado")

        # Encontrar y eliminar el item
        original_length = len(cart.items)
        cart.items = [i for i in cart.items if i.get("id") != item_id]

        if len(cart.items) == original_length:
            raise HTTPException(status_code=404, detail="Item no encontrado")

        await cart.save()
        return {"message": "Item eliminado"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error eliminando item {item_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")

@router.get("/carritos/activo")
async def get_carrito_activo(
    credentials: HTTPAuthorizationCredentials = Depends(security),
):
    """
    Obtiene el carrito activo del usuario autenticado, o crea uno si no existe
    """
    try:
        # Obtener usuario del token JWT
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail="Token inválido o usuario no encontrado")

        user_id = user['id']

        # Buscar carrito activo del usuario
        cart = await EcomerceCarritos.find_one(
            EcomerceCarritos.id_usuario == user_id,
            EcomerceCarritos.estado == "activo"
        )

        if cart:
            # Carrito activo encontrado
            return {
                "id": str(cart.id),
                "id_usuario": cart.id_usuario,
                "estado": cart.estado,
                "created_at": cart.created_at.isoformat() if cart.created_at else None,
                "updated_at": cart.created_at.isoformat() if cart.created_at else None
            }
        else:
            # No hay carrito activo, crear uno nuevo
            logger.info(f"Creando carrito activo para usuario {user_id}")
            cart = EcomerceCarritos(
                id_usuario=user_id,
                estado="activo",
                items=[]
            )
            await cart.insert()
            return {
                "id": str(cart.id),
                "id_usuario": cart.id_usuario,
                "estado": cart.estado,
                "created_at": cart.created_at.isoformat() if cart.created_at else None,
                "updated_at": cart.created_at.isoformat() if cart.created_at else None
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo carrito activo para usuario {user_id}: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor")
