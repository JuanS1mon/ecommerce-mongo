"""
Sistema de Validación Híbrida de Contraseñas
Permite tanto PINs (4-6 dígitos) como contraseñas seguras para diferentes niveles de seguridad
"""
import os
import re
from typing import Dict, Any

def is_pin(password: str) -> bool:
    """Detecta si la entrada es un PIN (solo números)"""
    return password.isdigit()

def validate_pin(pin: str) -> Dict[str, Any]:
    """Valida PIN de 4-6 dígitos con verificaciones de seguridad"""
      # Configuración desde variables de entorno (con limpieza de comentarios)
    pin_enabled = os.getenv("ENABLE_PIN_AUTH", "true").split('#')[0].strip().lower() == "true"
    min_length = int(os.getenv("PIN_MIN_LENGTH", "4").split('#')[0].strip())
    max_length = int(os.getenv("PIN_MAX_LENGTH", "6").split('#')[0].strip())
    allow_sequential = os.getenv("PIN_ALLOW_SEQUENTIAL", "false").split('#')[0].strip().lower() == "true"
    allow_repeating = os.getenv("PIN_ALLOW_REPEATING", "false").split('#')[0].strip().lower() == "true"
    
    if not pin_enabled:
        return {
            "valid": False,
            "message": "La autenticación con PIN está deshabilitada",
            "type": "pin"
        }
    
    # Verificar que sea solo números
    if not pin.isdigit():
        return {
            "valid": False,
            "message": "El PIN debe contener solo números",
            "type": "pin"
        }
    
    # Verificar longitud
    if len(pin) < min_length:
        return {
            "valid": False,
            "message": f"El PIN debe tener al menos {min_length} dígitos",
            "type": "pin"
        }
    
    if len(pin) > max_length:
        return {
            "valid": False,
            "message": f"El PIN no puede tener más de {max_length} dígitos",
            "type": "pin"
        }
    
    # Verificar patrones secuenciales si no están permitidos
    if not allow_sequential:
        # Secuencias ascendentes y descendentes
        for i in range(len(pin) - 2):
            if len(set(pin[i:i+3])) == 3:  # Tres dígitos diferentes
                nums = [int(pin[i+j]) for j in range(3)]
                if (nums[1] == nums[0] + 1 and nums[2] == nums[1] + 1) or \
                   (nums[1] == nums[0] - 1 and nums[2] == nums[1] - 1):
                    return {
                        "valid": False,
                        "message": "El PIN no puede contener secuencias como 123, 321, etc.",
                        "type": "pin"
                    }
    
    # Verificar repetición si no está permitida
    if not allow_repeating:
        if len(set(pin)) == 1:  # Todos los dígitos iguales
            return {
                "valid": False,
                "message": "El PIN no puede tener todos los dígitos iguales",
                "type": "pin"
            }
    
    return {
        "valid": True,
        "message": f"PIN válido de {len(pin)} dígitos",
        "type": "pin"
    }

def validate_secure_password(password: str) -> Dict[str, Any]:
    """Valida contraseña segura con requisitos robustos"""
      # Configuración desde variables de entorno (con limpieza de comentarios)
    min_length = int(os.getenv("SECURE_PASSWORD_MIN_LENGTH", "8").split('#')[0].strip())
    require_uppercase = os.getenv("SECURE_PASSWORD_REQUIRE_UPPERCASE", "true").split('#')[0].strip().lower() == "true"
    require_lowercase = os.getenv("SECURE_PASSWORD_REQUIRE_LOWERCASE", "true").split('#')[0].strip().lower() == "true"
    require_numbers = os.getenv("SECURE_PASSWORD_REQUIRE_NUMBERS", "true").split('#')[0].strip().lower() == "true"
    require_special = os.getenv("SECURE_PASSWORD_REQUIRE_SPECIAL", "true").split('#')[0].strip().lower() == "true"
    
    # Verificar longitud mínima
    if len(password) < min_length:
        return {
            "valid": False,
            "message": f"La contraseña debe tener al menos {min_length} caracteres",
            "type": "secure_password"
        }
    
    # Verificar longitud máxima
    if len(password) > 128:
        return {
            "valid": False,
            "message": "La contraseña no puede exceder 128 caracteres",
            "type": "secure_password"
        }
    
    # Verificar mayúsculas
    if require_uppercase and not re.search(r"[A-Z]", password):
        return {
            "valid": False,
            "message": "La contraseña debe contener al menos una letra mayúscula",
            "type": "secure_password"
        }
    
    # Verificar minúsculas
    if require_lowercase and not re.search(r"[a-z]", password):
        return {
            "valid": False,
            "message": "La contraseña debe contener al menos una letra minúscula",
            "type": "secure_password"
        }
    
    # Verificar números
    if require_numbers and not re.search(r"\d", password):
        return {
            "valid": False,
            "message": "La contraseña debe contener al menos un número",
            "type": "secure_password"
        }
    
    # Verificar caracteres especiales (INCLUYE GUIÓN BAJO)
    if require_special and not re.search(r"[!@#$%^&*(),.?\":{}|<>_\-+=\[\]\\\/`~]", password):
        return {
            "valid": False,
            "message": "La contraseña debe contener al menos un carácter especial (!@#$%^&*()_-+=[]{}|\\:\"';?/>.<,`~)",
            "type": "secure_password"
        }
      # Verificar patrones débiles (menos restrictivo para contraseñas complejas)
    weak_patterns = [
        (r"(.)\1{3,}", "La contraseña no puede tener más de 3 caracteres iguales consecutivos"),
        (r"(qwerty|asdfgh|zxcvbn|password|123456|admin)", "La contraseña no puede contener patrones comunes")
    ]
    
    for pattern, message in weak_patterns:
        if re.search(pattern, password.lower()):
            return {
                "valid": False,
                "message": message,
                "type": "secure_password"
            }
    
    return {
        "valid": True,
        "message": f"Contraseña segura válida de {len(password)} caracteres",
        "type": "secure_password"
    }

def validate_password(password: str) -> Dict[str, Any]:
    """
    Función principal que detecta automáticamente si es PIN o contraseña segura
    y aplica la validación correspondiente
    """
    if not password:
        return {
            "valid": False,
            "message": "La contraseña es requerida",
            "type": "unknown"
        }
    
    # Detectar automáticamente el tipo
    if is_pin(password):
        return validate_pin(password)
    else:
        return validate_secure_password(password)
