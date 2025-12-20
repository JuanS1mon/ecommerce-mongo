"""
Sistema de Limpieza de Backups del Generador
==========================================

Este módulo maneja la limpieza automática de backups
antiguos y el mantenimiento del sistema de archivos.
"""

import os
import time
import logging
from typing import List, Dict
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

def cleanup_old_backups(backup_dir: str = "Services/backups", retention_days: int = 30) -> Dict[str, int]:
    """
    Limpia backups antiguos basado en la política de retención.
    
    Args:
        backup_dir: Directorio de backups
        retention_days: Días de retención
        
    Returns:
        Dict con estadísticas de limpieza
    """
    try:
        if not os.path.exists(backup_dir):
            logger.info(f"Directorio de backups {backup_dir} no existe")
            return {"deleted": 0, "kept": 0, "errors": 0}
        
        cutoff_time = time.time() - (retention_days * 24 * 60 * 60)
        deleted_count = 0
        kept_count = 0
        error_count = 0
        
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            
            try:
                # Verificar si es un directorio de backup (formato: servicio_timestamp)
                if os.path.isdir(item_path) and "_" in item:
                    # Extraer timestamp del nombre
                    parts = item.split("_")
                    if len(parts) >= 2 and parts[-1].isdigit():
                        timestamp = int(parts[-1])
                        
                        if timestamp < cutoff_time:
                            # Eliminar backup antiguo
                            import shutil
                            shutil.rmtree(item_path)
                            deleted_count += 1
                            logger.info(f"Backup eliminado: {item}")
                        else:
                            kept_count += 1
                            
            except Exception as e:
                logger.error(f"Error procesando backup {item}: {str(e)}")
                error_count += 1
        
        logger.info(f"Limpieza completada: {deleted_count} eliminados, {kept_count} mantenidos, {error_count} errores")
        
        return {
            "deleted": deleted_count,
            "kept": kept_count,
            "errors": error_count
        }
        
    except Exception as e:
        logger.error(f"Error en limpieza de backups: {str(e)}")
        return {"deleted": 0, "kept": 0, "errors": 1}

def get_backup_statistics(backup_dir: str = "Services/backups") -> Dict:
    """
    Obtiene estadísticas de los backups existentes.
    
    Returns:
        Dict con estadísticas de backups
    """
    try:
        if not os.path.exists(backup_dir):
            return {
                "total_backups": 0,
                "total_size_mb": 0,
                "oldest_backup": None,
                "newest_backup": None,
                "services_with_backups": []
            }
        
        backups = []
        total_size = 0
        services = set()
        
        for item in os.listdir(backup_dir):
            item_path = os.path.join(backup_dir, item)
            
            if os.path.isdir(item_path) and "_" in item:
                # Calcular tamaño del directorio
                dir_size = get_directory_size(item_path)
                total_size += dir_size
                
                # Extraer información del backup
                parts = item.split("_")
                if len(parts) >= 2 and parts[-1].isdigit():
                    service_name = "_".join(parts[:-1])
                    timestamp = int(parts[-1])
                    
                    services.add(service_name)
                    backups.append({
                        "name": item,
                        "service": service_name,
                        "timestamp": timestamp,
                        "date": datetime.fromtimestamp(timestamp).isoformat(),
                        "size_mb": round(dir_size / (1024 * 1024), 2)
                    })
        
        # Ordenar por timestamp
        backups.sort(key=lambda x: x["timestamp"])
        
        return {
            "total_backups": len(backups),
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "oldest_backup": backups[0] if backups else None,
            "newest_backup": backups[-1] if backups else None,
            "services_with_backups": list(services),
            "backups": backups
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo estadísticas de backups: {str(e)}")
        return {"error": str(e)}

def get_directory_size(path: str) -> int:
    """
    Calcula el tamaño total de un directorio recursivamente.
    
    Args:
        path: Ruta del directorio
        
    Returns:
        Tamaño total en bytes
    """
    total_size = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, FileNotFoundError):
                    pass
    except Exception:
        pass
    
    return total_size

def schedule_cleanup_task():
    """
    Programa la tarea de limpieza automática.
    Esta función puede ser llamada al iniciar la aplicación.
    """
    import threading
    import schedule
    
    def run_cleanup():
        logger.info("Ejecutando limpieza automática de backups")
        result = cleanup_old_backups()
        logger.info(f"Limpieza completada: {result}")
    
    # Programar limpieza diaria a las 2:00 AM
    schedule.every().day.at("02:00").do(run_cleanup)
    
    def run_scheduler():
        while True:
            schedule.run_pending()
            time.sleep(60)  # Verificar cada minuto
    
    # Ejecutar scheduler en un hilo separado
    scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
    scheduler_thread.start()
    
    logger.info("Sistema de limpieza automática inicializado")

if __name__ == "__main__":
    # Prueba manual de limpieza
    result = cleanup_old_backups()
    print(f"Resultado de limpieza: {result}")
    
    stats = get_backup_statistics()
    print(f"Estadísticas de backups: {stats}")
