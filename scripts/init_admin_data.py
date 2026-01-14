"""
Script para inicializar datos del Admin
- Crea usuario admin inicial: juan/qwe123
- Seedea configuraciones básicas del sistema
"""
import asyncio
import os
import sys
from pathlib import Path

# Agregar el directorio raíz al path
root_dir = Path(__file__).parent.parent
sys.path.insert(0, str(root_dir))

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie, Document
from pydantic import Field, EmailStr
from datetime import datetime
from typing import Optional, Any
from passlib.context import CryptContext
from models.models_beanie import Configuracion, Usuario

# Configurar bcrypt localmente para evitar imports problemáticos
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)

def encriptar_clave(clave: str) -> str:
    """Encripta contraseña usando bcrypt"""
    if not clave:
        raise ValueError("La contraseña no puede estar vacía")
    clave_bytes = clave.encode('utf-8')
    if len(clave_bytes) > 72:
        clave = clave_bytes[:72].decode('utf-8', errors='ignore')
    return pwd_context.hash(clave)

# Definir modelos localmente para evitar imports circulares
class AdminUsuarios(Document):
    usuario: str
    nombre: str
    mail: EmailStr
    clave_hash: str
    activo: bool = Field(default=True)
    imagen_perfil: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "admin_usuarios"

class EcomerceConfiguracion(Document):
    clave: str
    valor: Any
    descripcion: Optional[str] = None
    tipo: str = "string"
    categoria: Optional[str] = "general"
    es_publica: bool = False
    modificable: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    updated_by: Optional[str] = None
    
    class Settings:
        name = "ecomerce_configuracion"


async def init_admin_user():
    """Crea el usuario admin inicial"""
    print("🔐 Creando usuario admin...")
    
    # Verificar si ya existe en AdminUsuarios
    existing_user = await AdminUsuarios.find_one(AdminUsuarios.mail == "juan@admin.com")
    if existing_user:
        print("⚠️  Usuario admin ya existe. Saltando creación.")
        return existing_user
    
    # Hashear contraseña
    password_hash = encriptar_clave("qwe123")
    
    # Crear usuario admin en AdminUsuarios
    admin_user = AdminUsuarios(
        usuario="juan",
        nombre="Juan Admin",
        mail="juan@admin.com",
        clave_hash=password_hash,
        activo=True
    )
    
    await admin_user.insert()
    print("✅ Usuario admin creado: juan@admin.com / qwe123")
    return admin_user


