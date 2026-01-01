"""
Router de Marketing con IA
Permite crear campañas de marketing usando IA generativa
"""
import logging
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
import google.genai as genai

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.marketing_beanie import MarketingCampaign, MarketingConfig
from Projects.Admin.middleware.admin_auth import require_admin
from Projects.Admin.utils.template_helpers import render_admin_template

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/admin/marketing",
    tags=["admin-marketing"]
)


@router.get("/", response_class=HTMLResponse)
async def marketing_dashboard(request: Request):
    """Dashboard principal de marketing"""
    logger.info("=== MARKETING DASHBOARD REQUEST STARTED ===")
    try:
        logger.info("Calling render_admin_template...")
        result = render_admin_template(
            "marketing/index.html",
            request,
            active_page="marketing"
        )
        logger.info("render_admin_template completed successfully")
        logger.info("=== MARKETING DASHBOARD REQUEST COMPLETED ===")
        return result
    except Exception as e:
        logger.error(f"Error cargando dashboard marketing: {str(e)}")
        logger.error(f"Exception type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando dashboard de marketing"
        )


@router.get("/crear", response_class=HTMLResponse)
async def crear_campana(request: Request):
    """Página para crear nueva campaña"""
    try:
        return render_admin_template(
            "marketing/crear.html",
            request,
            active_page="marketing"
        )
    except Exception as e:
        logger.error(f"Error cargando página crear campaña: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error cargando página de creación"
        )


@router.get("/api/productos-test")
async def test_listar_productos_para_marketing():
    """Endpoint de prueba sin autenticación para debug"""
    try:
        # Importar aquí para evitar dependencias circulares
        from Projects.ecomerce.models.productos_beanie import EcomerceProductos, EcomerceProductosVariantes

        # Obtener productos activos que tengan variantes con stock
        productos_activos = await EcomerceProductos.find(
            EcomerceProductos.active == True
        ).to_list()
        logger.info(f"TEST: Productos activos encontrados: {len(productos_activos)}")

        # Filtrar productos que tienen variantes con stock disponible
        productos_con_stock = []
        for producto in productos_activos:
            # Verificar si el producto tiene variantes activas con stock
            variantes_con_stock = await EcomerceProductosVariantes.find(
                EcomerceProductosVariantes.product_id == str(producto.id),
                EcomerceProductosVariantes.active == True,
                EcomerceProductosVariantes.stock > 0
            ).to_list()
            
            if variantes_con_stock:
                productos_con_stock.append(producto)
                logger.info(f"TEST: Producto {producto.nombre} tiene {len(variantes_con_stock)} variantes con stock")
            else:
                logger.info(f"TEST: Producto {producto.nombre} NO tiene variantes con stock")

        logger.info(f"TEST: Total productos con stock para marketing: {len(productos_con_stock)}")

        # Formatear para marketing (sin datos internos)
        productos_marketing = []
        for prod in productos_con_stock:
            productos_marketing.append({
                "id": str(prod.id),
                "nombre": prod.nombre,
                "descripcion": prod.descripcion,
                "precio": prod.precio,
                "imagen_url": prod.imagen_url or "",
                "categoria": getattr(prod, 'categoria', ''),
                "marca": getattr(prod, 'marca', '')
            })

        logger.info(f"TEST: Retornando {len(productos_marketing)} productos para marketing")

        return {
            "success": True,
            "productos": productos_marketing,
            "total": len(productos_marketing)
        }

    except Exception as e:
        logger.error(f"TEST: Error obteniendo productos: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo productos: {str(e)}"
        )


@router.get("/api/productos-debug")
async def debug_listar_productos_para_marketing():
    """Endpoint de debug para verificar que los cambios se aplican"""
    return {
        "success": True,
        "message": "DEBUG ENDPOINT WORKING",
        "productos": [{"id": "test", "nombre": "Producto de Prueba"}],
        "total": 1
    }


