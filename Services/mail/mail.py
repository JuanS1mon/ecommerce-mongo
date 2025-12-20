# -*- coding: utf-8 -*-
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email.header import Header
from email import encoders
import os.path
from dotenv import load_dotenv
import os
import re
import logging
from fastapi import APIRouter, HTTPException, status, UploadFile, File, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Optional

# Modelo de solicitud
class EmailRequest(BaseModel):
    destinatario: str
    asunto: str
    mensaje: str

class EmailConAdjuntoRequest(BaseModel):
    destinatario: str
    asunto: str
    mensaje: str
    rutas_archivos: List[str] = []

# Cargar variables de entorno desde .env
# Calcular la ruta correcta al archivo .env en la raíz del proyecto
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
load_dotenv(env_path)

# Configuracion de correo
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))  # Puerto por defecto 587
SMTP_USE_TLS = os.getenv('SMTP_USE_TLS', 'True').lower() == 'true'
SMTP_USE_SSL = os.getenv('SMTP_USE_SSL', 'False').lower() == 'true'
USERNAME = os.getenv('USERNAME_EMAIL')  # Corregido el nombre de la variable
PASSWORD = os.getenv('PASSWORD_EMAIL')  # Corregido el nombre de la variable
MAIL_FROM = os.getenv('MAIL_FROM')
MAIL_FROM_NAME = os.getenv('MAIL_FROM_NAME')

# Validación centralizada para main.py
MAIL_CONFIG_OK = all([SMTP_SERVER, SMTP_PORT, USERNAME, PASSWORD, MAIL_FROM])

# Validar que las variables de entorno estén configuradas
# Comentado temporalmente para evitar errores de inicio
# if not all([SMTP_SERVER, USERNAME, PASSWORD]):
#     raise ValueError("Las variables de entorno de correo no están configuradas correctamente. Verifica SMTP_SERVER, USERNAME_EMAIL y PASSWORD_EMAIL en tu archivo .env")

# Validación mejorada que permite el funcionamiento sin configuración de correo
if not all([SMTP_SERVER, USERNAME, PASSWORD]):
    print("⚠️  ADVERTENCIA: Variables de entorno de correo no configuradas.")
    print("   El sistema funcionará pero las funciones de correo estarán deshabilitadas.")
    print("   Para habilitar correo, configura: SMTP_SERVER, USERNAME_EMAIL, PASSWORD_EMAIL en .env")
    print(f"   Debug - SMTP_SERVER: {SMTP_SERVER}")
    print(f"   Debug - USERNAME: {USERNAME}")
    print(f"   Debug - PASSWORD: {'*' * len(PASSWORD) if PASSWORD else 'None'}")
    print(f"   Debug - Ruta .env: {env_path}")
    # Deshabilitar funciones de correo si no están configuradas
    MAIL_ENABLED = False
else:
    MAIL_ENABLED = True
    print("[OK] Configuración de correo cargada correctamente")

# FORZAR HABILITACIÓN DE CORREO PARA TESTING
MAIL_ENABLED = True
print("[INFO] CORREO FORZADO A HABILITADO PARA TESTING")

# Crear el router de FastAPI
router = APIRouter(
    include_in_schema=False ,  # Oculta todas las rutas de este router en la documentación
    prefix="/envios",
    tags=["envios"],
    responses={404: {"description": "Not Found"}},
)

