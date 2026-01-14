# Solución de Problemas - Admin Login en Vercel

## Problema: No puedo acceder a /admin/login en Vercel

### Pasos para diagnosticar y solucionar:

1. **Verificar configuración de Vercel:**
   - Ve a tu proyecto en Vercel Dashboard
   - Ve a Settings > Environment Variables
   - Asegúrate de tener configuradas estas variables:

   ```
   MONGO_URL=mongodb+srv://dbadmin:Pantone123@ecommerce-db.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000
   DB_NAME=db_sysne
   ENVIRONMENT=production
   SECRET_KEY=tu_clave_secreta_aqui
   VERCEL=1
   ```

2. **Verificar diagnóstico:**
   - Visita: `https://tu-dominio.vercel.app/debug/admin`
   - Esto te mostrará el estado de la configuración

3. **Crear usuario admin (si no existe):**
   - Visita: `https://tu-dominio.vercel.app/debug/create-admin`
   - Esto creará un usuario admin por defecto (usuario: admin, password: admin123)

4. **Verificar CORS:**
   - El dominio de Vercel debe estar en la lista de ORIGINS permitidos
   - Se agregó automáticamente detección de VERCEL_URL

5. **Credenciales de admin por defecto:**
   - Usuario: `admin`
   - Contraseña: `admin123`
   - Cambia la contraseña después del primer login

### Comandos para verificar localmente:

```bash
# Verificar que las rutas de admin estén registradas
curl http://localhost:8000/admin/login

# Verificar diagnóstico
curl http://localhost:8000/debug/admin

# Crear admin si no existe
curl -X POST http://localhost:8000/debug/create-admin
```

### Logs de Vercel:

Revisa los logs de Vercel en el dashboard para ver si hay errores de conexión a la base de datos o problemas de importación.

### Problemas comunes:

1. **Variables de entorno no configuradas:** Asegúrate de que MONGO_URL apunte a Azure Cosmos DB
2. **CORS bloqueando requests:** El dominio de Vercel debe estar en ORIGINS
3. **Usuario admin no existe:** Usa el endpoint de debug para crear uno
4. **Base de datos no inicializada:** Verifica que la colección `admin_usuarios` exista