@router.get("/api/productos")
async def listar_productos_para_marketing(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Lista productos disponibles para campañas de marketing"""
    try:
        logger.info(f"Usuario admin autenticado: {admin_user.usuario}")

        # Importar modelos necesarios
        from Projects.ecomerce.models.productos_beanie import EcomerceProductos, EcomerceProductosVariantes
        from Projects.ecomerce.models.categorias_beanie import EcomerceCategorias

        # Obtener productos activos
        productos_activos = await EcomerceProductos.find(EcomerceProductos.active == True).to_list()

        productos_para_marketing = []

        for producto in productos_activos:
            # Verificar si el producto tiene variantes con stock disponible
            variantes_con_stock = await EcomerceProductosVariantes.find(
                EcomerceProductosVariantes.product_id == str(producto.id),
                EcomerceProductosVariantes.active == True,
                EcomerceProductosVariantes.stock > 0
            ).to_list()

            # Solo incluir productos que tengan al menos una variante con stock
            if variantes_con_stock:
                # Obtener información de categoría si existe
                categoria_nombre = ""
                try:
                    if producto.id_categoria:
                        categoria = await EcomerceCategorias.get(producto.id_categoria)
                        categoria_nombre = categoria.nombre if categoria else ""
                except:
                    categoria_nombre = ""

                productos_para_marketing.append({
                    "id": str(producto.id),
                    "nombre": producto.nombre,
                    "descripcion": producto.descripcion or "",
                    "precio": float(producto.precio),
                    "imagen_url": producto.imagen_url or "",
                    "categoria": categoria_nombre,
                    "marca": "",  # Campo no disponible en el modelo actual
                    "variantes_con_stock": len(variantes_con_stock)
                })

        logger.info(f"Productos encontrados para marketing: {len(productos_para_marketing)}")

        return {
            "success": True,
            "productos": productos_para_marketing,
            "total": len(productos_para_marketing)
        }

    except Exception as e:
        logger.error(f"Error listando productos para marketing: {str(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo productos: {str(e)}"
        )


@router.post("/api/campana")
async def crear_campana_basica(
    producto_id: str = Form(...),
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Crear campaña básica con producto seleccionado"""
    try:
        # Importar aquí para evitar dependencias circulares
        from Projects.ecomerce.models.productos_beanie import EcomerceProductos
        from bson import ObjectId

        # Verificar que el producto existe
        try:
            producto_obj_id = ObjectId(producto_id)
            producto = await EcomerceProductos.get(producto_obj_id)
        except:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no encontrado"
            )

        if not producto or not producto.active:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Producto no disponible"
            )

        # Crear campaña básica
        campana = MarketingCampaign(
            producto_id=producto_id,
            producto_nombre=producto.nombre,
            producto_descripcion=producto.descripcion,
            producto_precio=producto.precio,
            producto_imagen_url=producto.imagen_url or "",
            creado_por=admin_user.usuario
        )

        await campana.insert()

        return {
            "success": True,
            "campana_id": str(campana.id),
            "mensaje": "Campaña creada exitosamente"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creando campaña: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creando campaña: {str(e)}"
        )


