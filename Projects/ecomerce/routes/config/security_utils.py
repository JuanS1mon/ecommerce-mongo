"""
Utilidades de seguridad para el generador de código.
Incluye validación de inputs, sanitización y gestión segura de DB.
"""

import re
import logging
from contextlib import contextmanager
from typing import Optional, Tuple, List

logger = logging.getLogger(__name__)

# Patrones de validación
VALID_TABLE_NAME = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$')
VALID_COLUMN_NAME = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,63}$')
VALID_MODULE_NAME = re.compile(r'^[a-zA-Z][a-zA-Z0-9_]{0,50}$')

# Palabras reservadas SQL Server
SQL_RESERVED_WORDS = {
    'select', 'insert', 'update', 'delete', 'drop', 'create', 'alter',
    'table', 'database', 'index', 'view', 'procedure', 'function',
    'trigger', 'where', 'from', 'join', 'union', 'order', 'group',
    'having', 'exec', 'execute', 'sp_', 'xp_', 'master', 'sys'
}

class ValidationError(Exception):
    """Error de validación de entrada"""
    pass


class DatabaseError(Exception):
    """Error de operación de base de datos"""
    pass


def validate_table_name(table_name: str) -> Tuple[bool, str]:
    """
    Valida que un nombre de tabla sea seguro y válido.
    
    Args:
        table_name: Nombre de la tabla a validar
        
    Returns:
        Tupla (válido, mensaje)
    """
    if not table_name or not isinstance(table_name, str):
        return False, "El nombre de tabla no puede estar vacío"
    
    # Eliminar espacios
    table_name = table_name.strip()
    
    # Validar longitud
    if len(table_name) > 64:
        return False, "El nombre de tabla no puede exceder 64 caracteres"
    
    # Validar formato
    if not VALID_TABLE_NAME.match(table_name):
        return False, "El nombre de tabla debe comenzar con letra y contener solo letras, números y guiones bajos"
    
    # Verificar palabras reservadas
    if table_name.lower() in SQL_RESERVED_WORDS or table_name.lower().startswith(('sp_', 'xp_')):
        return False, "El nombre de tabla usa una palabra reservada de SQL"
    
    return True, "Nombre de tabla válido"


def validate_column_name(column_name: str) -> Tuple[bool, str]:
    """
    Valida que un nombre de columna sea seguro y válido.
    
    Args:
        column_name: Nombre de la columna a validar
        
    Returns:
        Tupla (válido, mensaje)
    """
    if not column_name or not isinstance(column_name, str):
        return False, "El nombre de columna no puede estar vacío"
    
    column_name = column_name.strip()
    
    if len(column_name) > 64:
        return False, "El nombre de columna no puede exceder 64 caracteres"
    
    if not VALID_COLUMN_NAME.match(column_name):
        return False, "El nombre de columna debe comenzar con letra y contener solo letras, números y guiones bajos"
    
    if column_name.lower() in SQL_RESERVED_WORDS:
        return False, "El nombre de columna usa una palabra reservada de SQL"
    
    return True, "Nombre de columna válido"


def sanitize_identifier(identifier: str) -> str:
    """
    Sanitiza un identificador SQL (tabla o columna).
    
    Args:
        identifier: El identificador a sanitizar
        
    Returns:
        El identificador sanitizado y escapado
        
    Raises:
        ValidationError: Si el identificador no es válido
    """
    is_valid, msg = validate_table_name(identifier)
    if not is_valid:
        raise ValidationError(msg)
    
    # Escapar con corchetes para SQL Server
    return f"[{identifier}]"


def build_safe_query(query_template: str, **params) -> text:
    """
    Construye una query SQL parametrizada de forma segura.
    
    Args:
        query_template: Template de la query con placeholders
        **params: Parámetros para la query
        
    Returns:
    """


