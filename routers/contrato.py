# routers/contrato.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse
from models.models_beanie import Contrato, Servicio
from security.jwt_auth import get_current_user
from pydantic import BaseModel
from typing import List, Dict, Any
from datetime import datetime, timedelta
from models.models_beanie import Configuracion

async def get_contract_config() -> Dict[str, Any]:
    """Obtiene la configuración del contrato desde la base de datos"""
    try:
        configs = await Configuracion.find_all().to_list()
        config_dict = {c.key: c.value for c in configs}
        
        # Valores por defecto si no existen
        defaults = {
            'proveedor_razon_social': 'SysNeg S.A.',
            'proveedor_cuit': '30-XXXXXXXX-9',
            'proveedor_domicilio': 'Ciudad Autónoma de Buenos Aires, Argentina',
            'moneda': 'ARS',
            'periodicidad': 'mensual',
            'dias_vencimiento': 30,
            'dias_preaviso': 30,
            'dias_retencion': 30
        }
        
        # Combinar con valores de DB
        for key, default_value in defaults.items():
            if key not in config_dict:
                config_dict[key] = default_value
        
        return config_dict
    except Exception as e:
        print(f"Error obteniendo configuración del contrato: {e}")
        # Retornar valores por defecto en caso de error
        return {
            'proveedor_razon_social': 'SysNeg S.A.',
            'proveedor_cuit': '30-XXXXXXXX-9',
            'proveedor_domicilio': 'Ciudad Autónoma de Buenos Aires, Argentina',
            'moneda': 'ARS',
            'periodicidad': 'mensual',
            'dias_vencimiento': 30,
            'dias_preaviso': 30,
            'dias_retencion': 30
        }
import io

router = APIRouter()

class ContratoCreate(BaseModel):
    presupuesto_id: str
    detalles: str

class ContratoServicioCreate(BaseModel):
    servicio_id: str
    duracion_meses: int = 3
    renovacion_automatica: bool = True
    detalles: str = ""

@router.post("/contratos")
async def crear_contrato(contrato: ContratoCreate, current_user: dict = Depends(get_current_user)):
    from models.models_beanie import Presupuesto
    presupuesto = await Presupuesto.get(contrato.presupuesto_id)
    if not presupuesto or presupuesto.usuario_id != current_user["user_id"]:
        raise HTTPException(status_code=404, detail="Presupuesto no encontrado")
    
    nuevo_contrato = Contrato(
        presupuesto_id=contrato.presupuesto_id,
        usuario_id=current_user["user_id"],
        detalles=contrato.detalles,
        estado="pendiente"
    )
    await nuevo_contrato.insert()
    return {"message": "Contrato creado"}