# Ruta de FastAPI para enviar correo
@router.post("/enviar_correo")
async def enviar_correo_route(request: EmailRequest):
    # Validar el email
    destinatario = validar_email(request.destinatario)
    if not destinatario:
        raise HTTPException(status_code=400, detail="Correo electrónico inválido")
    # Enviar el correo
    try:
        enviar_correo(destinatario, request.asunto, request.mensaje)
        return {'mensaje': "Correo enviado exitosamente"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al enviar el correo: {str(e)}")
    
def enviar_correo(destinatario, asunto, mensaje):
    """
    Envía un correo electrónico simple sin adjuntos.
    
    Args:
        destinatario: Dirección de correo del destinatario
        asunto: Asunto del correo
        mensaje: Cuerpo del mensaje
    
    Raises:
        Exception: Si ocurre algún error durante el envío
    """
    # Verificar si el correo está habilitado
    if not MAIL_ENABLED:
        print(f"⚠️  Correo deshabilitado. Se habría enviado a {destinatario}: {asunto}")
        return
        
    # Para emails simples, usar MIMEText con HTML para mejor compatibilidad
    html_message = mensaje.replace('\n', '<br>')
    msg = MIMEText(f'<html><body><pre style="font-family: Arial, sans-serif; white-space: pre-wrap;">{html_message}</pre></body></html>', 'html', 'utf-8')
    msg['From'] = MAIL_FROM
    msg['To'] = destinatario
    msg['Subject'] = Header(asunto, 'utf-8')
    
    try:
        # Configurar el servidor SMTP
        if SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            if SMTP_USE_TLS:
                server.starttls()
        
        # Autenticar y enviar
        server.login(USERNAME, PASSWORD)
        text = msg.as_string()
        server.sendmail(MAIL_FROM, destinatario, text)
        server.quit()
        
        print(f"Correo enviado exitosamente a {destinatario}")
        
    except Exception as e:
        print(f"Error al enviar correo: {str(e)}")
        raise e  # Propagar la excepción

def validar_email(email):
    """
    Valida el formato de un correo electrónico.
    
    Args:
        email: Dirección de correo a validar
    
    Returns:
        str or None: El email si es válido, None si es inválido
    """
    # Expresión regular para validar el formato del correo electrónico
    patron = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    if re.match(patron, email):
        return email
    else:
        return None

# Función de utilidad para usar desde cualquier parte de la aplicación
def enviar_email_simple(destinatario: str, asunto: str, mensaje: str):
    """
    Función de utilidad para enviar correos desde cualquier parte de la aplicación.
    
    Args:
        destinatario: Email del destinatario
        asunto: Asunto del correo
        mensaje: Contenido del mensaje
    
    Returns:
        dict: Resultado del envío
    
    Raises:
        ValueError: Si el email es inválido
        Exception: Si hay error en el envío
    """
    # Verificar si el correo está habilitado
    if not MAIL_ENABLED:
        print(f"⚠️  Correo deshabilitado. Se habría enviado a {destinatario}: {asunto}")
        return {"success": True, "message": "Correo simulado (servicio deshabilitado)"}
        
    # Validar email
    if not validar_email(destinatario):
        raise ValueError("Correo electrónico inválido")
    
    try:
        enviar_correo(destinatario, asunto, mensaje)
        return {"success": True, "message": "Correo enviado exitosamente"}
    except Exception as e:
        raise Exception(f"Error al enviar correo: {str(e)}")

def enviar_email_con_adjuntos_simple(destinatario: str, asunto: str, mensaje: str, rutas_archivos: List[str]):
    """
    Función de utilidad para enviar correos con adjuntos desde cualquier parte de la aplicación.
    
    Args:
        destinatario: Email del destinatario
        asunto: Asunto del correo
        mensaje: Contenido del mensaje
        rutas_archivos: Lista de rutas de archivos a adjuntar
    
    Returns:
        dict: Resultado del envío
    
    Raises:
        ValueError: Si el email es inválido o archivos no existen
        Exception: Si hay error en el envío
    """
    # Validar email
    if not validar_email(destinatario):
        raise ValueError("Correo electrónico inválido")
    
    # Validar que los archivos existan
    archivos_no_encontrados = []
    for ruta in rutas_archivos:
        if not os.path.isfile(ruta):
            archivos_no_encontrados.append(ruta)
    
    if archivos_no_encontrados:
        raise ValueError(f"Los siguientes archivos no fueron encontrados: {', '.join(archivos_no_encontrados)}")
    
    try:
        enviar_email_con_adjunto(destinatario, asunto, mensaje, rutas_archivos)
        return {"success": True, "message": "Correo con adjuntos enviado exitosamente"}
    except Exception as e:
        raise Exception(f"Error al enviar correo con adjuntos: {str(e)}")

def enviar_email_con_adjunto(destinatario, asunto, mensaje, rutas_archivos):
    """
    Envía un correo electrónico con archivos adjuntos.
    
    Args:
        destinatario: Dirección de correo del destinatario
        asunto: Asunto del correo
        mensaje: Cuerpo del mensaje
        rutas_archivos: Lista de rutas a los archivos que se adjuntarán
    
    Returns:
        None
    
    Raises:
        Exception: Si ocurre algún error durante el envío
    """    # Crear el mensaje
    msg = MIMEMultipart()
    msg['From'] = f"{MAIL_FROM_NAME} <{MAIL_FROM}>" if MAIL_FROM_NAME else MAIL_FROM
    msg['To'] = destinatario
    # Codificar el asunto para soportar caracteres especiales
    msg['Subject'] = Header(asunto, 'utf-8')
    
    # Agregar el cuerpo del mensaje con codificación UTF-8
    
    # Adjuntar cada archivo
    for ruta_archivo in rutas_archivos:
        if os.path.isfile(ruta_archivo):
            # Obtener el nombre del archivo de la ruta
            nombre_archivo = os.path.basename(ruta_archivo)
            
            # Detectar el tipo de archivo y adjuntarlo de manera apropiada
            with open(ruta_archivo, "rb") as archivo:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(archivo.read())
            
            # Codificar para enviar por correo
            encoders.encode_base64(part)
            
            # Agregar cabecera con el nombre del archivo
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{nombre_archivo}"'
            )
            
            # Agregar el archivo adjunto al mensaje
            msg.attach(part)
    
    # Enviar el correo
    try:
        # Configurar el servidor SMTP
        if SMTP_USE_SSL:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            if SMTP_USE_TLS:
                server.starttls()
        
        # Autenticar y enviar
        server.login(USERNAME, PASSWORD)
        text = msg.as_string()
        server.sendmail(MAIL_FROM, destinatario, text)
        server.quit()
        
        print(f"Correo con adjuntos enviado exitosamente a {destinatario}")
        
    except Exception as e:
        print(f"Error al enviar correo con adjuntos: {str(e)}")
        raise e  # Propagar la excepción