@contextmanager
    """
    Context manager para obtener una sesión de base de datos.
    Asegura que la sesión se cierre correctamente.
    
    Yields:
        Sesión de base de datos
        
    Example:
    """
    db = next(db_gen)
    try:
        yield db
    except SQLAlchemyError as e:
        logger.error(f"Error en operación de base de datos: {str(e)}", exc_info=True)
        raise DatabaseError(f"Error en la base de datos: {str(e)}")
    finally:
        try:
            db.close()
        except Exception as e:
            logger.error(f"Error cerrando sesión de DB: {str(e)}")


def execute_safe_query(query: text, params: dict = None, fetch_mode: str = "all"):
    """
    Ejecuta una query de forma segura con manejo de errores.
    
    Args:
        query: Query SQL parametrizada
        params: Parámetros para la query
        fetch_mode: Modo de obtención de resultados ("all", "one", "none")
        
    Returns:
        Resultados de la query según fetch_mode
        
    Raises:
        DatabaseError: Si hay un error en la ejecución
    """
        try:
            
            if fetch_mode == "all":
                return result.fetchall()
            elif fetch_mode == "one":
                return result.fetchone()
            elif fetch_mode == "none":
                return None
            else:
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Error ejecutando query: {str(e)}", exc_info=True)
            raise DatabaseError(f"Error ejecutando query: {str(e)}")


def validate_pagination_params(page: int, per_page: int) -> Tuple[bool, str, int, int]:
    """
    Valida y normaliza parámetros de paginación.
    
    Args:
        page: Número de página
        per_page: Registros por página
        
    Returns:
        Tupla (válido, mensaje, page_normalizado, per_page_normalizado)
    """
    MAX_PER_PAGE = 1000
    DEFAULT_PER_PAGE = 50
    
    try:
        page = int(page)
        per_page = int(per_page)
    except (ValueError, TypeError):
        return False, "Los parámetros de paginación deben ser números", 1, DEFAULT_PER_PAGE
    
    if page < 1:
        page = 1
    
    if per_page < 1:
        per_page = DEFAULT_PER_PAGE
    elif per_page > MAX_PER_PAGE:
        return False, f"El máximo de registros por página es {MAX_PER_PAGE}", page, MAX_PER_PAGE
    
    return True, "Parámetros válidos", page, per_page


def get_safe_table_count(table_name: str) -> int:
    """
    Obtiene el conteo de registros de una tabla de forma segura.
    
    Args:
        table_name: Nombre de la tabla (será validado)
        
    Returns:
        Número de registros en la tabla
        
    Raises:
        ValidationError: Si el nombre de tabla no es válido
        DatabaseError: Si hay un error en la consulta
    """
    # Validar nombre de tabla
    is_valid, msg = validate_table_name(table_name)
    if not is_valid:
        raise ValidationError(msg)
    
    # Usar query parametrizada
        SELECT COUNT(*) as count 
        FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_NAME = :table_name 
        AND TABLE_SCHEMA = 'dbo'
    """)
    
        # Verificar que la tabla existe
        exists = result.fetchone()
        
        if not exists or exists.count == 0:
            raise ValidationError(f"La tabla '{table_name}' no existe")
        
        # Ahora sí obtener el conteo (aquí podemos usar el nombre sanitizado)
        safe_name = sanitize_identifier(table_name)
        
        return count_result.fetchone().count


def batch_validate_identifiers(identifiers: List[str], identifier_type: str = "table") -> List[Tuple[str, bool, str]]:
    """
    Valida múltiples identificadores en batch.
    
    Args:
        identifiers: Lista de identificadores a validar
        identifier_type: Tipo de identificador ("table" o "column")
        
    Returns:
        Lista de tuplas (identificador, válido, mensaje)
    """
    results = []
    validator = validate_table_name if identifier_type == "table" else validate_column_name
    
    for identifier in identifiers:
        is_valid, msg = validator(identifier)
        results.append((identifier, is_valid, msg))
    
    return results


# Constantes de configuración
DB_QUERY_TIMEOUT = 30  # segundos
MAX_BATCH_SIZE = 100
CACHE_TTL = 300  # 5 minutos