@router.post("/contratos/servicio")
async def crear_contrato_servicio(contrato: ContratoServicioCreate, current_user: dict = Depends(get_current_user)):
    # Asegurar que Beanie esté inicializado
    from db.database import init_beanie_db
    await init_beanie_db()

    # Buscar primero en productos (ya que el admin dashboard maneja productos como servicios)
    from models.models_beanie import Producto
    servicio = None
    precio_base = 0

    # Intentar encontrar en productos primero
    producto = await Producto.get(contrato.servicio_id)
    if producto:
        # Convertir producto a formato de servicio para el contrato
        servicio = producto
        precio_base = float(producto.precio) if producto.precio else 0
    else:
        # Si no es producto, buscar en servicios
        servicio = await Servicio.get(contrato.servicio_id)
        if servicio:
            precio_base = servicio.precio_base

    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")

    # Check if user already has an active contract for this service
    existing_contract = await Contrato.find_one(
        Contrato.usuario_id == current_user["user_id"],
        Contrato.servicio_id == contrato.servicio_id,
        Contrato.estado == "activo"
    )
    if existing_contract:
        raise HTTPException(status_code=400, detail="Ya tienes un contrato activo para este servicio")

    fecha_inicio = datetime.utcnow()
    fecha_fin = fecha_inicio + timedelta(days=contrato.duracion_meses * 30)  # Approximate months

    nuevo_contrato = Contrato(
        usuario_id=current_user["user_id"],
        servicio_id=contrato.servicio_id,
        precio_mensual=precio_base,
        duracion_meses=contrato.duracion_meses,
        renovacion_automatica=contrato.renovacion_automatica,
        fecha_contrato=fecha_inicio,
        fecha_fin=fecha_fin,
        estado="pendiente",  # Will be activated by admin
        detalles=contrato.detalles
    )
    await nuevo_contrato.insert()

    # Send email notification to user
    try:
        from Services.mail.mail import enviar_correo
        user_email = current_user.get("email")
        if user_email:
            service_name = getattr(servicio, 'nombre', 'Servicio')
            subject = f"Contrato de {service_name} creado"
            message = f"""
Hola {current_user.get("nombre") or current_user.get("username") or 'Usuario'},

Tu contrato para el servicio "{service_name}" ha sido creado exitosamente.

Detalles del contrato:
- Servicio: {service_name}
- Precio mensual: ${precio_base}
- Duración: {contrato.duracion_meses} meses
- Renovación automática: {'Sí' if contrato.renovacion_automatica else 'No'}
- Estado: Pendiente de aprobación

El contrato será revisado por nuestro equipo administrativo y te notificaremos cuando sea activado.

Gracias por elegir nuestros servicios.

Atentamente,
Equipo de Servicios Profesionales
"""
            enviar_correo(user_email, subject, message)
    except Exception as e:
        print(f"Error sending email: {e}")

    return {"message": "Contrato de servicio creado exitosamente. Será revisado por nuestro equipo."}

@router.get("/contratos", response_model=List[Contrato])
async def listar_contratos(current_user: dict = Depends(get_current_user)):
    contratos = await Contrato.find(Contrato.usuario_id == current_user["user_id"]).to_list()
    return contratos

@router.get("/contratos/usuario")
async def listar_contratos_usuario(current_user: dict = Depends(get_current_user)):
    """Obtener contratos del usuario actual con información del servicio"""
    # Asegurar que Beanie esté inicializado
    from db.database import init_beanie_db
    await init_beanie_db()
    
    contratos = await Contrato.find(Contrato.usuario_id == current_user["user_id"]).to_list()
    
    # Enriquecer contratos con información del servicio
    contratos_enriquecidos = []
    for contrato in contratos:
        contrato_dict = contrato.dict()
        contrato_dict['id'] = str(contrato.id)
        
        # Obtener información del servicio (buscar primero en productos, luego en servicios)
        if contrato.servicio_id:
            try:
                from models.models_beanie import Producto
                servicio_info = None

                # Buscar primero en productos
                producto = await Producto.get(contrato.servicio_id)
                if producto:
                    servicio_info = {
                        'id': str(producto.id),
                        'nombre': producto.nombre or 'Sin nombre',
                        'descripcion': producto.descripcion or 'Sin descripción',
                        'tipo_servicio': producto.categoria or 'Sin categoría',
                        'precio_base': float(producto.precio) if producto.precio else 0
                    }
                else:
                    # Si no es producto, buscar en servicios
                    servicio = await Servicio.get(contrato.servicio_id)
                    if servicio:
                        servicio_info = {
                            'id': str(servicio.id),
                            'nombre': servicio.nombre,
                            'descripcion': servicio.descripcion,
                            'tipo_servicio': servicio.tipo_servicio,
                            'precio_base': servicio.precio_base
                        }

                if servicio_info:
                    contrato_dict['servicio'] = servicio_info
                else:
                    contrato_dict['servicio'] = {'nombre': 'Servicio no encontrado'}
            except Exception as e:
                contrato_dict['servicio'] = {'nombre': 'Error al cargar servicio'}
        else:
            contrato_dict['servicio'] = {'nombre': 'Sin servicio asignado'}
        
        contratos_enriquecidos.append(contrato_dict)
    
    return contratos_enriquecidos

