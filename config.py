# config.py
# =============================
# Configuración central de la aplicación
# =============================

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Frontend URL
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8000")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
BASE_URL = FRONTEND_URL  # Alias for compatibility

# Google OAuth
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")

# CORS Origins
ORIGINS = [
    "http://localhost:3000",
    "http://localhost:8000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000",
    FRONTEND_URL,
]

# Static directory
STATIC_DIR = "static"

# Database URLs
# MongoDB/Cosmos DB
# Para Azure Cosmos DB, obtén la cadena de conexión desde Azure Portal > Connection String
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
MONGODB_URL = os.getenv("MONGODB_URL", MONGO_URL)  # Para compatibilidad
DB_NAME = os.getenv("DB_NAME", "db_ecomerce")

# JWT Secret
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
SECRET = SECRET_KEY  # Alias for compatibility
ALGORITHM = "HS256"

# Email configuration
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

# Azure Search
AZURE_SEARCH_ENDPOINT = os.getenv("AZURE_SEARCH_ENDPOINT")
AZURE_SEARCH_KEY = os.getenv("AZURE_SEARCH_KEY")
AZURE_SEARCH_INDEX_NAME = os.getenv("AZURE_SEARCH_INDEX_NAME", "ecommerce-index")
