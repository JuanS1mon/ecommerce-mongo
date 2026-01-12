# =============================================================================
# database.py - Configuración y utilidades de base de datos para SQL_APP
# =============================================================================
# Este módulo centraliza la configuración y utilidades de acceso a la base de datos
# para la aplicación FastAPI. Incluye:
# - Carga de variables de entorno y configuración de SQLAlchemy.
# - Creación y verificación de la base de datos y tablas.
# - Compatibilidad con SQL Server (prioridad), PostgreSQL y SQLite.
# - Funciones utilitarias para migraciones y manejo de errores.
#
# Notas profesionales:
# - No contiene lógica de negocio, solo inicialización y utilidades de infraestructura.
# - Los mensajes de ayuda y advertencia son claros para facilitar el diagnóstico.
# - Se recomienda mantener este archivo libre de prints de debug en producción.
# =============================================================================

import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# =============================
# CONFIGURACIÓN DE CONEXIÓN Y BEANIE (MongoDB)
# =============================
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from passlib.context import CryptContext
from datetime import datetime

# Configuración de encriptación para admin
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Variables de entorno para MongoDB
# Para Azure Cosmos DB, usa la cadena de conexión del Portal
# Formato: mongodb+srv://<username>:<password>@<cluster>.mongo.cosmos.azure.com:10255/?ssl=true&retryWrites=false&replicaSet=globaldb&maxIdleTimeMS=120000&appName=@<cluster>@
MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
DB_NAME = os.getenv("MONGO_DB_NAME", "db_sysne")

# Configuración de MongoDB con Beanie - Lazy initialization
mongo_client = None
mongo_database = None

def get_database():
    global mongo_client, mongo_database
    if mongo_client is None:
        MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
        DB_NAME = os.getenv("DB_NAME", "db_sysne")
        mongo_client = AsyncIOMotorClient(MONGO_URL)
        mongo_database = mongo_client[DB_NAME]
        print(f"[DEBUG] Created database object: {type(mongo_database)}")
    return mongo_database

# Función para crear usuario admin por defecto si la base está vacía
async def create_default_admin():
    admin_collection = database["admin_usuarios"]

    # Verificar si ya existe el admin por defecto
    existing_admin = await admin_collection.find_one({"usuario": "admin"})
    if existing_admin:
        print("[INFO] Usuario admin por defecto ya existe")
        return

    # Crear el usuario admin por defecto
    hashed_password = pwd_context.hash("admin123")
    admin_user = {
        "usuario": "admin",
        "nombre": "Administrator",
        "mail": "admin@example.com",
        "clave_hash": hashed_password,
        "activo": True,
        "es_super_admin": True,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow()
    }

    result = await admin_collection.insert_one(admin_user)
    print(f"[SUCCESS] Usuario admin creado: admin/admin123 (ID: {result.inserted_id})")

# Función para inicializar Beanie con los modelos
async def init_beanie_db():
    db = get_database()
    # Importar todos los modelos aquí
    from models.models_beanie import Servicio, Presupuesto, Contrato, Usuario, Configuracion, Producto, AdminUsuarios, Proyecto, UsuarioProyecto
    
    await init_beanie(database=db, document_models=[
        Usuario,
        AdminUsuarios,
        Servicio,
        Presupuesto,
        Contrato,
        Configuracion,
        Producto,
        Proyecto,
        UsuarioProyecto
    ])  # Lista de modelos Beanie
    return True

initialize_beanie_db = init_beanie_db
# Dependencia de base de datos (para FastAPI) - REMOVIDA
# def get_database():
#     return database

# =============================
# CONFIGURACIÓN DE SQLALCHEMY (COMENTADO - ELIMINADO)
# =============================

# # Configuración de SQLAlchemy
# SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "sqlite:///./sql_app.db")

# engine = create_engine(SQLALCHEMY_DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base = declarative_base()

# # Dependencia para obtener la sesión de DB
#     db = SessionLocal()
#     try:
#         yield db
#     finally:
#         db.close()

# # Variables para compatibilidad
# DB_TYPE = "sqlite"  # Default
# USE_PYMSSQL = False
# master_engine = engine  # For simplicity

# # Crear la base de datos si no existe (solo en entorno local)
# def create_database():
#     # Para SQLite, no necesitamos crear la base de datos manualmente
#     if DB_TYPE == "sqlite":
#         return
#     try:
#         with master_engine.connect() as connection:
#             if DB_TYPE == "sqlserver":
#                 # Crear la base de datos si no existe
                
#                 # Solo ejecutar comandos ALTER si usamos pyodbc (pymssql no los soporta)
#                 if not USE_PYMSSQL:
#                     try:
#                         print("✅ Configuración de base de datos aplicada (pyodbc)")
#                     except Exception as alter_error:
#                         print(f"⚠️  No se pudieron aplicar configuraciones ALTER: {alter_error}")
#                 else:
#                     print("ℹ️  Saltando configuraciones ALTER (no soportadas por pymssql)")
                    
#             elif DB_TYPE == "postgresql":
#                 if not result.scalar():
#     except (OperationalError, InterfaceError, ProgrammingError) as e:
#         msg = str(e)
#         if "Error de inicio de sesión" in msg or "login failed" in msg.lower():
#             print("⚠️  No se pudo conectar a la base de datos. Verifica usuario y contraseña.")
#         elif "ya existe" in msg.lower() or "already exists" in msg.lower():
#             pass
#         else:
#             print(f"⚠️  Error al crear la base de datos: {e}")

