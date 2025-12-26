# logging_config_new.py
# =============================
# Configuración de logging para la aplicación
# =============================

import logging
import sys
from logging.handlers import RotatingFileHandler

def setup_logging():
    """
    Configura el sistema de logging de la aplicación
    """
    # Crear logger principal
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # Formato del log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Handler para consola
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Remover handler para archivo (no compatible con Vercel/serverless)
    # file_handler = RotatingFileHandler(
    #     'app.log',
    #     maxBytes=10*1024*1024,  # 10MB
    #     backupCount=5
    # )
    # file_handler.setLevel(logging.DEBUG)
    # file_handler.setFormatter(formatter)

    # Agregar handlers al logger
    logger.addHandler(console_handler)
    # logger.addHandler(file_handler)

    # Configurar loggers específicos
    logging.getLogger('uvicorn').setLevel(logging.INFO)
    logging.getLogger('fastapi').setLevel(logging.INFO)
    logging.getLogger('beanie').setLevel(logging.INFO)

    print("[OK] Logging configurado correctamente")

# Configuración de logging para exportar
LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            "use_colors": True
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "level": "INFO"
        },
        # "file": {  # Removido para compatibilidad con Vercel/serverless
        #     "class": "logging.handlers.RotatingFileHandler",
        #     "filename": "app.log",
        #     "maxBytes": 10485760,  # 10MB
        #     "backupCount": 5,
        #     "formatter": "default",
        #     "level": "DEBUG"
        # },
        "access": {
            "class": "logging.StreamHandler",
            "formatter": "access",
            "level": "INFO"
        }
    },
    "root": {
        "handlers": ["console"],  # Removido "file"
        "level": "DEBUG"
    },
    "loggers": {
        "uvicorn": {
            "level": "INFO",
            "handlers": ["console"],  # Removido "file"
            "propagate": False
        },
        "uvicorn.access": {
            "level": "INFO",
            "handlers": ["access"],
            "propagate": False
        },
        "fastapi": {
            "level": "INFO",
            "handlers": ["console"],  # Removido "file"
            "propagate": False
        }
    }
}
