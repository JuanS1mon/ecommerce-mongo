# 🗄️ ARQUITECTURA DE BASES DE DATOS

## 📋 Resumen

Esta aplicación utiliza **DOS bases de datos MongoDB** separadas:

1. **Base de Datos Local (App)** - Base de datos principal de la aplicación
2. **Base de Datos Externa (Remota)** - Base de datos maestra de usuarios admin

---

## 1️⃣ Base de Datos Local (App)

### Conexión

```env
# En .env
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=db_ecomerce
```

**En Producción (Vercel/Azure):**
```env
MONGO_URL=mongodb+srv://usuario:password@cluster.mongodb.net/?appName=db_ecomerce
MONGO_DB_NAME=db_ecomerce
```

### Propósito
- Base de datos principal de la aplicación ecommerce
- Almacena datos de la aplicación local

### Colecciones Principales

```
db_ecomerce/
├── admin_usuarios          # Usuarios admin sincronizados LOCALMENTE
├── ecomerce_usuarios       # Usuarios del ecommerce
├── ecomerce_productos      # Catálogo de productos
├── ecomerce_categorias     # Categorías de productos
├── ecomerce_pedidos        # Pedidos de clientes
├── ecomerce_carritos       # Carritos de compra
├── ecomerce_cupones        # Cupones de descuento
├── ecomerce_resenas        # Reseñas de productos
├── ecomerce_lista_deseos   # Listas de deseos
├── ecomerce_presupuestos   # Presupuestos
├── ecomerce_configuracion  # Configuración del sistema
└── marketing_*             # Campañas de marketing
```

### Características
- ✅ Base de datos principal de la aplicación
- ✅ Usuarios admin son **SINCRONIZADOS** desde la base externa
- ✅ Todos los datos del ecommerce se almacenan aquí
- ✅ Puede ser local (desarrollo) o remota (producción)

---

## 2️⃣ Base de Datos Externa (Remota) - FUENTE DE VERDAD

### Conexión

```env
# En .env o variables de entorno
MONGO_EXTERNAL_URL=mongodb+srv://Vercel-Admin-db_sysne:Pantone123@db-sysne.neh4dci.mongodb.net/?appName=db-sysne
MONGO_EXTERNAL_DB_NAME=db_sysne
```

**Importante:** Esta es la base de datos MAESTRA de usuarios admin.

### Propósito
- Base de datos centralizada de usuarios administradores
- Fuente de verdad para proyectos y vinculaciones
- Sistema multi-aplicación (varios proyectos usan esta base)

### Colecciones Principales

```
db_sysne/
├── admin_usuarios         # FUENTE DE VERDAD de usuarios admin
├── proyectos              # Lista de proyectos del sistema
└── usuario_proyectos      # Vinculaciones usuario-proyecto con vencimientos
```

### Características
- ✅ Base de datos centralizada y remota
- ✅ **FUENTE DE VERDAD** para usuarios admin
- ✅ Sistema multi-aplicación (varios proyectos la consultan)
- ✅ Gestiona fechas de vencimiento centralizadas
- ✅ Administrador puede gestionar usuarios desde un solo lugar

---

## 🔄 Flujo de Sincronización

### Sincronización de Usuarios Admin

```
┌─────────────────────────────────────────────────────────────┐
│        BASE DE DATOS EXTERNA (db_sysne)                    │
│                FUENTE DE VERDAD                             │
│  mongodb+srv://...@db-sysne.neh4dci.mongodb.net            │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ 1. CONSULTA
                         │ GET /api/v1/proyecto/Ecomerce/usuarios
                         │
                         ▼
          ┌──────────────────────────────┐
          │ API de Validación Externa    │
          │ Endpoint: /api/v1/validate   │
          └──────────┬───────────────────┘
                     │
                     │ 2. SINCRONIZACIÓN AUTOMÁTICA
                     │ (Durante login o manual)
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│         BASE DE DATOS LOCAL (db_ecomerce)                   │
│            DATOS SINCRONIZADOS                              │
│  mongodb://localhost:27017/db_ecomerce                      │
│  - Usuarios admin sincronizados                             │
│  - Productos, pedidos, carritos del ecommerce               │
└─────────────────────────────────────────────────────────────┘
```

### Proceso Detallado

1. **Usuario intenta hacer login** en `/admin/login`
2. **Sistema busca usuario localmente** en `db_ecomerce.admin_usuarios`
3. Si NO existe o datos desactualizados:
   - **Consulta la base externa** `db_sysne`
   - **Obtiene datos actualizados** del usuario
   - **Sincroniza localmente** en `db_ecomerce`