@router.post("/enviar_email_con_adjunto")
async def enviar_email_con_adjunto_route(request: EmailConAdjuntoRequest):
    """
    Ruta para enviar un correo electrónico con archivos adjuntos
    """
    # Validar el email
    destinatario = validar_email(request.destinatario)
    if not destinatario:
        raise HTTPException(status_code=400, detail="Correo electrónico inválido")
    
    # Validar que los archivos existan
    archivos_no_encontrados = []
    for ruta in request.rutas_archivos:
        if not os.path.isfile(ruta):
            archivos_no_encontrados.append(ruta)
    
    if archivos_no_encontrados:
        raise HTTPException(
            status_code=400, 
            detail=f"Los siguientes archivos no fueron encontrados: {', '.join(archivos_no_encontrados)}"
        )
    
    # Enviar el correo con los adjuntos
    try:
        enviar_email_con_adjunto(
            destinatario, 
            request.asunto, 
            request.mensaje, 
            request.rutas_archivos
        )
        return {'mensaje': "Correo con archivos adjuntos enviado exitosamente"}
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error al enviar el correo con adjuntos: {str(e)}"
        )

@router.post("/enviar_email_con_adjunto_upload")
async def enviar_email_con_adjunto_upload(
    destinatario: str = Form(...),
    asunto: str = Form(...),
    mensaje: str = Form(...),
    archivos: List[UploadFile] = File(...)
):
    """
    Ruta para enviar un correo electrónico con archivos adjuntos subidos directamente
    """
    # Validar el email
    destinatario_valido = validar_email(destinatario)
    if not destinatario_valido:
        raise HTTPException(status_code=400, detail="Correo electrónico inválido")
    
    # Directorio temporal para guardar los archivos subidos
    temp_dir = "temp_uploads"
    os.makedirs(temp_dir, exist_ok=True)
    
    # Lista para almacenar las rutas temporales de los archivos
    rutas_temporales = []
    
    try:
        # Guardar cada archivo en el directorio temporal
        for archivo in archivos:
            # Generar un nombre de archivo único para evitar colisiones
            nombre_temporal = f"{temp_dir}/{archivo.filename}"
            
            # Guardar el archivo
            with open(nombre_temporal, "wb") as buffer:
                content = await archivo.read()
                buffer.write(content)
            
            # Añadir la ruta a la lista
            rutas_temporales.append(nombre_temporal)
        
        # Enviar el correo con los archivos adjuntos
        enviar_email_con_adjunto(
            destinatario_valido, 
            asunto, 
            mensaje, 
            rutas_temporales
        )
        
        # Eliminar los archivos temporales después de enviar el correo
        for ruta in rutas_temporales:
            if os.path.exists(ruta):
                os.remove(ruta)
        
        return {'mensaje': "Correo con archivos adjuntos enviado exitosamente"}
    
    except Exception as e:
        # Asegurarse de limpiar los archivos temporales en caso de error
        for ruta in rutas_temporales:
            if os.path.exists(ruta):
                os.remove(ruta)
                
        raise HTTPException(
            status_code=500, 
            detail=f"Error al enviar el correo con adjuntos: {str(e)}"
        )