async def init_configurations():
    """Seedea configuraciones básicas del sistema"""
    print("\n⚙️  Creando configuraciones del sistema...")
    
    configuraciones_default = [
        {
            "clave": "nombre_tienda",
            "valor": "Mi Tienda Online",
            "descripcion": "Nombre de la tienda que aparece en el sitio",
            "tipo": "string",
            "categoria": "general",
            "es_publica": True,
            "modificable": True
        },
        {
            "clave": "email_contacto",
            "valor": "contacto@mitienda.com",
            "descripcion": "Email de contacto de la tienda",
            "tipo": "string",
            "categoria": "contacto",
            "es_publica": True,
            "modificable": True
        },
        {
            "clave": "moneda",
            "valor": "ARS",
            "descripcion": "Moneda predeterminada (código ISO)",
            "tipo": "string",
            "categoria": "comercial",
            "es_publica": True,
            "modificable": True
        },
        {
            "clave": "iva_porcentaje",
            "valor": 21,
            "descripcion": "Porcentaje de IVA aplicado",
            "tipo": "int",
            "categoria": "comercial",
            "es_publica": False,
            "modificable": True
        },
        {
            "clave": "direccion_tienda",
            "valor": "Av. Principal 123, CABA, Argentina",
            "descripcion": "Dirección física de la tienda",
            "tipo": "string",
            "categoria": "contacto",
            "es_publica": True,
            "modificable": True
        },
        {
            "clave": "telefono_contacto",
            "valor": "+54 11 1234-5678",
            "descripcion": "Teléfono de contacto",
            "tipo": "string",
            "categoria": "contacto",
            "es_publica": True,
            "modificable": True
        },
        {
            "clave": "index_sections",
            "valor": """{
                "hero": {
                    "titulo": "Transformamos datos en decisiones inteligentes",
                    "subtitulo": "Consultoría IA, ecommerce inteligente, desarrollo web",
                    "contenido": "Ofrecemos soluciones tecnológicas avanzadas para potenciar tu negocio con inteligencia artificial y desarrollo web profesional.",
                    "imagen": "/static/img/logo.png",
                    "buttonText": "🚀 Descubre nuestros servicios",
                    "buttonLink": "#servicios",
                    "showButton": true
                },
                "servicios": {
                    "titulo": "Nuestros Servicios",
                    "subtitulo": "Ofrecemos soluciones tecnológicas avanzadas",
                    "contenido": "Transformamos tu negocio con las últimas tecnologías",
                    "imagen": null,
                    "buttonText": "Solicitar Presupuesto",
                    "buttonLink": "/presupuestos",
                    "showButton": true
                }
            }""",
            "descripcion": "Secciones dinámicas de la página principal",
            "tipo": "json",
            "categoria": "frontend",
            "es_publica": True,
            "modificable": True
        },
        {
            "clave": "envio_gratis_desde",
            "valor": 50000,
            "descripcion": "Monto mínimo para envío gratis",
            "tipo": "int",
            "categoria": "comercial",
            "es_publica": True,
            "modificable": True
        },
        {
            "clave": "mostrar_productos_sin_stock",
            "valor": True,
            "descripcion": "Mostrar productos sin stock en el catálogo",
            "tipo": "bool",
            "categoria": "productos",
            "es_publica": False,
            "modificable": True
        }
    ]
    
    created_count = 0
    for config_data in configuraciones_default:
        # Verificar si ya existe
        existing = await Configuracion.find_one(
            Configuracion.key == config_data["clave"]
        )
        
        if existing:
            print(f"⚠️  Configuración '{config_data['clave']}' ya existe. Saltando.")
            continue
        
        # Crear configuración
        config = Configuracion(
            key=config_data["clave"],
            value=str(config_data["valor"])
        )
        await config.insert()
        created_count += 1
        print(f"✅ Configuración creada: {config.key} = {config.value}")
    
    print(f"\n✅ {created_count} configuraciones creadas.")


async def init_contract_configurations():
    """Inicializa configuraciones del contrato"""
    print("\n📄 Inicializando configuraciones del contrato...")
    
    contract_configs = [
        ('proveedor_razon_social', 'SysNeg S.A.'),
        ('proveedor_cuit', '30-XXXXXXXX-9'),
        ('proveedor_domicilio', 'Ciudad Autónoma de Buenos Aires, Argentina'),
        ('moneda', 'ARS'),
        ('periodicidad', 'mensual'),
        ('dias_vencimiento', '30'),
        ('dias_preaviso', '30'),
        ('dias_retencion', '30')
    ]
    
    created_count = 0
    for key, value in contract_configs:
        existing = await Configuracion.find_one(Configuracion.key == key)
        if not existing:
            config = Configuracion(key=key, value=value)
            await config.insert()
            created_count += 1
            print(f"   ✅ Creada: {key} = {value}")
        else:
            print(f"   ⏭️  Ya existe: {key}")
    
    print(f"\n✅ {created_count} configuraciones del contrato inicializadas.")


async def main():
    """Función principal"""
    print("=" * 60)
    print("🚀 INICIALIZADOR DE DATOS DEL ADMIN")
    print("=" * 60)
    
    # Obtener variables de entorno
    from dotenv import load_dotenv
    load_dotenv()
    
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "db_sysne")
    
    print(f"\n📡 Conectando a MongoDB...")
    print(f"   URL: {MONGO_URL}")
    print(f"   Base de datos: {DB_NAME}")
    
    # Conectar a MongoDB
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    
    # Inicializar Beanie
    await init_beanie(
        database=database,
        document_models=[Usuario, Configuracion, AdminUsuarios]
    )
    
    print("✅ Conexión establecida\n")
    
    # Crear usuario admin
    await init_admin_user()
    
    # Crear configuraciones
    await init_configurations()
    
    # Crear configuraciones del contrato
    await init_contract_configurations()
    
    print("\n" + "=" * 60)
    print("✅ INICIALIZACIÓN COMPLETADA")
    print("=" * 60)
    print("\n📋 Credenciales del admin:")
    print("   Email: juan@admin.com")
    print("   Contraseña: qwe123")
    print("\n🌐 Acceso al panel: http://localhost:8000/admin/login")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