4. **Valida credenciales** con datos sincronizados
5. **Valida fecha de vencimiento** local
6. **Genera JWT** y permite acceso

---

## ⚙️ Configuración

### Variables de Entorno Requeridas

**Para Desarrollo (.env):**

```env
# ===== BASE DE DATOS LOCAL (APP) =====
MONGO_URL=mongodb://localhost:27017
MONGO_DB_NAME=db_ecomerce

# ===== BASE DE DATOS EXTERNA (REMOTA) =====
# URL de la API que consulta db_sysne
API_BASE_URL=http://127.0.0.1:8000

# Nombre del proyecto en el sistema de proyectos
ADMIN_PROYECTO_NOMBRE=Ecomerce
```

**Para Producción (Vercel/Azure):**

```env
# ===== BASE DE DATOS LOCAL (APP) =====
MONGO_URL=mongodb+srv://usuario:password@cluster-ecomerce.mongodb.net/?appName=db_ecomerce
MONGO_DB_NAME=db_ecomerce

# ===== BASE DE DATOS EXTERNA (REMOTA) =====
# URL de la API pública que consulta db_sysne
API_BASE_URL=https://tu-api-principal.vercel.app

# Nombre del proyecto en el sistema de proyectos
ADMIN_PROYECTO_NOMBRE=Ecomerce
```

---

## 🔐 API de Validación Externa

La base de datos externa (`db_sysne`) se consulta a través de una **API RESTful pública**.

### Endpoints Disponibles

#### 1. Listar Usuarios de un Proyecto
```http
GET /api/v1/proyecto/{proyecto_nombre}/usuarios
```

**Ejemplo:**
```bash
curl https://tu-api-principal.vercel.app/api/v1/proyecto/Ecomerce/usuarios
```

**Respuesta:**
```json
{
  "proyecto": "Ecomerce",
  "usuarios": [
    {
      "email": "admin@sysneg.com",
      "username": "admin",
      "nombre": "Admin Sysneg",
      "activo": true,
      "fecha_vencimiento": "2026-07-03T23:59:59Z",
      "clave_hash": "$2b$12$..."
    }
  ],
  "total": 1
}
```

#### 2. Validar Acceso de Usuario
```http
POST /api/v1/validate
Content-Type: application/json

{
  "email": "admin@sysneg.com",
  "password": "password123",
  "proyecto_nombre": "Ecomerce"
}
```

**Respuesta Exitosa:**
```json
{
  "valid": true,
  "mensaje": "Acceso válido",
  "datos_usuario": {
    "email": "admin@sysneg.com",
    "username": "admin"
  },
  "fecha_vencimiento": "2026-07-03T23:59:59Z"
}
```

---

## 📊 Diagrama Completo

```
┌─────────────────────────────────────────────────────────────────────┐
│                    APLICACIÓN ECOMMERCE                             │
│                   (Puerto 8000 - Vercel)                            │
└────────────┬────────────────────────────────────┬───────────────────┘
             │                                    │
             │                                    │
    ┌────────▼────────┐                  ┌────────▼─────────┐
    │  BASE LOCAL     │                  │  API EXTERNA     │
    │  db_ecomerce    │                  │  /api/v1/...     │
    │  (App Data)     │                  │  (Validación)    │
    └─────────────────┘                  └────────┬─────────┘
             │                                    │
             │                                    │
             │                            ┌───────▼──────────┐
             │                            │ BASE EXTERNA     │
             │                            │ db_sysne         │
             │                            │ (Fuente Verdad)  │
             │                            └──────────────────┘
             │
    ┌────────▼────────────────────────────────────────────────┐
    │  Datos Sincronizados Localmente:                        │
    │  - admin_usuarios (sincronizados desde db_sysne)        │
    │  - ecomerce_* (datos propios de la app)                 │
    └─────────────────────────────────────────────────────────┘
```

---

## 🔧 Scripts de Sincronización

### Sincronización Manual

```bash
# Simular (dry-run)
python sincronizar_usuarios_admin.py --dry-run

# Ejecutar sincronización real
python sincronizar_usuarios_admin.py
```

### Sincronización Automática

La sincronización ocurre automáticamente en:
- ✅ **Login de usuario admin** - Si el usuario no existe o datos desactualizados
- ✅ **Validación de credenciales** - Si la contraseña no coincide
- ✅ **Verificación de vencimiento** - Si la fecha está próxima a vencer