@router.get("/api/config")
async def obtener_config_marketing(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener configuración actual del sistema de marketing"""
    try:
        config = await MarketingConfig.find_one() or MarketingConfig()

        return {
            "success": True,
            "config": {
                "google_ai_api_key": "***hidden***" if config.google_ai_api_key else "",
                "facebook_app_id": config.facebook_app_id,
                "facebook_app_secret": "***hidden***" if config.facebook_app_secret else "",
                "facebook_access_token": "***hidden***" if config.facebook_access_token else "",
                "instagram_access_token": "***hidden***" if config.instagram_access_token else "",
                "modelo_ia": config.modelo_ia,
                "max_tokens_por_request": config.max_tokens_por_request,
                "temperatura": config.temperatura,
                "activo": config.activo
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo config marketing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo configuración: {str(e)}"
        )


@router.post("/api/config")
async def actualizar_config_marketing(
    google_ai_api_key: Optional[str] = Form(None),
    facebook_app_id: Optional[str] = Form(None),
    facebook_app_secret: Optional[str] = Form(None),
    facebook_access_token: Optional[str] = Form(None),
    instagram_access_token: Optional[str] = Form(None),
    modelo_ia: Optional[str] = Form(None),
    max_tokens_por_request: Optional[int] = Form(None),
    temperatura: Optional[float] = Form(None),
    activo: Optional[bool] = Form(None),
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Actualizar configuración del sistema de marketing"""
    try:
        config = await MarketingConfig.find_one()
        if not config:
            config = MarketingConfig()

        # Actualizar campos proporcionados
        if google_ai_api_key is not None:
            config.google_ai_api_key = google_ai_api_key
        if facebook_app_id is not None:
            config.facebook_app_id = facebook_app_id
        if facebook_app_secret is not None:
            config.facebook_app_secret = facebook_app_secret
        if facebook_access_token is not None:
            config.facebook_access_token = facebook_access_token
        if instagram_access_token is not None:
            config.instagram_access_token = instagram_access_token
        if modelo_ia is not None:
            config.modelo_ia = modelo_ia
        if max_tokens_por_request is not None:
            config.max_tokens_por_request = max_tokens_por_request
        if temperatura is not None:
            config.temperatura = temperatura
        if activo is not None:
            config.activo = activo

        await config.save()

        return {
            "success": True,
            "mensaje": "Configuración actualizada exitosamente"
        }

    except Exception as e:
        logger.error(f"Error actualizando config marketing: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error actualizando configuración: {str(e)}"
        )


@router.get("/api/campanas")
async def listar_campanas(
    limit: int = 10,
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Lista campañas del usuario actual"""
    try:
        campanas = await MarketingCampaign.find(
            {"creado_por": admin_user.usuario}
        ).sort([("fecha_creacion", -1)]).limit(limit).to_list()

        # Formatear para respuesta
        campanas_formateadas = []
        for campana in campanas:
            campanas_formateadas.append({
                "id": str(campana.id),
                "titulo_campana": campana.titulo_campana,
                "producto_nombre": campana.producto_nombre,
                "estado": campana.estado,
                "plataformas": campana.plataformas,
                "fecha_creacion": campana.fecha_creacion.isoformat(),
                "fecha_publicacion": campana.fecha_publicacion.isoformat() if campana.fecha_publicacion else None
            })

        return {
            "success": True,
            "campanas": campanas_formateadas
        }

    except Exception as e:
        logger.error(f"Error listando campañas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo campañas: {str(e)}"
        )


@router.get("/api/estadisticas")
async def obtener_estadisticas_marketing(
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Obtener estadísticas de marketing"""
    try:
        # Contar campañas por estado
        total = await MarketingCampaign.find({"creado_por": admin_user.usuario}).count()
        borrador = await MarketingCampaign.find({"creado_por": admin_user.usuario, "estado": "borrador"}).count()
        publicadas = await MarketingCampaign.find({"creado_por": admin_user.usuario, "estado": "publicado"}).count()

        # Verificar si IA está configurada
        config = await MarketingConfig.find_one()
        ia_activa = bool(config and config.google_ai_api_key and config.activo)

        return {
            "success": True,
            "estadisticas": {
                "total": total,
                "borrador": borrador,
                "publicadas": publicadas,
                "ia_activa": ia_activa
            }
        }

    except Exception as e:
        logger.error(f"Error obteniendo estadísticas: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )


@router.post("/api/chat")
async def enviar_mensaje_chat(
    message: str = Form(...),
    conversation_history: str = Form(None),
    campana_id: str = Form(None),
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Enviar mensaje al chat de IA para una campaña"""
    try:
        # Si hay campaña_id y no está vacío, verificar que existe
        campana = None
        if campana_id and campana_id.strip():
            from bson import ObjectId
            campana = await MarketingCampaign.get(ObjectId(campana_id))
            if not campana or campana.creado_por != admin_user.usuario:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Campaña no encontrada"
                )

        # Verificar configuración de IA
        config = await MarketingConfig.find_one()
        api_key = config.google_ai_api_key if config and config.google_ai_api_key else os.getenv('GOOGLE_AI_API_KEY')
        
        # Usar API key proporcionada como fallback temporal
        if not api_key:
            api_key = "AIzaSyAOMmVutZdJNxzp74bMRNCjefZrLqPyEfQ"
        
        if not api_key:
            return {
                "success": False,
                "response": "Lo siento, la IA no está configurada. Por favor, configura GOOGLE_AI_API_KEY en las variables de entorno o en Configuración > Marketing.",
                "campana_id": campana_id
            }
        contexto = "Eres un experto en marketing digital. Estás ayudando a crear una campaña."

        # Si hay campaña, agregar detalles del producto
        if campana:
            contexto += f"""
            Producto:
            - Nombre: {campana.producto_nombre}
            - Descripción: {campana.producto_descripcion}
            - Precio: ${campana.producto_precio}
            """

        contexto += "\n\nHistorial de conversación:\n"

        # Agregar mensajes anteriores
        if campana and campana.conversacion:
            for msg in campana.conversacion[-5:]:
                contexto += f"{msg.role}: {msg.content}\n"
        elif conversation_history:
            # Parsear el historial del frontend
            try:
                import json
                history = json.loads(conversation_history)
                for msg in history[-5:]:
                    contexto += f"{msg['role']}: {msg['content']}\n"
            except:
                pass

        contexto += f"Usuario: {message}\n\nResponde de manera útil y profesional."

        # Generar respuesta usando Gemini
        import google.generativeai as genai
        genai.configure(api_key=api_key)
        client = genai.GenerativeModel(config.modelo_ia if config and config.modelo_ia else "gemini-2.0-flash")
        
        try:
            response = client.generate_content(contexto)
            respuesta_ia = response.text
        except Exception as e:
            error_msg = str(e).lower()
            if "quota" in error_msg or "429" in error_msg:
                respuesta_ia = "Lo siento, se ha excedido la cuota de la API de Gemini. Por favor, verifica tu plan de facturación en Google AI Studio o configura una API key con cuota disponible."
            elif "api key" in error_msg or "invalid" in error_msg:
                respuesta_ia = "Error de autenticación con Gemini API. Por favor, verifica que la API key sea válida."
            elif "model" in error_msg or "404" in error_msg:
                respuesta_ia = "El modelo de IA configurado no es válido. Por favor, actualiza la configuración de marketing con un modelo válido."
            else:
                respuesta_ia = f"Error al procesar la solicitud con IA: {str(e)}"

        # Si hay campaña, guardar conversación
        if campana:
            from Projects.Admin.models.marketing_beanie import ConversacionIAMessage

            nuevo_mensaje_usuario = ConversacionIAMessage(
                role="user",
                content=message
            )

            nuevo_mensaje_ia = ConversacionIAMessage(
                role="assistant",
                content=respuesta_ia
            )

            campana.conversacion.extend([nuevo_mensaje_usuario, nuevo_mensaje_ia])
            await campana.save()

        return {
            "success": True,
            "response": respuesta_ia,
            "campana_id": campana_id
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error en chat IA: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error procesando mensaje: {str(e)}"
        )


@router.post("/api/generar")
async def generar_contenido_campana(
    campana_id: str = Form(...),
    admin_user: AdminUsuarios = Depends(require_admin)
):
    """Generar contenido completo de la campaña usando IA"""
    try:
        # Verificar campaña
        from bson import ObjectId
        campana = await MarketingCampaign.get(ObjectId(campana_id))

        if not campana or campana.creado_por != admin_user.usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Campaña no encontrada"
            )

        # Verificar configuración IA
        config = await MarketingConfig.find_one()
        api_key = config.google_ai_api_key if config and config.google_ai_api_key else os.getenv('GOOGLE_AI_API_KEY')
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IA no configurada. Configure GOOGLE_AI_API_KEY en variables de entorno"
            )

        # Configurar IA con nueva API
        client = genai.Client(api_key=api_key)

        # Crear prompt para generación de contenido
        prompt = f"""
        Basándote en esta conversación sobre marketing para el producto "{campana.producto_nombre}",
        genera contenido completo para una campaña en redes sociales.

        Producto:
        - Nombre: {campana.producto_nombre}
        - Descripción: {campana.producto_descripcion}
        - Precio: ${campana.producto_precio}

        Conversación previa:
        {chr(10).join([f"{msg.role}: {msg.content}" for msg in campana.conversacion])}

        Genera:
        1. Un título atractivo para la campaña
        2. Texto optimizado para Instagram/Facebook (máximo 2200 caracteres)
        3. Lista de 5-7 hashtags relevantes
        4. Sugerencias para el tipo de publicación

        Formato de respuesta:
        TÍTULO: [título]
        TEXTO: [texto completo]
        HASHTAGS: [lista separada por comas]
        SUGERENCIAS: [sugerencias]
        """

        # Generar contenido con nueva API
        response = client.models.generate_content(
            model=config.modelo_ia,
            contents=prompt
        )
        contenido = response.text

        # Parsear respuesta (básico)
        lineas = contenido.split('\n')
        titulo = ""
        texto = ""
        hashtags = []
        sugerencias = ""

        for linea in lineas:
            if linea.startswith('TÍTULO:'):
                titulo = linea.replace('TÍTULO:', '').strip()
            elif linea.startswith('TEXTO:'):
                texto = linea.replace('TEXTO:', '').strip()
            elif linea.startswith('HASHTAGS:'):
                hashtags_str = linea.replace('HASHTAGS:', '').strip()
                hashtags = [h.strip() for h in hashtags_str.split(',') if h.strip()]
            elif linea.startswith('SUGERENCIAS:'):
                sugerencias = linea.replace('SUGERENCIAS:', '').strip()

        # Actualizar campaña
        campana.titulo_campana = titulo
        campana.texto_para_redes = texto
        campana.hashtags = hashtags
        campana.estado = "generado"
        await campana.save()

        return {
            "success": True,
            "titulo": titulo,
            "texto": texto,
            "hashtags": hashtags,
            "sugerencias": sugerencias
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error generando contenido: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando contenido: {str(e)}"
        )