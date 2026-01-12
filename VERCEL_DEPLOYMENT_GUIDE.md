# 🚀 Guía de Despliegue en Vercel - MongoDB Atlas

## 📌 Pasos para Desplegar en Vercel

### Paso 1: Agregar Variables de Entorno en Vercel

1. Ve a tu proyecto en [Vercel Dashboard](https://vercel.com/dashboard)
2. Selecciona tu proyecto
3. Ve a **Settings** → **Environment Variables**
4. Agregue las siguientes variables (cópielas del archivo `.env.vercel`):

```env
# MongoDB Atlas
MONGO_URL=mongodb+srv://Vercel-Admin-db_sysne:lhAv2Av7NrwGxv6l@db-sysne.neh4dci.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=db_ecommerce
MONGODB_URL=mongodb+srv://Vercel-Admin-db_sysne:lhAv2Av7NrwGxv6l@db-sysne.neh4dci.mongodb.net/db_ecommerce?retryWrites=true&w=majority

# Aplicación
PROJECT_NAME=app_Ecomerce
ENVIRONMENT=production
BASE_URL=https://tu-proyecto.vercel.app
FRONTEND_URL=https://tu-proyecto.vercel.app

# Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USE_SSL=false
USERNAME_EMAIL=fjuansimon@gmail.com
PASSWORD_EMAIL=kfiq isrr gyjw qtng
MAIL_FROM=fjuansimon@gmail.com
MAIL_FROM_NAME=app_Ecomerce

# Autenticación
ALGORITHM=HS256
ACCESS_TOKEN_DURATION=360
SECRET=11018517e34d137b782c1f6af9d9e20ebb8ec6425b5b97689e2715b6cb3187c4

# CORS
ORIGINS=https://tu-proyecto.vercel.app

# Integraciones
GOOGLE_AI_API_KEY=AIzaSyB-3g8njFpew09BNthUaaeUy0sVbAGvKuY
MERCADOPAGO_ACCESS_TOKEN=TEST-4638869150198277-110316-202a1385377cfc96c5f43eab7829c5ce-168706559
MERCADOPAGO_PUBLIC_KEY=TEST-6c596386-b72b-444b-8402-d59bab22540f
```

### Paso 2: Configurar Whitelist en MongoDB Atlas

Para que Vercel pueda acceder a MongoDB Atlas:

1. Ve a [MongoDB Atlas](https://cloud.mongodb.com)
2. Selecciona tu cluster (db-sysne)
3. Ve a **Network Access** → **IP Whitelist**
4. Haz clic en **Add IP Address**
5. Selecciona **Allow Access from Anywhere** (0.0.0.0/0)
6. Confirma

**Nota:** En producción, es mejor agregar IPs específicas de Vercel. Contacta con el soporte de Vercel para obtenerlas.

### Paso 3: Configurar Build y Start

Asegúrate de que tu `vercel.json` está configurado correctamente:

```json
{
  "buildCommand": "pip install -r requirements.txt",
  "outputDirectory": ".",
  "framework": "python",
  "installCommand": "pip install -r requirements.txt",
  "env": {
    "PYTHONUNBUFFERED": "1"
  }
}
```

O si usas Dockerfile:

```json
{
  "build": {
    "env": {
      "PYTHONUNBUFFERED": "1"
    }
  }
}
```

### Paso 4: Realizar Deploy

```bash
# 1. Commit y push
git add .
git commit -m "Migración a MongoDB Atlas"
git push origin main

# 2. Vercel desplegará automáticamente
# Puedes monitorear en https://vercel.com/dashboard
```

---

## ✅ Verificación Post-Deploy

### 1. Validar Endpoints

```bash
# Salud de la API
curl https://tu-proyecto.vercel.app/docs

# Obtener servicios
curl https://tu-proyecto.vercel.app/api/servicios

# Login admin
curl -X POST https://tu-proyecto.vercel.app/api/admin/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"admin","clave":"admin123"}'
```

### 2. Verificar Logs

En Vercel Dashboard:
- Ve a **Deployments**
- Selecciona el último deploy
- Abre **Function logs** para ver los errores

### 3. Monitorear Base de Datos

En MongoDB Atlas:
- Ve a **Monitoring** para ver uso de CPU, memoria, etc.
- Ve a **Database Activity** para ver queries
- Ve a **Alerts** para configurar notificaciones

---

## 🐛 Solución de Problemas Comunes

### Error: "MongoDB connection timeout"
**Causa:** Whitelist no está configurado  
**Solución:** Asegúrate de haber agregado la IP de Vercel al whitelist de MongoDB Atlas

### Error: "Invalid connection string"
**Causa:** Credenciales mal copiadas  
**Solución:** Verifica la URI en MongoDB Atlas → Connect → Connection String

### Error: "Database does not exist"
**Causa:** `MONGO_DB_NAME` es incorrecto  
**Solución:** Debe ser exactamente `db_ecommerce`

### Error: "Authentication failed"
**Causa:** Usuario/contraseña incorrectos  
**Solución:** Copia exactamente: `Vercel-Admin-db_sysne:lhAv2Av7NrwGxv6l`

---

## 📊 Monitoreo en Producción

### Configurar Alertas en MongoDB Atlas

1. Ve a **Alerts** → **Create Alert Policy**
2. Configura alertas para:
   - **Replication Lag** > 10 segundos
   - **CPU Usage** > 80%
   - **Memory Usage** > 90%
   - **Query Execution Time** > 1 segundo

### Logs en Vercel

Para ver logs de tu aplicación:

```bash
# Instalación de Vercel CLI
npm install -g vercel

# Ver logs
vercel logs --project=tu-proyecto
```

---

## 🔐 Seguridad en Producción

- [ ] Cambiar contraseña de admin (`admin123` → contraseña segura)
- [ ] Usar variables de entorno para credenciales sensibles
- [ ] Configurar dominio personalizado en Vercel
- [ ] Habilitar SSL/TLS (automático en Vercel)
- [ ] Configurar rate limiting en Vercel
- [ ] Habilitar CORS solo para dominios confiables
- [ ] Renovar SECRET_KEY periódicamente
- [ ] Monitorear accesos fallidos

---

## 🔄 Actualizaciones Futuras

Para desplegar cambios:

```bash
# 1. Realiza cambios locales
# 2. Prueba localmente
python -m uvicorn main:app --reload

# 3. Commit y push
git add .
git commit -m "Descripción de cambios"
git push origin main

# 4. Vercel desplegará automáticamente
```

---

## 📞 Soporte

### MongoDB Atlas
- Documentación: https://docs.mongodb.com/
- Soporte: https://support.mongodb.com

### Vercel
- Documentación: https://vercel.com/docs
- Soporte: https://vercel.com/support

### Tu Aplicación
- Contacta con el equipo de desarrollo

---

**Actualizado:** 12 de enero de 2026  
**Estado:** ✅ Listo para producción