---

## 🚀 Deployment

### Paso 1: Configurar Base de Datos Local

**MongoDB Atlas (Recomendado para producción):**

1. Crear cluster en MongoDB Atlas
2. Crear base de datos `db_ecomerce`
3. Obtener string de conexión
4. Configurar en Vercel:
   ```
   MONGO_URL=mongodb+srv://...
   MONGO_DB_NAME=db_ecomerce
   ```

### Paso 2: Configurar Acceso a Base Externa

**Configurar API de validación:**

1. Asegurarse de que la API que consulta `db_sysne` esté desplegada
2. Configurar en Vercel:
   ```
   API_BASE_URL=https://tu-api-principal.vercel.app
   ADMIN_PROYECTO_NOMBRE=Ecomerce
   ```

### Paso 3: Probar Sincronización

```bash
# Probar endpoint de listado
curl https://tu-api-principal.vercel.app/api/v1/proyecto/Ecomerce/usuarios

# Probar endpoint de validación
curl -X POST https://tu-api-principal.vercel.app/api/v1/validate \
  -H "Content-Type: application/json" \
  -d '{
    "email": "admin@sysneg.com",
    "password": "password123",
    "proyecto_nombre": "Ecomerce"
  }'
```

---

## ⚠️ Consideraciones Importantes

### Seguridad

1. **Nunca expongas credenciales** de la base externa en el código
2. **Usa variables de entorno** para todas las conexiones
3. **La base externa debería estar protegida** con IP whitelist
4. **HTTPS obligatorio** en producción

### Performance

1. **Caché de sincronización**: Los usuarios se sincronizan solo cuando es necesario
2. **Validación local**: Las requests subsecuentes usan datos locales
3. **Timeout corto**: 5-10 segundos máximo para API externa

### Backup

1. **Backup ambas bases** regularmente
2. **Base externa es crítica** - Es la fuente de verdad
3. **Base local puede reconstruirse** mediante sincronización

---

## 📝 Checklist de Configuración

### Desarrollo Local

- [ ] MongoDB local corriendo en puerto 27017
- [ ] Base de datos `db_ecomerce` creada
- [ ] Variables `MONGO_URL` y `MONGO_DB_NAME` en `.env`
- [ ] Variable `API_BASE_URL` apuntando a API externa
- [ ] Variable `ADMIN_PROYECTO_NOMBRE` configurada
- [ ] Script `sincronizar_usuarios_admin.py` ejecutado exitosamente

### Producción (Vercel)

- [ ] MongoDB Atlas cluster creado
- [ ] Base de datos `db_ecomerce` creada en Atlas
- [ ] Variables de entorno configuradas en Vercel
- [ ] API externa accesible desde Vercel
- [ ] Endpoint `/api/v1/proyecto/Ecomerce/usuarios` funcional
- [ ] Endpoint `/api/v1/validate` funcional
- [ ] Sincronización automática probada en login

---

## 📚 Documentación Relacionada

- [SINCRONIZACION_USUARIOS_ADMIN.md](./SINCRONIZACION_USUARIOS_ADMIN.md) - Sistema de sincronización completo
- [INTEGRACION_VALIDACION_EXTERNA.md](./INTEGRACION_VALIDACION_EXTERNA.md) - Integración con apps externas
- [VALIDACION_INTERNA_ADMIN.md](./VALIDACION_INTERNA_ADMIN.md) - Validación interna de vencimientos
- [GUIA_PRUEBAS_ECOMERCE.md](./GUIA_PRUEBAS_ECOMERCE.md) - Guía de pruebas

---

## ❓ FAQ

### ¿Por qué dos bases de datos?

**Respuesta:** Sistema multi-aplicación. La base externa (`db_sysne`) gestiona usuarios admin para MÚLTIPLES proyectos desde un solo lugar. Cada aplicación (como este ecommerce) sincroniza sus usuarios localmente.

### ¿Qué pasa si la base externa no está disponible?

**Respuesta:** El sistema continúa funcionando con los datos sincronizados localmente. La sincronización se reintentará en el próximo login.

### ¿Cómo actualizo un usuario admin?

**Respuesta:** Actualiza en la base externa (`db_sysne`). El cambio se sincronizará automáticamente en el próximo login del usuario.

### ¿Puedo usar solo una base de datos?

**Respuesta:** Sí, pero perderías la capacidad de gestionar usuarios centralizadamente para múltiples proyectos.

---

**Última actualización:** 13 de enero de 2026
