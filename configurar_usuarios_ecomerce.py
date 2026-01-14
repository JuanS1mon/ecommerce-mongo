"""
Script de Configuración: Usuarios del Proyecto Ecomerce
Configura los usuarios admin con sus proyectos y fechas de vencimiento
"""
import asyncio
import sys
import os
from datetime import datetime

# Agregar el directorio raíz al path
sys.path.insert(0, os.path.dirname(__file__))

from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from dotenv import load_dotenv
import bcrypt

# Cargar variables de entorno
load_dotenv()

# Importar modelos
from Projects.Admin.models.admin_usuarios_beanie import AdminUsuarios
from Projects.Admin.models.proyectos_beanie import Proyecto, UsuarioProyecto


async def configurar_usuarios_ecomerce():
    """Configura los usuarios del proyecto Ecomerce"""
    
    print("\n" + "="*70)
    print("⚙️  CONFIGURACIÓN DE USUARIOS - PROYECTO ECOMERCE")
    print("="*70 + "\n")
    
    # Conectar a MongoDB
    MONGO_URL = os.getenv("MONGO_URL", "mongodb://localhost:27017")
    DB_NAME = os.getenv("DB_NAME", "db_ecomerce")
    
    print(f"📊 Conectando a MongoDB...")
    print(f"   URL: {MONGO_URL}")
    print(f"   Database: {DB_NAME}\n")
    
    client = AsyncIOMotorClient(MONGO_URL)
    database = client[DB_NAME]
    
    # Inicializar Beanie
    print("⚙️  Inicializando Beanie...\n")
    await init_beanie(
        database=database,
        document_models=[AdminUsuarios, Proyecto, UsuarioProyecto]
    )
    
    # Proyecto Ecomerce
    proyecto_nombre = "Ecomerce"
    
    # Lista de usuarios a configurar
    usuarios_config = [
        {
            "email": "admin@sysneg.com",
            "username": "admin",
            "nombre": "Admin Sysneg",
            "password": "admin123",  # AJUSTA SI ES NECESARIO
            "proyecto": proyecto_nombre,
            "fecha_vencimiento": datetime(2026, 7, 3, 23, 59, 59),  # 3/7/2026
            "activo": True,
            "descripcion": "Usuario NO vencido (vence 3/7/2026)"
        },
        {
            "email": "fjuansimon@gmail.com",
            "username": "juan",
            "nombre": "Juan Ferreyra",
            "password": "juan123",  # AJUSTA LA CONTRASEÑA REAL
            "proyecto": proyecto_nombre,
            "fecha_vencimiento": datetime(2026, 1, 1, 23, 59, 59),  # 1/1/2026 (vencido)
            "activo": False,  # Inactivo según tu tabla
            "descripcion": "Usuario VENCIDO (venció 1/1/2026)"
        }
    ]
    
    print(f"👥 Configurando {len(usuarios_config)} usuarios...\n")
    
    for config in usuarios_config:
        print(f"{'='*70}")
        print(f"👤 Usuario: {config['email']}")
        print(f"{'='*70}")
        
        # Buscar o crear usuario
        usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == config['email'])
        
        if usuario:
            print(f"   ✅ Usuario encontrado en BD (ID: {usuario.id})")
            print(f"   📝 Actualizando información...")
            
            # Actualizar campos
            usuario.usuario = config['username']
            usuario.nombre = config['nombre']
            usuario.activo = config['activo']
            usuario.proyecto_nombre = config['proyecto']
            usuario.fecha_vencimiento = config['fecha_vencimiento']
            usuario.updated_at = datetime.utcnow()
            
            # Actualizar contraseña solo si es necesario (opcional)
            # usuario.clave_hash = bcrypt.hashpw(config['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            await usuario.save()
            print(f"   ✅ Usuario actualizado")
            
        else:
            print(f"   ❌ Usuario no encontrado, creando nuevo...")
            
            # Crear usuario
            password_hash = bcrypt.hashpw(config['password'].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            
            usuario = AdminUsuarios(
                usuario=config['username'],
                nombre=config['nombre'],
                mail=config['email'],
                clave_hash=password_hash,
                activo=config['activo'],
                proyecto_nombre=config['proyecto'],
                fecha_vencimiento=config['fecha_vencimiento'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await usuario.insert()
            print(f"   ✅ Usuario creado (ID: {usuario.id})")
        
        # Mostrar información
        print(f"\n   📋 INFORMACIÓN DEL USUARIO:")
        print(f"      Email: {usuario.mail}")
        print(f"      Username: {usuario.usuario}")
        print(f"      Nombre: {usuario.nombre}")
        print(f"      Estado: {'✅ Activo' if usuario.activo else '❌ Inactivo'}")
        print(f"      Proyecto: {usuario.proyecto_nombre}")
        print(f"      Vencimiento: {usuario.fecha_vencimiento.strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Calcular días restantes
        ahora = datetime.utcnow()
        dias_restantes = (usuario.fecha_vencimiento - ahora).days
        
        if dias_restantes > 0:
            print(f"      Estado fecha: ✅ VÁLIDA (quedan {dias_restantes} días)")
        else:
            print(f"      Estado fecha: ❌ VENCIDA (venció hace {abs(dias_restantes)} días)")
        
        print(f"      Descripción: {config['descripcion']}")
        print()
    
    # Verificar proyecto en API
    print(f"{'='*70}")
    print(f"📁 VERIFICACIÓN DEL PROYECTO EN API")
    print(f"{'='*70}\n")
    
    proyecto = await Proyecto.find_one(Proyecto.nombre == proyecto_nombre)
    
    if proyecto:
        print(f"   ✅ Proyecto '{proyecto_nombre}' encontrado en BD")
        print(f"      ID: {proyecto.id}")
        print(f"      Activo: {'✅ Sí' if proyecto.activo else '❌ No'}")
        print(f"      Descripción: {proyecto.descripcion}")
    else:
        print(f"   ❌ Proyecto '{proyecto_nombre}' NO encontrado")
        print(f"   💡 Creando proyecto...")
        
        proyecto = Proyecto(
            nombre=proyecto_nombre,
            descripcion="Proyecto de E-commerce",
            activo=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        await proyecto.insert()
        print(f"   ✅ Proyecto creado (ID: {proyecto.id})")
    
    # Verificar vinculaciones usuario-proyecto
    print(f"\n{'='*70}")
    print(f"🔗 VERIFICACIÓN DE VINCULACIONES")
    print(f"{'='*70}\n")
    
    for config in usuarios_config:
        usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == config['email'])
        
        vinculacion = await UsuarioProyecto.find_one(
            UsuarioProyecto.usuario_id == usuario.id,
            UsuarioProyecto.proyecto_id == proyecto.id
        )
        
        if vinculacion:
            print(f"   ✅ Vinculación existe: {usuario.usuario} → {proyecto_nombre}")
            
            # Actualizar si es necesario
            if vinculacion.fecha_vencimiento != config['fecha_vencimiento']:
                vinculacion.fecha_vencimiento = config['fecha_vencimiento']
                vinculacion.activo = config['activo']
                vinculacion.updated_at = datetime.utcnow()
                await vinculacion.save()
                print(f"      📝 Vinculación actualizada")
        else:
            print(f"   ❌ Vinculación NO existe, creando...")
            
            vinculacion = UsuarioProyecto(
                usuario_id=usuario.id,
                proyecto_id=proyecto.id,
                fecha_asignacion=datetime.utcnow(),
                fecha_vencimiento=config['fecha_vencimiento'],
                activo=config['activo'],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            await vinculacion.insert()
            print(f"   ✅ Vinculación creada: {usuario.usuario} → {proyecto_nombre}")
    
    # Resumen final
    print(f"\n{'='*70}")
    print(f"📊 RESUMEN DE CONFIGURACIÓN")
    print(f"{'='*70}\n")
    
    print(f"✅ Configuración completada exitosamente\n")
    print(f"📋 USUARIOS CONFIGURADOS:\n")
    
    for config in usuarios_config:
        usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == config['email'])
        dias = (config['fecha_vencimiento'] - datetime.utcnow()).days
        estado = "✅ VÁLIDA" if dias > 0 else "❌ VENCIDA"
        
        print(f"   👤 {config['email']}")
        print(f"      Password: {config['password']} (ajústala si es incorrecta)")
        print(f"      Proyecto: {config['proyecto']}")
        print(f"      Vencimiento: {config['fecha_vencimiento'].strftime('%d/%m/%Y')} - {estado}")
        print(f"      Estado usuario: {'✅ Activo' if config['activo'] else '❌ Inactivo'}")
        print()
    
    print(f"🚀 PRÓXIMOS PASOS:")
    print(f"   1. Ajusta las contraseñas en este script si son incorrectas")
    print(f"   2. Ejecuta: python test_usuarios_ecomerce.py")
    print(f"   3. O inicia el servidor y prueba el login manual")
    print(f"   4. Revisa los logs de validación interna\n")
    
    # Cerrar conexión
    client.close()


if __name__ == "__main__":
    print("\n⚠️  IMPORTANTE: Verifica las contraseñas antes de ejecutar")
    print("   Este script actualizará la información de los usuarios\n")
    
    try:
        asyncio.run(configurar_usuarios_ecomerce())
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
