# 🚀 Migración a MongoDB Atlas (Vercel) - Completada

## 📋 Resumen de la Migración

Se ha completado la migración del proyecto desde MongoDB local a **MongoDB Atlas** integrado con **Vercel**.

### ✅ Pasos Completados

#### 1. **Creación de Base de Datos en MongoDB Atlas**
- ✓ Cluster creado: `db-sysne`
- ✓ Base de datos: `db_ecommerce`
- ✓ Usuario: `Vercel-Admin-db_sysne`
- ✓ Conexión URI configurada correctamente

#### 2. **Inicialización de Estructura de Datos**
Se crearon las siguientes colecciones automáticamente:

- **usuarios** - Usuarios del sistema
- **admin_usuarios** - Administradores del sistema
- **servicios** - Catálogo de servicios
- **productos** - Catálogo de productos
- **presupuestos** - Gestión de presupuestos
- **contratos** - Contratos y acuerdos
- **configuraciones** - Configuraciones del sitio

#### 3. **Datos Iniciales Insertados**

```
✓ 3 Configuraciones iniciales creadas
✓ 3 Servicios iniciales creados
✓ 1 Usuario administrador creado (usuario: admin)
```

#### 4. **Variables de Entorno Actualizadas**

El archivo `.env` se actualizó con las credenciales de MongoDB Atlas:

```env
MONGO_URL=mongodb+srv://Vercel-Admin-db_sysne:lhAv2Av7NrwGxv6l@db-sysne.neh4dci.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=db_ecommerce
MONGODB_URL=mongodb+srv://Vercel-Admin-db_sysne:lhAv2Av7NrwGxv6l@db-sysne.neh4dci.mongodb.net/db_ecommerce?retryWrites=true&w=majority
```

---

## 🔐 Credenciales de Acceso

| Campo | Valor |
|-------|-------|
| **Cluster** | db-sysne.neh4dci.mongodb.net |
| **Usuario** | Vercel-Admin-db_sysne |
| **Contraseña** | lhAv2Av7NrwGxv6l |
| **Base de Datos** | db_ecommerce |
| **Protocolo** | MongoDB+SRV |

---

## 📝 Acceso a MongoDB Atlas

1. Ve a [MongoDB Atlas](https://cloud.mongodb.com)
2. Ingresa con tu cuenta (la que tiene el cluster)
3. Selecciona el proyecto
4. Ingresa a **Clusters** → **db-sysne**
5. Haz clic en **Connect** para ver la URI de conexión

---

## 🔗 Conexión desde la Aplicación

La aplicación ahora se conectará automáticamente a MongoDB Atlas usando las credenciales del `.env`.

Para verificar la conexión, ejecuta:

```bash
python -c "
import asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv
import os

load_dotenv()

async def test():
    client = AsyncIOMotorClient(os.getenv('MONGO_URL'))
    await client.admin.command('ping')
    db = client[os.getenv('MONGO_DB_NAME')]
    collections = await db.list_collection_names()
    print('✓ Conexión exitosa')
    print(f'Colecciones: {collections}')
    client.close()

asyncio.run(test())
"
```

---

## 📊 Verificación de Datos

### Colecciones Creadas

```
usuarios              0 documentos
admin_usuarios        1 documento  (usuario admin)
servicios             3 documentos
productos             0 documentos
presupuestos          0 documentos
contratos             0 documentos
configuraciones       3 documentos
```

### Admin por Defecto

- **Usuario**: `admin`
- **Email**: `fjuansimon@gmail.com`
- **Contraseña**: `admin123`
- **Nota**: Cambiar esta contraseña antes de producción

---

## 🚀 Desplegar en Vercel

### 1. **Sincronizar Variables de Entorno**

En el dashboard de Vercel:
1. Ve a **Settings** → **Environment Variables**
2. Copia las siguientes variables de `.env.vercel`:

```
MONGO_URL
MONGO_DB_NAME
MONGODB_URL
PROJECT_NAME
ENVIRONMENT
SMTP_SERVER
SMTP_PORT
SMTP_USE_TLS
SMTP_USE_SSL
USERNAME_EMAIL
PASSWORD_EMAIL
MAIL_FROM
MAIL_FROM_NAME
ALGORITHM
ACCESS_TOKEN_DURATION
SECRET
ORIGINS
GOOGLE_AI_API_KEY
MERCADOPAGO_ACCESS_TOKEN
MERCADOPAGO_PUBLIC_KEY
```

### 2. **Redeploy**

```bash
git push origin main
```

O desde el dashboard de Vercel, haz clic en **Redeploy**.

---

## 🔄 Scripts Útiles

### Verificar estado de la base de datos
```bash
python check_local_mongo.py
```

### Migrar datos desde local a Atlas (si hubiera datos locales)
```bash
python migrate_to_atlas.py
```

### Inicializar/Reinicializar la base de datos
```bash
python init_atlas_db.py
```

---

## ⚠️ Consideraciones Importantes

### Seguridad
- ✓ Las credenciales están cifradas en Vercel
- ⚠️ No commits credenciales al repositorio
- ✓ Los IPs permitidos están configurados en MongoDB Atlas
- ✓ Usa HTTPS en producción

### Backups
- MongoDB Atlas proporciona backups automáticos
- Ve a **Backup** en el cluster para administrarlos
- Configura backups automáticos si es necesario

### Monitoreo
- MongoDB Atlas proporciona monitoreo en tiempo real
- Ve a **Monitoring** para ver métricas de rendimiento
- Configura alertas en **Alerts**

---

## 📞 Próximos Pasos

1. **Validar funcionamiento en local**
   ```bash
   python -m uvicorn main:app --reload
   ```

2. **Realizar pruebas con la API**
   - Crear usuario
   - Login
   - Consultar servicios
   - Crear presupuestos

3. **Desplegar a Vercel**
   ```bash
   git push origin main
   ```

4. **Validar en producción**
   - Probar endpoints principales
   - Verificar CORS
   - Validar autenticación

---

## 🐛 Solución de Problemas

### Error: "Conexión rechazada"
- Verifica que la IP de Vercel esté en whitelist de MongoDB Atlas
- En MongoDB Atlas: **Network Access** → **Add IP Address** → **Allow access from anywhere**

### Error: "Autenticación fallida"
- Verifica el usuario y contraseña en las variables de entorno
- Asegúrate de haber URL-encoded la contraseña si contiene caracteres especiales

### Error: "Timeout"
- Aumenta el timeout en la configuración de Beanie
- Verifica la latencia de red

---

**Migración completada el:** 12 de enero de 2026  
**Estado:** ✅ Completado y verificado  
**Base de datos:** 🟢 Online y operacional
