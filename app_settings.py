# app_settings.py
# =============================
# Configuración centralizada de CORS y documentación de la API
# Este archivo permite modificar fácilmente los orígenes permitidos, credenciales, métodos y headers para CORS,
# así como las URLs de la documentación interactiva de FastAPI (Swagger y ReDoc).
# =============================

from config import ORIGINS, ENVIRONMENT

# CORS_CONFIG:
# Diccionario con la configuración de CORS (Cross-Origin Resource Sharing).
# Permite definir desde qué orígenes externos se puede acceder a la API, qué métodos y headers están permitidos,
# y si se permiten credenciales (cookies, headers de autenticación, etc.).
# - allow_origins: Lista de orígenes permitidos. En producción usa los definidos en ORIGINS, en desarrollo permite todos.
# - allow_credentials: Si se permiten credenciales (True recomendado para APIs autenticadas).
# - allow_methods: Métodos HTTP permitidos ("*" para todos).
# - allow_headers: Headers permitidos ("*" para todos).
CORS_CONFIG = {
    "allow_origins": ORIGINS if ENVIRONMENT == "production" else ["*"],
    "allow_credentials": True,
    "allow_methods": ["*"],
    "allow_headers": ["*"],
}

# DOCS_URL y REDOC_URL:
# URLs para la documentación interactiva de la API.
# - DOCS_URL: Habilita/deshabilita la documentación Swagger (por defecto en /docs). Solo visible en desarrollo.
# - REDOC_URL: Habilita/deshabilita la documentación ReDoc (por defecto en /redoc). Solo visible en desarrollo.
# En producción, ambas quedan deshabilitadas por seguridad.
DOCS_URL = "/docs" if ENVIRONMENT == "development" else None
REDOC_URL = "/redoc" if ENVIRONMENT == "development" else None
