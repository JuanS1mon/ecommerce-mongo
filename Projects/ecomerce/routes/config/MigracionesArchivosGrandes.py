"""
API Endpoints para Migración de Archivos Grandes
=================================================

Endpoints optimizados para archivos de 500GB+:
- Upload streaming (no carga todo en RAM)
- Background processing con Celery
- Progress tracking en tiempo real
- Cancelación de tareas

Autor: Sistema SQL App
Fecha: 18 de octubre de 2025
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from pathlib import Path
import aiofiles
import logging
import os
import tempfile

from security.auth_middleware import require_role_api
from tasks.file_migration_tasks import (
    migrate_file_to_db,
    get_migration_progress,
    cancel_migration
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/migraciones/archivos-grandes",
    tags=["Migraciones - Archivos Grandes"]
)


# ========================
# MODELOS PYDANTIC
# ========================

class FileUploadResponse(BaseModel):
    """Respuesta de upload de archivo."""
    success: bool
    task_id: str
    file_name: str
    file_size_mb: float
    file_path: str
    message: str
    estimated_time_minutes: Optional[int] = None


class MigrationProgressResponse(BaseModel):
    """Respuesta de progreso de migración."""
    task_id: str
    status: str  # iniciando, procesando, completado, error, cancelado
    percent: int
    stage: str
    processed_rows: Optional[int] = 0
    estimated_total_rows: Optional[int] = None
    chunks_processed: Optional[int] = 0
    started_at: Optional[str] = None
    updated_at: Optional[str] = None
    completed_at: Optional[str] = None
    error: Optional[str] = None


class CancelMigrationResponse(BaseModel):
    """Respuesta de cancelación."""
    success: bool
    task_id: str
    message: str


class MigrationConfigRequest(BaseModel):
    """Configuración de migración."""
    table_name: str = Field(..., description="Nombre de la tabla destino")
    tipo_motor: str = Field(default="sqlserver", description="Motor BD: sqlserver, postgresql, mysql, oracle")
    host: str = Field(..., description="Host de la BD")
    puerto: int = Field(..., description="Puerto de la BD")
    bd: str = Field(..., description="Nombre de la base de datos")
    usuario: str = Field(..., description="Usuario de la BD")
    password: str = Field(..., description="Contraseña de la BD")
    import_mode: str = Field(default="append", description="Modo: append, replace, fail")
    encoding: str = Field(default="utf-8", description="Codificación del archivo")
    delimiter: str = Field(default=",", description="Delimitador para CSV/TXT")
    sheet_name: str = Field(default="0", description="Hoja de Excel (nombre o índice)")


# ========================
# ENDPOINTS
# ========================

@router.post("/upload-streaming", response_model=FileUploadResponse)
async def upload_file_streaming(
    file: UploadFile = File(...),
    user=Depends(require_role_api(["admin"]))
):
    """
    Upload de archivo grande con streaming (NO carga todo en RAM).
    
    Soporta archivos de 500GB+:
    - Streaming upload (chunks de 1MB)
    - Guardado incremental en disco
    - No bloquea la API
    - Retorna task_id para tracking
    
    **Formatos soportados:**
    - CSV (.csv) - Recomendado para archivos 500GB+
    - Excel (.xlsx, .xls) - Hasta 5GB recomendado
    - TXT (.txt) - Delimitado
    - JSON (.json, .jsonl) - JSON Lines recomendado
    - Parquet (.parquet) - ULTRA EFICIENTE, 10x más rápido
    
    Args:
        file: Archivo a subir (multipart/form-data)
        user: Usuario autenticado (admin requerido)
    
    Returns:
        FileUploadResponse con task_id para tracking
    """
    try:
        # Validar extensión
        file_ext = Path(file.filename).suffix.lower()
        
        valid_extensions = {
            '.csv': 'csv',
            '.xlsx': 'excel',
            '.xls': 'excel',
            '.txt': 'txt',
            '.json': 'json',
            '.jsonl': 'json',
            '.parquet': 'parquet'
        }
        
        if file_ext not in valid_extensions:
            raise HTTPException(
                status_code=400,
                detail=f"Extensión no soportada: {file_ext}. Soportados: {', '.join(valid_extensions.keys())}"
            )
        
        file_type = valid_extensions[file_ext]
        
        logger.info(f"📤 Upload streaming iniciado: {file.filename}")
        
        # Crear directorio temporal para archivos grandes
        upload_dir = Path("uploads/large_files")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_filename = f"{timestamp}_{file.filename}"
        file_path = upload_dir / safe_filename
        
        # Guardar archivo con streaming (chunks de 1MB)
        chunk_size = 1024 * 1024  # 1MB
        total_bytes = 0
        
        async with aiofiles.open(file_path, 'wb') as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                
                await f.write(chunk)
                total_bytes += len(chunk)
                
                # Log cada 100MB
                if total_bytes % (100 * 1024 * 1024) == 0:
                    logger.info(f"📥 Subidos: {total_bytes / (1024**3):.2f} GB")
        
        file_size_mb = total_bytes / (1024**2)
        
        logger.info(f"✅ Archivo guardado: {file_path} ({file_size_mb:.2f} MB)")
        
        # Estimar tiempo de procesamiento (heurística)
        # Asumimos ~10MB/segundo de procesamiento
        estimated_seconds = file_size_mb / 10
        estimated_minutes = int(estimated_seconds / 60)
        
        return FileUploadResponse(
            success=True,
            task_id="",  # Se asignará en el endpoint de inicio
            file_name=file.filename,
            file_size_mb=round(file_size_mb, 2),
            file_path=str(file_path),
            message=f"Archivo subido exitosamente. Listo para migración.",
            estimated_time_minutes=estimated_minutes if estimated_minutes > 0 else 1
        )
        
    except Exception as e:
        logger.error(f"❌ Error en upload streaming: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error subiendo archivo: {str(e)}")


@router.post("/iniciar-migracion", response_model=FileUploadResponse)
async def start_migration(
    config: MigrationConfigRequest,
    file_path: str = Form(...),
    file_type: str = Form(...),
    user=Depends(require_role_api(["admin"]))
):
    """
    Inicia la migración de un archivo grande a base de datos.
    
    Proceso:
    1. Valida configuración de BD
    2. Crea tarea Celery asíncrona
    3. Retorna task_id para tracking
    4. El procesamiento continúa en background
    
    Args:
        config: Configuración de migración (BD, tabla, etc.)
        file_path: Ruta del archivo previamente subido
        file_type: Tipo de archivo (csv, excel, txt, json, parquet)
        user: Usuario autenticado
    
    Returns:
        FileUploadResponse con task_id
    """
    try:
        # Validar que el archivo existe
        if not Path(file_path).exists():
            raise HTTPException(
                status_code=404,
                detail=f"Archivo no encontrado: {file_path}"
            )
        
        logger.info(f"🚀 Iniciando migración: {file_path} → {config.table_name}")
        
        # Crear configuración de BD
        db_config = {
            'tipo_motor': config.tipo_motor,
            'host': config.host,
            'puerto': config.puerto,
            'bd': config.bd,
            'usuario': config.usuario,
            'password': config.password
        }
        
        # Lanzar tarea Celery asíncrona
        task = migrate_file_to_db.delay(
            file_path=file_path,
            file_type=file_type,
            table_name=config.table_name,
            db_config=db_config,
            import_mode=config.import_mode,
            encoding=config.encoding,
            delimiter=config.delimiter,
            sheet_name=config.sheet_name
        )
        
        logger.info(f"✅ Tarea Celery creada: {task.id}")
        
        # Obtener tamaño del archivo
        file_size_bytes = Path(file_path).stat().st_size
        file_size_mb = file_size_bytes / (1024**2)
        
        return FileUploadResponse(
            success=True,
            task_id=task.id,
            file_name=Path(file_path).name,
            file_size_mb=round(file_size_mb, 2),
            file_path=file_path,
            message=f"Migración iniciada. Task ID: {task.id}",
            estimated_time_minutes=None
        )
        
    except Exception as e:
        logger.error(f"❌ Error iniciando migración: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/progreso/{task_id}", response_model=MigrationProgressResponse)
async def get_progress(
    task_id: str,
    user=Depends(require_role_api(["admin"]))
):
    """
    Obtiene el progreso de una migración en tiempo real.
    
    Consulta Redis para obtener:
    - Porcentaje completado
    - Cantidad de registros procesados
    - Chunk actual
    - Tiempo estimado restante
    - Estado (iniciando, procesando, completado, error)
    
    Args:
        task_id: ID de la tarea Celery
        user: Usuario autenticado
    
    Returns:
        MigrationProgressResponse con progreso actual
    """
    try:
        # Obtener progreso desde Celery task
        progress_data = get_migration_progress.delay(task_id).get(timeout=5)
        
        return MigrationProgressResponse(
            task_id=task_id,
            status=progress_data.get('status', 'unknown'),
            percent=progress_data.get('percent', 0),
            stage=progress_data.get('stage', 'Consultando estado...'),
            processed_rows=progress_data.get('processed_rows'),
            estimated_total_rows=progress_data.get('estimated_total_rows'),
            chunks_processed=progress_data.get('chunks_processed'),
            started_at=progress_data.get('started_at'),
            updated_at=progress_data.get('updated_at'),
            completed_at=progress_data.get('completed_at'),
            error=progress_data.get('error')
        )
        
    except Exception as e:
        logger.error(f"❌ Error consultando progreso: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/cancelar/{task_id}", response_model=CancelMigrationResponse)
async def cancel_migration_endpoint(
    task_id: str,
    user=Depends(require_role_api(["admin"]))
):
    """
    Cancela una migración en progreso.
    
    Termina la tarea Celery inmediatamente y actualiza el estado en Redis.
    
    Args:
        task_id: ID de la tarea a cancelar
        user: Usuario autenticado
    
    Returns:
        CancelMigrationResponse con resultado
    """
    try:
        result = cancel_migration.delay(task_id).get(timeout=5)
        
        return CancelMigrationResponse(
            success=result['success'],
            task_id=task_id,
            message=result.get('message', 'Cancelación procesada')
        )
        
    except Exception as e:
        logger.error(f"❌ Error cancelando migración: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/health")
async def health_check():
    """
    Verifica que Celery y Redis estén funcionando.
    
    Returns:
        Estado del sistema de background tasks
    """
    try:
        # Verificar conexión a Celery
        from tasks.file_migration_tasks import celery_app, redis_client
        
        # Ping a Redis
        redis_ok = redis_client.ping()
        
        # Obtener workers activos
        stats = celery_app.control.inspect().stats()
        workers_count = len(stats) if stats else 0
        
        return {
            "status": "healthy" if redis_ok and workers_count > 0 else "degraded",
            "redis": "connected" if redis_ok else "disconnected",
            "celery_workers": workers_count,
            "message": "Sistema de archivos grandes operativo" if workers_count > 0 else "⚠️ Sin workers Celery activos"
        }
        
    except Exception as e:
        logger.error(f"❌ Health check failed: {str(e)}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "message": "Sistema de background tasks no disponible"
        }


@router.get("/formatos-soportados")
async def get_supported_formats():
    """
    Lista los formatos de archivo soportados con recomendaciones.
    
    Returns:
        Dict con formatos y recomendaciones
    """
    return {
        "formatos": [
            {
                "extension": ".csv",
                "tipo": "csv",
                "descripcion": "Archivo CSV delimitado",
                "recomendado_para": "Archivos 500GB+",
                "performance": "⭐⭐⭐⭐⭐ Excelente",
                "chunk_size": 50000,
                "notas": "Formato más eficiente para archivos gigantes"
            },
            {
                "extension": ".parquet",
                "tipo": "parquet",
                "descripcion": "Apache Parquet (columnar)",
                "recomendado_para": "Archivos 100GB+ con compresión",
                "performance": "⭐⭐⭐⭐⭐ Excelente (10x más rápido que CSV)",
                "chunk_size": 100000,
                "notas": "Formato ULTRA EFICIENTE, compresión nativa, lectura columnar"
            },
            {
                "extension": ".xlsx / .xls",
                "tipo": "excel",
                "descripcion": "Microsoft Excel",
                "recomendado_para": "Archivos hasta 5GB",
                "performance": "⭐⭐⭐ Regular",
                "chunk_size": 10000,
                "notas": "Para archivos grandes, convertir a CSV primero"
            },
            {
                "extension": ".txt",
                "tipo": "txt",
                "descripcion": "Archivo de texto delimitado",
                "recomendado_para": "Archivos 100GB+",
                "performance": "⭐⭐⭐⭐ Muy buena",
                "chunk_size": 100000,
                "notas": "Similar a CSV, especificar delimitador"
            },
            {
                "extension": ".json / .jsonl",
                "tipo": "json",
                "descripcion": "JSON o JSON Lines",
                "recomendado_para": "Archivos hasta 50GB (usar .jsonl para más)",
                "performance": "⭐⭐⭐ Regular (⭐⭐⭐⭐ con .jsonl)",
                "chunk_size": 25000,
                "notas": "JSON Lines (.jsonl) es MUY superior para archivos grandes"
            }
        ],
        "recomendaciones": {
            "archivos_500gb_plus": "Usar CSV o Parquet exclusivamente",
            "mejor_performance": "Parquet (10x más rápido que CSV)",
            "mas_compatible": "CSV (funciona en cualquier sistema)",
            "excel_grande": "Convertir a CSV antes de migrar"
        }
    }