# # Función para cargar el modelo Roles primero
# def ensure_roles_model():
#     try:
#         # Intentar importar el modelo Roles existente
#         try:
#             importlib.import_module("db.models.roles")
#         except ImportError:
#             # Si no existe, crearlo
#             import os
#             models_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'db', 'models')
#             os.makedirs(models_dir, exist_ok=True)
            
#             roles_file_path = os.path.join(models_dir, 'roles.py')
            
#             if not os.path.exists(roles_file_path):
#                 with open(roles_file_path, 'w') as f:
# from db.database import Base

# class Roles(Base):
#     __tablename__ = "Roles"
#     __table_args__ = {'extend_existing': True}
    
#     id = Column(Integer, primary_key=True, index=True)
#     nombre = Column(String(50), unique=True)
#     descripcion = Column(String(255), nullable=True)
# """)
#                 importlib.import_module("db.models.roles")
#         # Crear solo la tabla Roles primero
#         temp_metadata = MetaData()
#         for table_name, table in Base.metadata.tables.items():
#             if table_name == "Roles":
#                 table.tometadata(temp_metadata)
#                 try:
#                     temp_metadata.create_all(bind=engine)
#                 except (OperationalError, InterfaceError, ProgrammingError) as e:
#                     msg = str(e)
#                     if "Error de inicio de sesión" in msg or "login failed" in msg.lower():
#                         print("⚠️  No se pudo conectar a la base de datos. Verifica usuario y contraseña.")
#                     elif "ya existe" in msg.lower() or "already exists" in msg.lower():
#                         pass
#                     else:
#                         print(f"⚠️  Error al crear tabla Roles: {e}")
#                 break
                
#     except Exception as e:
#         print(f"Error al asegurar el modelo Roles: {e}")

# # Crear las tablas en la base de datos
# def create_tables():
#     try:
#         # Primero asegurar que exista la tabla Roles
#         ensure_roles_model()
        
#         # Crear todas las demás tablas usando el método estándar de SQLAlchemy
#         try:
#             Base.metadata.create_all(bind=engine)
#         except (OperationalError, InterfaceError, ProgrammingError) as e:
#             msg = str(e)
#             if "Error de inicio de sesión" in msg or "login failed" in msg.lower():
#                 print("⚠️  No se pudo conectar a la base de datos. Verifica usuario y contraseña.")
#             elif "ya existe" in msg.lower() or "already exists" in msg.lower():
#                 pass
#             else:
#                 print(f"⚠️  Error al crear tablas: {e}")
#     except NoReferencedTableError as e:
#         print(f"Error de tabla referenciada: {e}")
#         # Si falla porque falta una tabla referenciada, intenta manejar caso por caso
#         if "Roles" in str(e):
#             ensure_roles_model()
#             try:
#                 Base.metadata.create_all(bind=engine)
#             except Exception as e2:
#                 print(f"⚠️  Error al crear tablas tras asegurar Roles: {e2}")
#     except Exception as e:
#         print(f"⚠️  Error inesperado al crear tablas: {e}")

# # Eliminar cualquier lógica residual de PostgreSQL
# if 'psycopg2' in sys.modules:
#     del sys.modules['psycopg2']
#     print("Referencia a psycopg2 eliminada.")

# # Asegurar que SQLALCHEMY_DATABASE_URL esté configurado para SQL Server
# # TODO: Remove this check when fully migrated to MongoDB
# # if not (SQLALCHEMY_DATABASE_URL.startswith("mssql+pyodbc://") or SQLALCHEMY_DATABASE_URL.startswith("mssql+pymssql://")):
# #     raise ValueError("SQLALCHEMY_DATABASE_URL no está configurado correctamente para SQL Server.")

# # =============================
# # AUTO-ACTUALIZAR BASE DE DATOS CON ALEMBIC EN STARTUP
# # =============================
# def run_alembic_upgrade():
#     import subprocess
#     import logging
#     try:
#         result = subprocess.run([
#             sys.executable, '-m', 'alembic', 'upgrade', 'head'
#         ], cwd=os.path.dirname(os.path.dirname(__file__)), capture_output=True, text=True)
#         if result.returncode == 0:
#             return True
#         else:
#             # Solo mostrar error si es realmente crítico
#             if result.stderr.strip():
#                 print(f"[Alembic] Error al aplicar migraciones: {result.stderr}")
#             return not result.stderr.strip()
#     except Exception as e:
#         print(f"[Alembic] Excepción al ejecutar migraciones: {e}")
#         return False

# # REMOVIDO: Ejecutar migraciones automáticamente al importar este módulo
# # run_alembic_upgrade()

# # La base de datos se crea pero las tablas no se crean automáticamente
# # para evitar problemas de orden de creación
# # create_database()  # Se omitirá en Heroku - COMMENTED OUT FOR MONGODB MIGRATION
# # Las tablas se crearán explícitamente desde main.py

# =============================
# FUNCIONES DE COMPATIBILIDAD
# =============================

# Compat: exportar `Base` para modelos legacy de SQLAlchemy
try:
    from sqlalchemy.ext.declarative import declarative_base
    Base = declarative_base()
except Exception:
    # Si SQLAlchemy no está disponible, exportar un objeto dummy para evitar ImportError
    class _DummyBase:
        pass
    Base = _DummyBase()


def get_db():
    """
    Generador que yield una sesión dummy para compatibilidad
    con código legacy que espera SQLAlchemy Session
    TODO: Migrar completamente a Beanie/MongoDB
    """
    yield None