# Al final del archivo, para exportar explícitamente MAIL_CONFIG_OK
__all__ = ["router", "MAIL_CONFIG_OK", "enviar_correo_presupuesto", "enviar_multiples_emails"]

async def enviar_correo_presupuesto(presupuesto_detalles: dict):
    """
    Envía un correo con los detalles del presupuesto solicitado

    Args:
        presupuesto_detalles: Diccionario con los detalles del presupuesto
    """
    import asyncio
    logger = logging.getLogger(__name__)
    
    try:
        destinatario = presupuesto_detalles.get('email')
        usuario = presupuesto_detalles.get('usuario', 'Cliente')
        pedido_id = presupuesto_detalles.get('pedido_id')
        total = presupuesto_detalles.get('total', 0)
        items = presupuesto_detalles.get('items', [])

        # Crear el asunto
        asunto = f"Presupuesto solicitado - Pedido #{pedido_id}"

        # Crear el mensaje
        mensaje = f"""
Estimado/a {usuario},

Gracias por solicitar un presupuesto. A continuación te detallamos la cotización para tu pedido #{pedido_id}:

DETALLE DE PRODUCTOS:
"""

        for item in items:
            mensaje += f"""
- {item['nombre']}
  Cantidad: {item['cantidad']}
  Precio unitario: ${item['precio_unitario']:.2f}
  Subtotal: ${item['subtotal']:.2f}
"""

        mensaje += f"""

TOTAL DEL PRESUPUESTO: ${total:.2f}

Este presupuesto tiene una validez de 30 días a partir de la fecha de emisión.

Si tienes alguna pregunta o necesitas modificar algún aspecto del presupuesto, no dudes en contactarnos.

Atentamente,
Equipo de Ventas
Tu Tienda Online
"""

        # Enviar el correo de forma asíncrona usando asyncio.to_thread()
        await asyncio.to_thread(enviar_email_simple, destinatario, asunto, mensaje)
        logger.info(f"Correo de presupuesto enviado exitosamente a {destinatario}")

    except Exception as e:
        logger.error(f"Error enviando correo de presupuesto: {e}")
        raise e

async def enviar_multiples_emails(emails_lista: list):
    """
    Envía múltiples emails de forma concurrente

    Args:
        emails_lista: Lista de diccionarios con 'destinatario', 'asunto', 'mensaje'

    Returns:
        dict: Resultado del envío con success, enviados, total, tiempo_total, errores
    """
    import asyncio
    import time
    logger = logging.getLogger(__name__)
    
    start_time = time.time()
    total = len(emails_lista)
    enviados = 0
    errores = 0

    try:
        # Enviar emails de forma concurrente
        tasks = []
        for email_data in emails_lista:
            task = asyncio.create_task(_enviar_email_async(email_data))
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                errores += 1
                logger.error(f"Error enviando email: {result}")
            else:
                enviados += 1

        tiempo_total = time.time() - start_time

        return {
            "success": errores == 0,
            "enviados": enviados,
            "total": total,
            "tiempo_total": tiempo_total,
            "errores": errores
        }

    except Exception as e:
        logger.error(f"Error en enviar_multiples_emails: {e}")
        return {
            "success": False,
            "enviados": 0,
            "total": total,
            "tiempo_total": time.time() - start_time,
            "errores": total
        }

async def _enviar_email_async(email_data: dict):
    """
    Función auxiliar para enviar un email de forma asíncrona
    """
    logger = logging.getLogger(__name__)
    
    try:
        destinatario = email_data.get('destinatario')
        asunto = email_data.get('asunto')
        mensaje = email_data.get('mensaje')

        if not all([destinatario, asunto, mensaje]):
            raise ValueError("Faltan datos requeridos: destinatario, asunto, mensaje")

        enviar_email_simple(destinatario, asunto, mensaje)

    except Exception as e:
        logger.error(f"Error enviando email a {email_data.get('destinatario')}: {e}")
        raise e
