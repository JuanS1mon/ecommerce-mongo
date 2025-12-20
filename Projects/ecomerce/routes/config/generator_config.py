"""
Configuración del Generador de Aplicaciones
==========================================

Este archivo contiene las configuraciones y validaciones
para el sistema generador de código automático.
"""

import re
from typing import List, Dict, Tuple

# Configuraciones del generador
GENERATOR_CONFIG = {
    "max_fields": 20,
    "max_module_name_length": 50,
    "max_field_name_length": 50,
    "allowed_field_types": [
        "int", "integer", "string", "str", "text", "varchar",
        "boolean", "bool", "datetime", "date", "time",
        "float", "decimal", "json", "blob", "binary"
    ],
    "reserved_module_names": [
        "admin", "auth", "config", "main", "app", "api", 
        "static", "templates", "middleware", "security",
        "db", "models", "schemas", "crud", "routers"
    ],
    "backup_retention_days": 30,
    "service_directory": "Services",
    "backup_directory": "Services/backups"
}

# Patrones de validación
VALIDATION_PATTERNS = {
    "module_name": re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$'),
    "field_name": re.compile(r'^[a-zA-Z][a-zA-Z0-9_]*$'),
    "safe_filename": re.compile(r'^[a-zA-Z0-9_-]+$')
}

def validate_module_name(module_name: str) -> Tuple[bool, str]:
    """
    Valida el nombre de un módulo según las reglas establecidas.
    
    Returns:
        Tuple[bool, str]: (es_válido, mensaje)
    """
    if not module_name:
        return False, "El nombre del módulo es requerido"
    
    if len(module_name) > GENERATOR_CONFIG["max_module_name_length"]:
        return False, f"El nombre del módulo no puede exceder {GENERATOR_CONFIG['max_module_name_length']} caracteres"
    
    if not VALIDATION_PATTERNS["module_name"].match(module_name):
        return False, "El nombre del módulo debe comenzar con una letra y contener solo letras, números y guiones bajos"
    
    if module_name.lower() in GENERATOR_CONFIG["reserved_module_names"]:
        return False, f"'{module_name}' es un nombre reservado"
    
    return True, "Válido"

def validate_field_name(field_name: str) -> Tuple[bool, str]:
    """
    Valida el nombre de un campo según las reglas establecidas.
    
    Returns:
        Tuple[bool, str]: (es_válido, mensaje)
    """
    if not field_name:
        return False, "El nombre del campo es requerido"
    
    if len(field_name) > GENERATOR_CONFIG["max_field_name_length"]:
        return False, f"El nombre del campo no puede exceder {GENERATOR_CONFIG['max_field_name_length']} caracteres"
    
    if not VALIDATION_PATTERNS["field_name"].match(field_name):
        return False, "El nombre del campo debe comenzar con una letra y contener solo letras, números y guiones bajos"
    
    return True, "Válido"

def validate_field_type(field_type: str) -> Tuple[bool, str]:
    """
    Valida el tipo de un campo según los tipos permitidos.
    
    Returns:
        Tuple[bool, str]: (es_válido, mensaje)
    """
    if not field_type:
        return False, "El tipo del campo es requerido"
    
    if field_type.lower() not in GENERATOR_CONFIG["allowed_field_types"]:
        return False, f"Tipo de campo no permitido. Tipos válidos: {', '.join(GENERATOR_CONFIG['allowed_field_types'])}"
    
    return True, "Válido"

def validate_fields_data(field_names: List[str], field_types: List[str]) -> Tuple[bool, str]:
    """
    Valida una lista completa de campos y tipos.
    
    Returns:
        Tuple[bool, str]: (es_válido, mensaje)
    """
    if len(field_names) != len(field_types):
        return False, "El número de nombres de campos debe coincidir con el número de tipos"
    
    if len(field_names) == 0:
        return False, "Debe especificar al menos un campo"
    
    if len(field_names) > GENERATOR_CONFIG["max_fields"]:
        return False, f"No se pueden especificar más de {GENERATOR_CONFIG['max_fields']} campos"
    
    # Validar duplicados en nombres de campos
    if len(field_names) != len(set(field_names)):
        return False, "Los nombres de campos no pueden estar duplicados"
    
    # Validar cada campo individualmente
    for i, (field_name, field_type) in enumerate(zip(field_names, field_types)):
        valid_name, name_msg = validate_field_name(field_name)
        if not valid_name:
            return False, f"Campo {i+1}: {name_msg}"
        
        valid_type, type_msg = validate_field_type(field_type)
        if not valid_type:
            return False, f"Campo {i+1}: {type_msg}"
    
    return True, "Todos los campos son válidos"

def get_type_mapping() -> Dict[str, str]:
    """
    Retorna el mapeo de tipos de datos SQL a tipos de Python.
    """
    return {
        'int': 'int',
        'integer': 'int',
        'string': 'str',
        'str': 'str',
        'text': 'str',
        'varchar': 'str',
        'boolean': 'bool',
        'bool': 'bool',
        'datetime': 'datetime',
        'date': 'date',
        'time': 'time',
        'float': 'float',
        'decimal': 'float',
        'json': 'dict',
        'blob': 'bytes',
        'binary': 'bytes'
    }

def sanitize_path(path: str) -> str:
    """
    Sanitiza una ruta de archivo para prevenir ataques de directory traversal.
    """
    import os
    # Normalizar la ruta y eliminar componentes peligrosos
    normalized = os.path.normpath(path)
    
    # Eliminar referencias a directorio padre
    while ".." in normalized:
        normalized = normalized.replace("..", "")
    
    # Eliminar barras iniciales
    normalized = normalized.lstrip("/\\")
    
    return normalized
