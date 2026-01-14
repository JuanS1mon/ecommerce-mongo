"""
Script de Sincronización de Usuarios Admin
==========================================

Este script sincroniza los usuarios administradores entre el sistema de 
gestión de proyectos y esta aplicación de ecommerce.

Uso:
    # Simulación (no hace cambios)
    python sincronizar_usuarios_admin.py --dry-run
    
    # Ejecución real
    python sincronizar_usuarios_admin.py
    
Requisitos:
    - La API del proyecto debe estar accesible en API_BASE_URL
    - ADMIN_PROYECTO_NOMBRE debe estar configurado en .env
    - MongoDB debe estar corriendo y accesible
"""

import asyncio
import sys
import argparse
import logging
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Asegurar que el directorio raíz esté en el path
sys.path.insert(0, str(Path(__file__).parent))

from db.database import init_database
from Projects.Admin.services.sincronizar_usuarios import sincronizar_usuarios_admin

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def main():
    """Función principal del script."""
    
    # Parsear argumentos
    parser = argparse.ArgumentParser(description='Sincronizar usuarios admin entre aplicaciones')
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Simular sin hacer cambios reales en la base de datos'
    )
    args = parser.parse_args()
    
    try:
        logger.info("=" * 70)
        logger.info("SINCRONIZACIÓN DE USUARIOS ADMIN")
        logger.info("=" * 70)
        
        # Verificar configuración
        api_base_url = os.getenv("API_BASE_URL")
        proyecto_nombre = os.getenv("ADMIN_PROYECTO_NOMBRE")
        
        if not api_base_url:
            logger.error("❌ API_BASE_URL no configurado en .env")
            return 1
        
        if not proyecto_nombre:
            logger.error("❌ ADMIN_PROYECTO_NOMBRE no configurado en .env")
            return 1
        
        logger.info(f"📍 API Base URL: {api_base_url}")
        logger.info(f"📁 Proyecto: {proyecto_nombre}")
        
        if args.dry_run:
            logger.info("🔍 MODO DRY RUN - No se harán cambios reales")
        
        logger.info("-" * 70)
        
        # Inicializar MongoDB
        logger.info("🔌 Conectando a MongoDB...")
        await init_database()
        logger.info("✅ MongoDB conectado")
        
        # Ejecutar sincronización
        logger.info("🔄 Iniciando sincronización...")
        estadisticas = await sincronizar_usuarios_admin(dry_run=args.dry_run)
        
        # Mostrar resultados
        logger.info("=" * 70)
        logger.info("RESULTADOS DE LA SINCRONIZACIÓN")
        logger.info("=" * 70)
        logger.info(f"👥 Usuarios remotos: {estadisticas['usuarios_remotos']}")
        logger.info(f"💾 Usuarios locales: {estadisticas['usuarios_locales']}")
        logger.info(f"➕ Usuarios creados: {estadisticas['usuarios_creados']}")
        logger.info(f"🔄 Usuarios actualizados: {estadisticas['usuarios_actualizados']}")
        logger.info(f"🔒 Usuarios desactivados: {estadisticas['usuarios_desactivados']}")
        
        if estadisticas['errores']:
            logger.warning(f"⚠️  Errores encontrados: {len(estadisticas['errores'])}")
            for error in estadisticas['errores']:
                logger.error(f"   - {error}")
        else:
            logger.info("✅ No se encontraron errores")
        
        logger.info("=" * 70)
        
        if args.dry_run:
            logger.info("🔍 DRY RUN completado - No se realizaron cambios")
        else:
            logger.info("✅ Sincronización completada exitosamente")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Error en sincronización: {str(e)}", exc_info=True)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
