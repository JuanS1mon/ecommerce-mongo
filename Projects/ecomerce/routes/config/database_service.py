"""
Servicio centralizado para operaciones de base de datos.
Maneja consultas de tablas, schemas y datos de forma segura.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime

from .security_utils import (
    validate_table_name,
    sanitize_identifier,
    validate_pagination_params,
    ValidationError,
    DatabaseError
)

logger = logging.getLogger(__name__)


class DatabaseService:
    """Servicio para operaciones de base de datos de forma segura."""
    
    def __init__(self):
        self.schema_name = 'dbo'
    
    def get_all_tables(self) -> List[Dict[str, Any]]:
        """
        Obtiene todas las tablas de la base de datos con su información.
        Optimizado para evitar queries N+1.
        
        Returns:
            Lista de diccionarios con información de tablas
            
        Raises:
            DatabaseError: Si hay error en la consulta
        """
        try:
            # Query optimizada que obtiene toda la información en una sola consulta
                SELECT 
                    t.TABLE_NAME as name,
                    t.TABLE_SCHEMA as schema_name,
                    t.TABLE_TYPE as type,
                    COUNT(DISTINCT c.COLUMN_NAME) as column_count
                FROM INFORMATION_SCHEMA.TABLES t
                LEFT JOIN INFORMATION_SCHEMA.COLUMNS c 
                    ON t.TABLE_NAME = c.TABLE_NAME 
                    AND t.TABLE_SCHEMA = c.TABLE_SCHEMA
                WHERE t.TABLE_SCHEMA = :schema_name
                    AND t.TABLE_TYPE = 'BASE TABLE'
                GROUP BY t.TABLE_NAME, t.TABLE_SCHEMA, t.TABLE_TYPE
                ORDER BY t.TABLE_NAME
            """)
            
                tables = []
                
                for row in result:
                    table_info = {
                        "name": row.name,
                        "schema": row.schema_name,
                        "type": row.type,
                        "column_count": row.column_count or 0,
                        "record_count": 0  # Se calculará bajo demanda
                    }
                    tables.append(table_info)
                
                logger.info(
                    "Tables retrieved successfully",
                    extra={"table_count": len(tables)}
                )
                
                return tables
                
        except Exception as e:
            logger.error(f"Error retrieving tables: {str(e)}", exc_info=True)
            raise DatabaseError(f"Error al obtener lista de tablas: {str(e)}")
    
    def get_table_record_count(self, table_name: str) -> int:
        """
        Obtiene el conteo de registros de una tabla de forma segura.
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Número de registros
            
        Raises:
            ValidationError: Si el nombre es inválido
            DatabaseError: Si hay error en la consulta
        """
        # Validar nombre
        is_valid, msg = validate_table_name(table_name)
        if not is_valid:
            raise ValidationError(msg)
        
        try:
            safe_name = sanitize_identifier(table_name)
            
                count = result.fetchone().count
                
                logger.debug(
                    "Table record count retrieved",
                    extra={"table": table_name, "count": count}
                )
                
                return count
                
        except Exception as e:
            logger.warning(
                f"Error counting records for table {table_name}: {str(e)}"
            )
            return 0
    
    def get_table_columns(self, table_name: str) -> List[Dict[str, Any]]:
        """
        Obtiene información de columnas de una tabla.
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Lista de diccionarios con información de columnas
            
        Raises:
            ValidationError: Si el nombre es inválido
            DatabaseError: Si hay error en la consulta
        """
        # Validar nombre
        is_valid, msg = validate_table_name(table_name)
        if not is_valid:
            raise ValidationError(msg)
        
        try:
                SELECT 
                    COLUMN_NAME as name,
                    DATA_TYPE as type,
                    IS_NULLABLE as nullable,
                    COLUMN_DEFAULT as default_value,
                    CHARACTER_MAXIMUM_LENGTH as max_length,
                    NUMERIC_PRECISION as precision,
                    NUMERIC_SCALE as scale,
                    ORDINAL_POSITION as position
                FROM INFORMATION_SCHEMA.COLUMNS 
                WHERE TABLE_NAME = :table_name
                    AND TABLE_SCHEMA = :schema_name
                ORDER BY ORDINAL_POSITION
            """)
            
                    "table_name": table_name,
                    "schema_name": self.schema_name
                })
                
                columns = []
                for row in result:
                    columns.append({
                        "name": row.name,
                        "type": row.type,
                        "nullable": row.nullable == "YES",
                        "default": row.default_value,
                        "max_length": row.max_length,
                        "precision": row.precision,
                        "scale": row.scale,
                        "position": row.position
                    })
                
                logger.debug(
                    "Table columns retrieved",
                    extra={"table": table_name, "column_count": len(columns)}
                )
                
                return columns
                
        except Exception as e:
            logger.error(
                f"Error retrieving columns for table {table_name}: {str(e)}",
                exc_info=True
            )
            raise DatabaseError(f"Error al obtener columnas: {str(e)}")
    
    def get_table_schema(self, table_name: str) -> Dict[str, Any]:
        """
        Obtiene el schema completo de una tabla incluyendo claves y relaciones.
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            Diccionario con información completa del schema
            
        Raises:
            ValidationError: Si el nombre es inválido
            DatabaseError: Si hay error en la consulta
        """
        # Validar nombre
        is_valid, msg = validate_table_name(table_name)
        if not is_valid:
            raise ValidationError(msg)
        
        try:
            # Query compleja para obtener toda la información del schema
                SELECT 
                    c.COLUMN_NAME as name,
                    c.DATA_TYPE as data_type,
                    c.CHARACTER_MAXIMUM_LENGTH as max_length,
                    c.NUMERIC_PRECISION as precision,
                    c.NUMERIC_SCALE as scale,
                    c.IS_NULLABLE as nullable,
                    c.COLUMN_DEFAULT as default_value,
                    c.ORDINAL_POSITION as position,
                    CASE 
                        WHEN pk.COLUMN_NAME IS NOT NULL THEN 1
                        ELSE 0
                    END as is_primary_key,
                    CASE 
                        WHEN fk.COLUMN_NAME IS NOT NULL THEN 1
                        ELSE 0
                    END as is_foreign_key,
                    fk.REFERENCED_TABLE_NAME as references_table,
                    fk.REFERENCED_COLUMN_NAME as references_column
                FROM INFORMATION_SCHEMA.COLUMNS c
                LEFT JOIN (
                    SELECT ku.COLUMN_NAME
                    FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS tc
                    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                        ON tc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                        AND tc.TABLE_SCHEMA = ku.TABLE_SCHEMA
                    WHERE tc.TABLE_NAME = :table_name
                        AND tc.TABLE_SCHEMA = :schema_name
                        AND tc.CONSTRAINT_TYPE = 'PRIMARY KEY'
                ) pk ON c.COLUMN_NAME = pk.COLUMN_NAME
                LEFT JOIN (
                    SELECT 
                        ku.COLUMN_NAME,
                        ku2.TABLE_NAME as REFERENCED_TABLE_NAME,
                        ku2.COLUMN_NAME as REFERENCED_COLUMN_NAME
                    FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS rc
                    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku
                        ON rc.CONSTRAINT_NAME = ku.CONSTRAINT_NAME
                        AND rc.CONSTRAINT_SCHEMA = ku.CONSTRAINT_SCHEMA
                    INNER JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE ku2
                        ON rc.UNIQUE_CONSTRAINT_NAME = ku2.CONSTRAINT_NAME
                        AND rc.UNIQUE_CONSTRAINT_SCHEMA = ku2.CONSTRAINT_SCHEMA
                    WHERE ku.TABLE_NAME = :table_name
                        AND ku.TABLE_SCHEMA = :schema_name
                ) fk ON c.COLUMN_NAME = fk.COLUMN_NAME
                WHERE c.TABLE_NAME = :table_name
                    AND c.TABLE_SCHEMA = :schema_name
                ORDER BY c.ORDINAL_POSITION
            """)
            
                    "table_name": table_name,
                    "schema_name": self.schema_name
                })
                
                columns = []
                primary_keys = []
                foreign_keys = []
                
                for row in result:
                    column_info = {
                        "name": row.name,
                        "data_type": row.data_type,
                        "max_length": row.max_length,
                        "precision": row.precision,
                        "scale": row.scale,
                        "nullable": row.nullable == "YES",
                        "default_value": row.default_value,
                        "position": row.position,
                        "is_primary_key": bool(row.is_primary_key),
                        "is_foreign_key": bool(row.is_foreign_key),
                        "references_table": row.references_table,
                        "references_column": row.references_column
                    }
                    
                    columns.append(column_info)
                    
                    if column_info["is_primary_key"]:
                        primary_keys.append(column_info)
                    
                    if column_info["is_foreign_key"]:
                        foreign_keys.append(column_info)
                
                schema_info = {
                    "table_name": table_name,
                    "schema": self.schema_name,
                    "columns": columns,
                    "primary_keys": primary_keys,
                    "foreign_keys": foreign_keys,
                    "column_count": len(columns)
                }
                
                logger.info(
                    "Table schema retrieved",
                    extra={
                        "table": table_name,
                        "columns": len(columns),
                        "pk_count": len(primary_keys),
                        "fk_count": len(foreign_keys)
                    }
                )
                
                return schema_info
                
        except Exception as e:
            logger.error(
                f"Error retrieving schema for table {table_name}: {str(e)}",
                exc_info=True
            )
            raise DatabaseError(f"Error al obtener schema: {str(e)}")
    
    def get_table_data(
        self,
        table_name: str,
        page: int = 1,
        per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Obtiene datos paginados de una tabla.
        
        Args:
            table_name: Nombre de la tabla
            page: Número de página
            per_page: Registros por página
            
        Returns:
            Diccionario con datos paginados y metadatos
            
        Raises:
            ValidationError: Si los parámetros son inválidos
            DatabaseError: Si hay error en la consulta
        """
        # Validar nombre de tabla
        is_valid, msg = validate_table_name(table_name)
        if not is_valid:
            raise ValidationError(msg)
        
        # Validar y normalizar parámetros de paginación
        valid_pagination, msg, page, per_page = validate_pagination_params(page, per_page)
        if not valid_pagination:
            raise ValidationError(msg)
        
        try:
            offset = (page - 1) * per_page
            safe_name = sanitize_identifier(table_name)
            
                # Obtener total de registros
                total_records = count_result.fetchone().total
                
                # Obtener datos paginados
                    SELECT * FROM {safe_name}
                    ORDER BY (SELECT NULL)
                    OFFSET :offset ROWS 
                    FETCH NEXT :per_page ROWS ONLY
                """)
                
                    "offset": offset,
                    "per_page": per_page
                })
                
                # Convertir resultados a lista de diccionarios
                columns = data_result.keys()
                records = []
                
                for row in data_result:
                    record = {}
                    for i, column in enumerate(columns):
                        value = row[i]
                        # Convertir tipos especiales a string para JSON
                        if hasattr(value, 'isoformat'):  # datetime objects
                            value = value.isoformat()
                        elif isinstance(value, bytes):  # binary data
                            value = f"<binary data: {len(value)} bytes>"
                        elif value is None:
                            value = None
                        
                        record[column] = value
                    
                    records.append(record)
                
                # Calcular información de paginación
                total_pages = (total_records + per_page - 1) // per_page
                
                result = {
                    "status": "success",
                    "table_name": table_name,
                    "records": records,
                    "pagination": {
                        "current_page": page,
                        "per_page": per_page,
                        "total_records": total_records,
                        "total_pages": total_pages,
                        "has_next": page < total_pages,
                        "has_prev": page > 1
                    },
                    "columns": list(columns)
                }
                
                logger.info(
                    "Table data retrieved",
                    extra={
                        "table": table_name,
                        "page": page,
                        "records": len(records)
                    }
                )
                
                return result
                
        except Exception as e:
            logger.error(
                f"Error retrieving data for table {table_name}: {str(e)}",
                exc_info=True
            )
            raise DatabaseError(f"Error al obtener datos: {str(e)}")
    
    def table_exists(self, table_name: str) -> bool:
        """
        Verifica si una tabla existe.
        
        Args:
            table_name: Nombre de la tabla
            
        Returns:
            True si existe, False en caso contrario
        """
        try:
                SELECT COUNT(*) as count
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_NAME = :table_name 
                AND TABLE_SCHEMA = :schema_name
            """)
            
                    "table_name": table_name,
                    "schema_name": self.schema_name
                })
                return result.fetchone().count > 0
                
        except Exception as e:
            logger.error(f"Error checking table existence: {str(e)}")
            return False
    
    def get_table_info_batch(self, table_names: List[str]) -> Dict[str, Dict[str, Any]]:
        """
        Obtiene información de múltiples tablas en batch.
        
        Args:
            table_names: Lista de nombres de tablas
            
        Returns:
            Diccionario con información de cada tabla
        """
        results = {}
        
        for table_name in table_names:
            try:
                is_valid, _ = validate_table_name(table_name)
                if not is_valid:
                    results[table_name] = {"error": "Nombre inválido"}
                    continue
                
                columns = self.get_table_columns(table_name)
                record_count = self.get_table_record_count(table_name)
                
                results[table_name] = {
                    "columns": columns,
                    "record_count": record_count,
                    "column_count": len(columns)
                }
                
            except Exception as e:
                logger.warning(f"Error getting info for table {table_name}: {str(e)}")
                results[table_name] = {"error": str(e)}
        
        return results

    async def list_user_tables(self) -> list:
        """
        Devuelve una lista de tablas de usuario (no del sistema) para el explorador dinámico.
        Cada tabla es un dict con: name, record_count, column_count, columns (vacío).
        """
        try:
            all_tables = self.get_all_tables()
            user_tables = []
            import re
            valid_name = lambda n: bool(re.match(r'^[A-Za-z][A-Za-z0-9_]*$', n or ''))
            blacklist = set([
                'usuario', 'usuarios', 'user', 'users', 'log', 'logs', 'activity_log',
                'auth', 'admin', 'alembic_version', 'migrations', 'session', 'sessions',
                'token', 'tokens', 'password', 'clave', 'claves', 'permisos', 'permissions',
                'roles', 'role', 'config', 'settings', 'parametros', 'parameters',
                'audit', 'auditoria', 'bitacora', 'bitacoras', 'system', 'sistema',
            ])
            for t in all_tables:
                name = t.get("name", "")
                lname = name.lower()
                if (
                    t.get("schema", "dbo") == self.schema_name
                    and t.get("type", "BASE TABLE") == "BASE TABLE"
                    and name
                    and valid_name(name)
                    and lname not in blacklist
                ):
                    try:
                        record_count = self.get_table_record_count(name)
                    except Exception:
                        record_count = 0
                    user_tables.append({
                        "name": name,
                        "record_count": record_count,
                        "column_count": t.get("column_count", 0),
                        "columns": []
                    })
            return user_tables
        except Exception as e:
            logger.error(f"Error en list_user_tables: {str(e)}", exc_info=True)
            return []
