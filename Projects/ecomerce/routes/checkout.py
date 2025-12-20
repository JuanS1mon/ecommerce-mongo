"""
Router de checkout para procesamiento de pagos
Maneja la configuración y procesamiento de pagos con MercadoPago
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from fastapi import Request
from pydantic import BaseModel
from typing import Optional
import os
from dotenv import load_dotenv
import mercadopago

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Configurar templates
templates = Jinja2Templates(directory="Projects/ecomerce/templates")

router = APIRouter(
    prefix="/checkout",
    tags=["checkout"],
)

# Seguridad
security = HTTPBearer()

# Modelos Pydantic
class MercadoPagoConfig(BaseModel):
    public_key: Optional[str] = None
    configured: bool = False
    environment: str = "test"

@router.get("/config/mercadopago")
async def get_mercadopago_config():
    """
    Obtiene la configuración de MercadoPago para el frontend
    """
    try:
        # Obtener la public key de MercadoPago desde variables de entorno
        public_key = os.getenv("MERCADOPAGO_PUBLIC_KEY")

        config = MercadoPagoConfig(
            public_key=public_key,
            configured=bool(public_key),
            environment=os.getenv("MERCADOPAGO_ENVIRONMENT", "test")
        )

        logger.info(f"Configuración de MercadoPago solicitada - Configurada: {config.configured}")

        return config.dict()

    except Exception as e:
        logger.error(f"Error obteniendo configuración de MercadoPago: {e}")
        raise HTTPException(
            status_code=500,
            detail="Error interno del servidor"
        )

@router.post("/")
async def process_checkout(data: dict, credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Procesa el checkout de un carrito para métodos: efectivo y presupuesto
    """
    try:
        # Validar método de pago
        payment_method = (data or {}).get('payment_method')
        if not payment_method:
            raise HTTPException(status_code=400, detail='payment_method es requerido')

        # Obtener datos de envío
        shipping_data = (data or {}).get('shipping_data', {})

        # Autenticar usuario ecommerce
        from security.ecommerce_auth import get_current_ecommerce_user
        user = await get_current_ecommerce_user(credentials.credentials)
        if not user:
            raise HTTPException(status_code=401, detail='Usuario no autenticado')

        # Obtener carrito activo del usuario
        from Projects.ecomerce.models.carritos_beanie import EcomerceCarritos
        cart = await EcomerceCarritos.find_one(
            EcomerceCarritos.id_usuario == user['id'],
            EcomerceCarritos.estado == 'activo'
        )

        if not cart or not cart.items:
            raise HTTPException(status_code=400, detail='El carrito está vacío')

        # Calcular totales
        total = 0
        for it in cart.items:
            qty = it.get('quantity') or it.get('cantidad') or 1
            price = it.get('price') or it.get('precio_unitario') or 0
            total += qty * price

        # Crear registro de pedido
        from Projects.ecomerce.models.pedidos_beanie import EcomercePedidos

        order_status = 'pendiente'
        if payment_method == 'presupuesto':
            order_status = 'presupuesto'
        elif payment_method == 'efectivo':
            order_status = 'pendiente_pago_efectivo'

        pedido = EcomercePedidos(
            id_usuario=str(user['id']),
            items=cart.items,
            total=total,
            estado=order_status,
            metodo_pago=payment_method
        )
        await pedido.insert()

        # Enviar correos según método
        from Services.mail.mail import enviar_email_simple
        admin_email = os.getenv('ADMIN_EMAIL') or os.getenv('MAIL_FROM')
        company_phone = os.getenv('COMPANY_PHONE') or ''
        user_email = user.get('email')

        # Guardar información de contacto de empresa y datos de envío en pedido
        pedido.contacto = {
            'empresa_email': admin_email, 
            'empresa_phone': company_phone, 
            'usuario_email': user_email
        }
        
        # Guardar datos de envío si existen
        if shipping_data:
            pedido.datos_envio = shipping_data
        
        await pedido.save()

        # Mensajes
        if payment_method == 'efectivo':
            # Preparar detalles de productos para el email
            productos_html = ""
            productos_text = ""
            
            for item in cart.items:
                producto_nombre = item.get('product_name', 'Producto')
                producto_imagen = item.get('product_image', '/static/img/logo.png')
                producto_precio = item.get('price', 0)
                producto_cantidad = item.get('quantity', 1)
                subtotal = producto_precio * producto_cantidad
                
                # Obtener información de variantes si existen
                variant_data = item.get('variant_data')
                variante_info = ""
                variante_info_html = ""
                
                if variant_data and isinstance(variant_data, dict):
                    variantes = []
                    for key, value in variant_data.items():
                        variantes.append(f"{key.capitalize()}: {value}")
                    
                    if variantes:
                        variante_info = f" ({', '.join(variantes)})"
                        variante_info_html = f"""<div style="color: #6b7280; font-size: 13px; margin-top: 3px;">🎨 {', '.join(variantes)}</div>"""
                
                # HTML para email del cliente
                productos_html += f"""
                <tr>
                    <td style="padding: 15px; border-bottom: 1px solid #e5e7eb;">
                        <div style="display: flex; align-items: center;">
                            <img src="{producto_imagen}" alt="{producto_nombre}" 
                                 style="width: 80px; height: 80px; object-fit: cover; border-radius: 8px; margin-right: 15px;">
                            <div>
                                <div style="font-weight: 600; color: #111827; margin-bottom: 5px;">{producto_nombre}</div>
                                {variante_info_html}
                                <div style="color: #6b7280; font-size: 14px;">Cantidad: {producto_cantidad}</div>
                            </div>
                        </div>
                    </td>
                    <td style="padding: 15px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: 600; color: #111827;">
                        ${subtotal:,.0f}
                    </td>
                </tr>
                """
                
                # Texto para email del admin
                productos_text += f"\n  • {producto_nombre}{variante_info} - Cantidad: {producto_cantidad} - Precio: ${producto_precio:,.0f} - Subtotal: ${subtotal:,.0f}"
            
            # Correo al usuario (HTML)
            subject_user = 'Confirmación de pedido - Pago en efectivo'
            msg_user = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 20px;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                <!-- Header -->
                                <tr>
                                    <td style="background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%); padding: 40px 30px; text-align: center;">
                                        <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">
                                            ✅ Pedido Confirmado
                                        </h1>
                                        <p style="margin: 10px 0 0 0; color: #e0e7ff; font-size: 16px;">
                                            Gracias por tu compra
                                        </p>
                                    </td>
                                </tr>
                                
                                <!-- Body -->
                                <tr>
                                    <td style="padding: 30px;">
                                        <p style="margin: 0 0 20px 0; color: #111827; font-size: 16px; line-height: 1.6;">
                                            Hemos recibido tu pedido correctamente. Te contactaremos pronto para coordinar la entrega.
                                        </p>
                                        
                                        <!-- Order Info -->
                                        <div style="background-color: #f9fafb; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                                            <p style="margin: 0 0 10px 0; color: #6b7280; font-size: 14px; font-weight: 600; text-transform: uppercase;">
                                                Número de Pedido
                                            </p>
                                            <p style="margin: 0; color: #111827; font-size: 18px; font-weight: 700; font-family: monospace;">
                                                #{str(pedido.id)[:8]}...
                                            </p>
                                        </div>
                                        
                                        <!-- Products -->
                                        <h2 style="margin: 0 0 15px 0; color: #111827; font-size: 20px; font-weight: 600;">
                                            📦 Productos
                                        </h2>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; margin-bottom: 25px;">
                                            {productos_html}
                                        </table>
                                        
                                        <!-- Total -->
                                        <div style="background-color: #f0f9ff; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                                <span style="color: #0369a1; font-size: 18px; font-weight: 600;">Total:</span>
                                                <span style="color: #0369a1; font-size: 24px; font-weight: 700;">${total:,.0f}</span>
                                            </div>
                                            <p style="margin: 10px 0 0 0; color: #075985; font-size: 14px;">
                                                💵 Pago en efectivo al recibir
                                            </p>
                                        </div>
                                        
                                        <!-- Contact Info -->
                                        <div style="border-top: 2px solid #e5e7eb; padding-top: 20px;">
                                            <h3 style="margin: 0 0 15px 0; color: #111827; font-size: 18px; font-weight: 600;">
                                                📞 Información de contacto
                                            </h3>
                                            <p style="margin: 0 0 8px 0; color: #4b5563; font-size: 15px;">
                                                <strong>Email:</strong> {admin_email or 'No especificado'}
                                            </p>
                                            <p style="margin: 0; color: #4b5563; font-size: 15px;">
                                                <strong>Teléfono:</strong> {company_phone or 'No especificado'}
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                                
                                <!-- Footer -->
                                <tr>
                                    <td style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="margin: 0; color: #6b7280; font-size: 14px;">
                                            Si tienes alguna pregunta, no dudes en contactarnos.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            try:
                enviar_email_simple(user_email, subject_user, msg_user)
            except Exception as e:
                logger.error(f"Error enviando correo al usuario: {e}")

            # Correo al admin (HTML mejorado)
            if admin_email:
                # Preparar información del cliente
                cliente_nombre = user.get('nombre', 'No especificado')
                cliente_telefono = user.get('telefono') or shipping_data.get('telefono') or 'No especificado'
                
                # Preparar dirección de envío
                direccion_html = ""
                if shipping_data:
                    direccion = shipping_data.get('direccion', '')
                    ciudad = shipping_data.get('ciudad', '')
                    provincia = shipping_data.get('provincia', '')
                    codigo_postal = shipping_data.get('codigo_postal', '')
                    
                    if direccion or ciudad or provincia:
                        direccion_completa = f"{direccion}"
                        if ciudad:
                            direccion_completa += f", {ciudad}"
                        if provincia:
                            direccion_completa += f", {provincia}"
                        if codigo_postal:
                            direccion_completa += f" ({codigo_postal})"
                        
                        direccion_html = f"""
                        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                            <h3 style="margin: 0 0 10px 0; color: #92400e; font-size: 16px;">📍 Dirección de Envío</h3>
                            <p style="margin: 0; color: #78350f; font-size: 15px; line-height: 1.5;">{direccion_completa}</p>
                        </div>
                        """
                    else:
                        direccion_html = """
                        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 0; color: #78350f; font-size: 15px;">⚠️ No se proporcionó dirección de envío</p>
                        </div>
                        """
                
                subject_admin = '🛒 Nuevo pedido - Pago en efectivo'
                msg_admin = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f3f4f6;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #10b981; padding: 20px; color: white;">
                            <h2 style="margin: 0;">🛒 Nuevo Pedido Recibido</h2>
                        </div>
                        <div style="padding: 20px;">
                            <p style="margin: 0 0 15px 0; font-size: 16px;"><strong>ID del Pedido:</strong> <code>{str(pedido.id)}</code></p>
                            <p style="margin: 0 0 15px 0; font-size: 16px;"><strong>Método de pago:</strong> Efectivo</p>
                            <p style="margin: 0 0 15px 0; font-size: 18px; color: #10b981;"><strong>Total:</strong> ${total:,.0f}</p>
                            
                            <div style="background-color: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; border-radius: 4px;">
                                <h3 style="margin: 0 0 10px 0; color: #1e40af; font-size: 16px;">👤 Datos del Cliente</h3>
                                <p style="margin: 5px 0; color: #1e3a8a; font-size: 15px;"><strong>Nombre:</strong> {cliente_nombre}</p>
                                <p style="margin: 5px 0; color: #1e3a8a; font-size: 15px;"><strong>Email:</strong> {user_email}</p>
                                <p style="margin: 5px 0; color: #1e3a8a; font-size: 15px;"><strong>📞 Teléfono:</strong> <a href="tel:{cliente_telefono}" style="color: #1e40af; text-decoration: none; font-weight: 600;">{cliente_telefono}</a></p>
                            </div>
                            
                            {direccion_html}
                            
                            <h3 style="margin: 20px 0 10px 0; color: #111827;">📦 Productos:</h3>
                            <div style="background-color: #f9fafb; padding: 15px; border-radius: 6px;">
                                {productos_text}
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                try:
                    enviar_email_simple(admin_email, subject_admin, msg_admin)
                except Exception as e:
                    logger.error(f"Error enviando correo al admin: {e}")

        elif payment_method == 'presupuesto':
            # Preparar detalles de productos
            productos_html = ""
            productos_text = ""
            
            for item in cart.items:
                producto_nombre = item.get('product_name', 'Producto')
                producto_imagen = item.get('product_image', '/static/img/logo.png')
                producto_precio = item.get('price', 0)
                producto_cantidad = item.get('quantity', 1)
                subtotal = producto_precio * producto_cantidad
                
                # Obtener información de variantes si existen
                variant_data = item.get('variant_data')
                variante_info = ""
                variante_info_html = ""
                
                if variant_data and isinstance(variant_data, dict):
                    variantes = []
                    for key, value in variant_data.items():
                        variantes.append(f"{key.capitalize()}: {value}")
                    
                    if variantes:
                        variante_info = f" ({', '.join(variantes)})"
                        variante_info_html = f"""<div style="color: #6b7280; font-size: 13px; margin-top: 3px;">🎨 {', '.join(variantes)}</div>"""
                
                productos_html += f"""
                <tr>
                    <td style="padding: 15px; border-bottom: 1px solid #e5e7eb;">
                        <div style="display: flex; align-items: center;">
                            <img src="{producto_imagen}" alt="{producto_nombre}" 
                                 style="width: 80px; height: 80px; object-fit: cover; border-radius: 8px; margin-right: 15px;">
                            <div>
                                <div style="font-weight: 600; color: #111827; margin-bottom: 5px;">{producto_nombre}</div>
                                {variante_info_html}
                                <div style="color: #6b7280; font-size: 14px;">Cantidad: {producto_cantidad}</div>
                            </div>
                        </div>
                    </td>
                    <td style="padding: 15px; border-bottom: 1px solid #e5e7eb; text-align: right; font-weight: 600; color: #111827;">
                        ${subtotal:,.0f}
                    </td>
                </tr>
                """
                
                productos_text += f"\n  • {producto_nombre}{variante_info} - Cantidad: {producto_cantidad} - Precio: ${producto_precio:,.0f} - Subtotal: ${subtotal:,.0f}"
            
            # Correo al usuario
            subject_user = 'Presupuesto recibido'
            msg_user = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f3f4f6;">
                <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f3f4f6; padding: 20px;">
                    <tr>
                        <td align="center">
                            <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
                                <tr>
                                    <td style="background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%); padding: 40px 30px; text-align: center;">
                                        <h1 style="margin: 0; color: #ffffff; font-size: 28px; font-weight: 700;">
                                            📋 Presupuesto Recibido
                                        </h1>
                                        <p style="margin: 10px 0 0 0; color: #e9d5ff; font-size: 16px;">
                                            Estamos preparando tu cotización
                                        </p>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="padding: 30px;">
                                        <p style="margin: 0 0 20px 0; color: #111827; font-size: 16px; line-height: 1.6;">
                                            Tu solicitud de presupuesto está siendo analizada. Muy pronto nos contactaremos para confirmarlo.
                                        </p>
                                        
                                        <div style="background-color: #faf5ff; border-radius: 8px; padding: 20px; margin-bottom: 25px;">
                                            <p style="margin: 0 0 10px 0; color: #6b7280; font-size: 14px; font-weight: 600; text-transform: uppercase;">
                                                Número de Referencia
                                            </p>
                                            <p style="margin: 0; color: #111827; font-size: 18px; font-weight: 700; font-family: monospace;">
                                                #{str(pedido.id)[:8]}...
                                            </p>
                                        </div>
                                        
                                        <h2 style="margin: 0 0 15px 0; color: #111827; font-size: 20px; font-weight: 600;">
                                            📦 Productos Solicitados
                                        </h2>
                                        <table width="100%" cellpadding="0" cellspacing="0" style="border: 1px solid #e5e7eb; border-radius: 8px; overflow: hidden; margin-bottom: 25px;">
                                            {productos_html}
                                        </table>
                                        
                                        <div style="background-color: #faf5ff; border-radius: 8px; padding: 20px;">
                                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                                <span style="color: #7c3aed; font-size: 18px; font-weight: 600;">Total Estimado:</span>
                                                <span style="color: #7c3aed; font-size: 24px; font-weight: 700;">${total:,.0f}</span>
                                            </div>
                                            <p style="margin: 10px 0 0 0; color: #6b21a8; font-size: 14px;">
                                                * Monto sujeto a confirmación
                                            </p>
                                        </div>
                                    </td>
                                </tr>
                                <tr>
                                    <td style="background-color: #f9fafb; padding: 20px 30px; text-align: center; border-top: 1px solid #e5e7eb;">
                                        <p style="margin: 0; color: #6b7280; font-size: 14px;">
                                            Nos pondremos en contacto contigo en las próximas 24-48 horas.
                                        </p>
                                    </td>
                                </tr>
                            </table>
                        </td>
                    </tr>
                </table>
            </body>
            </html>
            """
            try:
                enviar_email_simple(user_email, subject_user, msg_user)
            except Exception as e:
                logger.error(f"Error enviando correo al usuario: {e}")

            # Correo al admin
            if admin_email:
                # Preparar información del cliente
                cliente_nombre = user.get('nombre', 'No especificado')
                cliente_telefono = user.get('telefono') or shipping_data.get('telefono') or 'No especificado'
                
                # Preparar dirección de envío
                direccion_html = ""
                if shipping_data:
                    direccion = shipping_data.get('direccion', '')
                    ciudad = shipping_data.get('ciudad', '')
                    provincia = shipping_data.get('provincia', '')
                    codigo_postal = shipping_data.get('codigo_postal', '')
                    
                    if direccion or ciudad or provincia:
                        direccion_completa = f"{direccion}"
                        if ciudad:
                            direccion_completa += f", {ciudad}"
                        if provincia:
                            direccion_completa += f", {provincia}"
                        if codigo_postal:
                            direccion_completa += f" ({codigo_postal})"
                        
                        direccion_html = f"""
                        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                            <h3 style="margin: 0 0 10px 0; color: #92400e; font-size: 16px;">📍 Dirección de Envío</h3>
                            <p style="margin: 0; color: #78350f; font-size: 15px; line-height: 1.5;">{direccion_completa}</p>
                        </div>
                        """
                    else:
                        direccion_html = """
                        <div style="background-color: #fef3c7; border-left: 4px solid #f59e0b; padding: 15px; margin: 20px 0; border-radius: 4px;">
                            <p style="margin: 0; color: #78350f; font-size: 15px;">⚠️ No se proporcionó dirección de envío</p>
                        </div>
                        """
                
                subject_admin = '📋 Nueva solicitud de presupuesto'
                msg_admin = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <meta charset="UTF-8">
                </head>
                <body style="margin: 0; padding: 20px; font-family: Arial, sans-serif; background-color: #f3f4f6;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: #ffffff; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                        <div style="background-color: #8b5cf6; padding: 20px; color: white;">
                            <h2 style="margin: 0;">📋 Nueva Solicitud de Presupuesto</h2>
                        </div>
                        <div style="padding: 20px;">
                            <p style="margin: 0 0 15px 0; font-size: 16px;"><strong>ID de Referencia:</strong> <code>{str(pedido.id)}</code></p>
                            <p style="margin: 0 0 15px 0; font-size: 18px; color: #8b5cf6;"><strong>Total Estimado:</strong> ${total:,.0f}</p>
                            
                            <div style="background-color: #dbeafe; border-left: 4px solid #3b82f6; padding: 15px; margin: 20px 0; border-radius: 4px;">
                                <h3 style="margin: 0 0 10px 0; color: #1e40af; font-size: 16px;">👤 Datos del Cliente</h3>
                                <p style="margin: 5px 0; color: #1e3a8a; font-size: 15px;"><strong>Nombre:</strong> {cliente_nombre}</p>
                                <p style="margin: 5px 0; color: #1e3a8a; font-size: 15px;"><strong>Email:</strong> {user_email}</p>
                                <p style="margin: 5px 0; color: #1e3a8a; font-size: 15px;"><strong>📞 Teléfono:</strong> <a href="tel:{cliente_telefono}" style="color: #1e40af; text-decoration: none; font-weight: 600;">{cliente_telefono}</a></p>
                            </div>
                            
                            {direccion_html}
                            
                            <h3 style="margin: 20px 0 10px 0; color: #111827;">📦 Productos:</h3>
                            <div style="background-color: #f9fafb; padding: 15px; border-radius: 6px;">
                                {productos_text}
                            </div>
                        </div>
                    </div>
                </body>
                </html>
                """
                try:
                    enviar_email_simple(admin_email, subject_admin, msg_admin)
                except Exception as e:
                    logger.error(f"Error enviando correo al admin: {e}")

        elif payment_method == 'mercadopago':
            # Crear preferencia en MercadoPago usando SDK oficial
            mp_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
            if not mp_token:
                logger.error('MERCADOPAGO_ACCESS_TOKEN no configurado')
                raise HTTPException(status_code=500, detail='MercadoPago no configurado en el servidor')

            # Inicializar SDK de MercadoPago
            sdk = mercadopago.SDK(mp_token)

            # Construir items para MP
            mp_items = []
            for it in cart.items:
                qty = it.get('quantity') or it.get('cantidad') or 1
                price = it.get('price') or it.get('precio_unitario') or 0
                title = it.get('product_name') or f"Producto {it.get('product_id') or it.get('id_producto')}"
                mp_items.append({
                    'title': title,
                    'quantity': qty,
                    'unit_price': price,
                    'currency_id': 'ARS'  # Moneda argentina
                })

            # Crear preferencia con back_urls y auto_return
            mp_payload = {
                'items': mp_items,
                'external_reference': str(pedido.id),
                'notification_url': os.getenv('MERCADOPAGO_NOTIFICATION_URL'),
                'back_urls': {
                    'success': os.getenv('MERCADOPAGO_SUCCESS_URL', 'https://webhook.site/test-success'),
                    'failure': os.getenv('MERCADOPAGO_FAILURE_URL', 'https://webhook.site/test-failure'),
                    'pending': os.getenv('MERCADOPAGO_PENDING_URL', 'https://webhook.site/test-pending')
                }
            }

            try:
                preference_response = sdk.preference().create(mp_payload)

                if preference_response["status"] != 201:
                    logger.error(f"Error creando preferencia MercadoPago: {preference_response}")
                    raise HTTPException(status_code=500, detail='Error creando preferencia de MercadoPago')

                preference_data = preference_response["response"]
                preference_id = preference_data.get('id')
                if not preference_id:
                    logger.error(f"Preferencia creada sin id: {preference_data}")
                    raise HTTPException(status_code=500, detail='Error creando preferencia de MercadoPago')

                # Guardar referencia externa en el pedido
                pedido.external_reference = preference_id
                await pedido.save()

                # Notificar usuario/admin por email
                if user_email:
                    try:
                        enviar_email_simple(user_email, 'Pago iniciado', f'Se ha creado una preferencia de pago en MercadoPago para tu pedido (ID: {str(pedido.id)}).')
                    except Exception as e:
                        logger.error(f"Error enviando email usuario MP: {e}")
                if admin_email:
                    try:
                        enviar_email_simple(admin_email, 'Preferencia MercadoPago creada', f'Preferencia ID: {preference_id} para pedido {str(pedido.id)}')
                    except Exception as e:
                        logger.error(f"Error enviando email admin MP: {e}")

                return JSONResponse(status_code=200, content={'success': True, 'preference_id': preference_id, 'order_id': str(pedido.id)})

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"Error comunicando con MercadoPago: {e}")
                raise HTTPException(status_code=500, detail='Error comunicando con MercadoPago')

        # Limpiar carrito (para efectivo y presupuesto)
        cart.items = []
        await cart.save()

        return JSONResponse(status_code=200, content={
            'success': True,
            'mensaje': 'Pedido registrado correctamente',
            'order_id': str(pedido.id)
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error procesando checkout: {e}")
        raise HTTPException(status_code=500, detail='Error procesando el checkout')


@router.post('/webhook/mercadopago')
async def mercadopago_webhook(request_data: dict):
    """Procesa notificaciones desde MercadoPago y actualiza el pedido correspondiente."""
    try:
        mp_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
        if not mp_token:
            logger.error('MERCADOPAGO_ACCESS_TOKEN no configurado para webhook')
            raise HTTPException(status_code=500, detail='Webhook no configurado')

        # Inicializar SDK de MercadoPago
        sdk = mercadopago.SDK(mp_token)

        # Intentar extraer un id de payment o preference del payload
        preference_id = None
        payment_id = None

        # MercadoPago puede enviar distintos formatos: {"action":"payment.created","data":{"id":...}} o {"id":"...","type":"payment"}
        if isinstance(request_data, dict):
            if 'data' in request_data and isinstance(request_data['data'], dict) and 'id' in request_data['data']:
                payment_id = request_data['data']['id']
            elif 'id' in request_data:
                payment_id = request_data['id']
            elif 'preference_id' in request_data:
                preference_id = request_data['preference_id']

        # Si tenemos payment_id, consultar la API para obtener external_reference/preference
        preference_to_lookup = None
        payment_info = None
        if payment_id:
            payment_response = sdk.payment().get(payment_id)
            if payment_response["status"] != 200:
                logger.error(f'Error consultando pago MP {payment_id}: {payment_response}')
                raise HTTPException(status_code=500, detail='Error consultando pago')
            payment_info = payment_response["response"]
            preference_to_lookup = payment_info.get('external_reference') or payment_info.get('collection', {}).get('external_reference')
        elif preference_id:
            preference_to_lookup = preference_id

        if not preference_to_lookup:
            logger.error('No se pudo extraer referencia externa del webhook')
            raise HTTPException(status_code=400, detail='No se pudo procesar la notificación')

        # Buscar el pedido por external_reference
        from Projects.ecomerce.models.pedidos_beanie import EcomercePedidos
        pedido = await EcomercePedidos.find_one(EcomercePedidos.external_reference == preference_to_lookup)
        if not pedido:
            logger.error(f'Pedido no encontrado para referencia: {preference_to_lookup}')
            return JSONResponse(status_code=200, content={'success': False, 'message': 'Pedido no encontrado'})

        # Determinar nuevo estado del pedido consultando la preferencia o el pago
        status_final = None
        # Si tenemos payment_id, usar estado del pago
        if payment_id and payment_info:
            estado_mp = payment_info.get('status') or payment_info.get('collection', {}).get('status')
            if estado_mp in ['approved', 'paid', 'authorized']:
                status_final = 'pagado'
            elif estado_mp in ['in_process', 'pending']:
                status_final = 'pendiente'
            else:
                status_final = 'cancelado'
        else:
            # Sin payment_id, consultar preferencia para obtener detalles si es necesario
            preference_response = sdk.preference().get(preference_to_lookup)
            if preference_response["status"] == 200:
                # No siempre contiene estado de pago, por lo que dejamos en pendiente
                status_final = pedido.estado or 'pendiente'
            else:
                status_final = pedido.estado or 'pendiente'

        # Actualizar pedido
        pedido.estado = status_final
        await pedido.save()

        # Notificar por correo si el pedido fue pagado
        from Services.mail.mail import enviar_email_simple
        admin_email = os.getenv('ADMIN_EMAIL') or os.getenv('MAIL_FROM')
        user_email = None
        # Intentar obtener el correo del pedido (si se guardó contacto)
        if pedido.contacto and pedido.contacto.get('email'):
            user_email = pedido.contacto.get('email')

        if status_final == 'pagado':
            if user_email:
                try:
                    enviar_email_simple(user_email, 'Pago recibido', f'Se ha confirmado el pago para tu pedido {str(pedido.id)}. Gracias por tu compra.')
                except Exception as e:
                    logger.error(f'Error enviando email a usuario tras pago: {e}')
            if admin_email:
                try:
                    enviar_email_simple(admin_email, 'Pago confirmado', f'El pago del pedido {str(pedido.id)} ha sido confirmado.')
                except Exception as e:
                    logger.error(f'Error enviando email a admin tras pago: {e}')

        return JSONResponse(status_code=200, content={'success': True, 'status': status_final})

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error procesando webhook MercadoPago: {e}')
        raise HTTPException(status_code=500, detail='Error procesando webhook')


@router.get('/test/mercadopago')
async def test_mercadopago_template(request: Request):
    """
    Template de prueba para MercadoPago Checkout Pro
    """
    try:
        # Obtener configuración de MercadoPago
        public_key = os.getenv('MERCADOPAGO_PUBLIC_KEY')
        if not public_key:
            raise HTTPException(status_code=500, detail='MERCADOPAGO_PUBLIC_KEY no configurada')

        # Crear una preferencia de prueba
        mp_token = os.getenv('MERCADOPAGO_ACCESS_TOKEN')
        if not mp_token:
            raise HTTPException(status_code=500, detail='MERCADOPAGO_ACCESS_TOKEN no configurado')

        sdk = mercadopago.SDK(mp_token)

        preference_data = {
            "items": [
                {
                    "title": "Producto de Prueba",
                    "quantity": 1,
                    "unit_price": 100.50,
                    "currency_id": "ARS"
                }
            ],
            "back_urls": {
                "success": os.getenv('MERCADOPAGO_SUCCESS_URL', 'https://webhook.site/test-success'),
                "failure": os.getenv('MERCADOPAGO_FAILURE_URL', 'https://webhook.site/test-failure'),
                "pending": os.getenv('MERCADOPAGO_PENDING_URL', 'https://webhook.site/test-pending')
            },
            "external_reference": "test_preference_123",
            "notification_url": os.getenv('MERCADOPAGO_NOTIFICATION_URL')
        }

        preference_response = sdk.preference().create(preference_data)

        if preference_response["status"] != 201:
            raise HTTPException(status_code=500, detail='Error creando preferencia de prueba')

        preference = preference_response["response"]

        return templates.TemplateResponse("mercadopago_test.html", {
            "request": request,
            "mercadopago_public_key": public_key,
            "preference_id": preference["id"]
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f'Error creando template de prueba MercadoPago: {e}')
        raise HTTPException(status_code=500, detail='Error interno del servidor')