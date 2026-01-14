"""
Script para crear vinculaciones de usuarios admin al proyecto Ecomerce
"""
import asyncio
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main():
    logger.info("=" * 80)
    logger.info("CREAR VINCULACIONES USUARIO-PROYECTO")
    logger.info("=" * 80)
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    
    # Inicializar Beanie
    await init_beanie(
        database=client.db_ecomerce,
        document_models=[AdminUsuarios, Proyecto, UsuarioProyecto]
    )
    
    proyecto_nombre = "Ecomerce"
    
    # Buscar o crear proyecto
    proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
    
    if not proyecto:
        logger.info(f"📁 Creando proyecto: {proyecto_nombre}")
        proyecto = Proyecto(
            nombre=proyecto_nombre,
            descripcion=f"Proyecto {proyecto_nombre}",
            activo=True
        )
        await proyecto.save()
        logger.info(f"✅ Proyecto creado: {proyecto.id}")
    else:
        logger.info(f"📁 Proyecto encontrado: {proyecto.nombre} (ID: {proyecto.id})")
    
    # Buscar todos los usuarios admin del proyecto
    usuarios = await AdminUsuarios.find(
        AdminUsuarios.proyecto_nombre == proyecto_nombre
    ).to_list()
    
    logger.info(f"👥 Encontrados {len(usuarios)} usuarios para vincular")
    
    vinculaciones_creadas = 0
    vinculaciones_existentes = 0
    
    for usuario in usuarios:
        # Verificar si ya existe vinculación
        vinculacion_existente = await UsuarioProyecto.find_one(
            UsuarioProyecto.usuario_id == usuario.id,
            UsuarioProyecto.proyecto_id == proyecto.id
        )
        
        if vinculacion_existente:
            logger.info(f"  ⏭️  {usuario.mail} - Vinculación ya existe")
            vinculaciones_existentes += 1
        else:
            # Crear vinculación
            vinculacion = UsuarioProyecto(
                usuario_id=usuario.id,
                proyecto_id=proyecto.id,
                fecha_vencimiento=usuario.fecha_vencimiento,
                activo=usuario.activo
            )
            await vinculacion.save()
            logger.info(f"  ✅ {usuario.mail} - Vinculación creada")
            vinculaciones_creadas += 1
    
    logger.info("=" * 80)
    logger.info("RESUMEN")
    logger.info("=" * 80)
    logger.info(f"✅ Vinculaciones creadas: {vinculaciones_creadas}")
    logger.info(f"⏭️  Vinculaciones existentes: {vinculaciones_existentes}")
    logger.info(f"👥 Total usuarios: {len(usuarios)}")
    logger.info("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())