@router.get("/contratos/{contrato_id}/pdf")
async def descargar_contrato_pdf(contrato_id: str, current_user: dict = Depends(get_current_user)):
    """Descargar PDF del contrato"""
    try:
        # Asegurar que Beanie esté inicializado
        from db.database import init_beanie_db
        await init_beanie_db()

        # Buscar el contrato
        contrato = await Contrato.get(contrato_id)
        if not contrato:
            raise HTTPException(status_code=404, detail="Contrato no encontrado")

        # Verificar que el contrato pertenece al usuario actual
        if contrato.usuario_id != current_user["user_id"]:
            raise HTTPException(status_code=403, detail="No tienes permiso para acceder a este contrato")

        # Preparar datos del contrato
        contrato_dict = contrato.dict()
        contrato_dict['id'] = str(contrato.id)

        # Obtener información del servicio (buscar primero en productos, luego en servicios)
        servicio_info = {'nombre': 'Servicio no encontrado'}
        if contrato.servicio_id:
            try:
                from models.models_beanie import Producto
                # Buscar primero en productos
                producto = await Producto.get(contrato.servicio_id)
                if producto:
                    servicio_info = {
                        'id': str(producto.id),
                        'nombre': producto.nombre or 'Sin nombre',
                        'descripcion': producto.descripcion or 'Sin descripción',
                        'tipo_servicio': producto.categoria or 'Sin categoría',
                        'precio_base': float(producto.precio) if producto.precio else 0
                    }
                else:
                    # Si no es producto, buscar en servicios
                    servicio = await Servicio.get(contrato.servicio_id)
                    if servicio:
                        servicio_info = {
                            'id': str(servicio.id),
                            'nombre': servicio.nombre,
                            'descripcion': servicio.descripcion,
                            'tipo_servicio': servicio.tipo_servicio,
                            'precio_base': servicio.precio_base
                        }
            except Exception as e:
                print(f"Error obteniendo servicio: {e}")

        contrato_dict['servicio'] = servicio_info

        # Obtener configuración del contrato desde DB
        contract_config = await get_contract_config()

        # Agregar datos del proveedor (configurables)
        contrato_dict.update({
            'proveedor_razon_social': contract_config.get('proveedor_razon_social'),
            'proveedor_cuit': contract_config.get('proveedor_cuit'),
            'proveedor_domicilio': contract_config.get('proveedor_domicilio'),
            'moneda': contract_config.get('moneda'),
            'periodicidad': contract_config.get('periodicidad'),
            'dias_vencimiento': int(contract_config.get('dias_vencimiento', 30)),
            'dias_preaviso': int(contract_config.get('dias_preaviso', 30)),
            'dias_retencion': int(contract_config.get('dias_retencion', 30)),
            'precio_acordado': contrato.precio_mensual or servicio_info.get('precio_base', 0)
        })

        # Preparar datos del usuario (agregar campos adicionales si están disponibles)
        user_data = {
            'email': current_user.get('email', 'N/A'),
            'username': current_user.get('username', 'N/A'),
            'nombre': current_user.get('nombre', 'N/A'),
            'razon_social': current_user.get('razon_social', current_user.get('nombre', 'Cliente')),
            'cuit': current_user.get('cuit', 'XX-XXXXXXXX-X'),
            'domicilio': current_user.get('domicilio', 'Domicilio del Cliente')
        }

        # Generar PDF
        pdf_buffer = generate_contract_pdf(contrato_dict, user_data)

        # Crear respuesta de streaming
        def iter_pdf():
            yield pdf_buffer.getvalue()

        filename = f"contrato_{contrato_id}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            iter_pdf(),
            media_type='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Length': str(len(pdf_buffer.getvalue()))
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error generando PDF: {e}")
        raise HTTPException(status_code=500, detail="Error interno del servidor al generar el PDF")