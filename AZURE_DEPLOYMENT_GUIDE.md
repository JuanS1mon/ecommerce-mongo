# Guía para Configurar ecommerce-mongo en Azure App Service

## ✅ Configuración Completada

### 1. Comando de Inicio Configurado
```bash
gunicorn -w 2 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app
```

### 2. Logging Habilitado
- Logs del servidor web configurados en filesystem
- Retención: 3 días, máximo 100MB

### 3. Código Desplegado
- Build completado exitosamente
- Archivo zip subido con todos los módulos necesarios incluidos (pre_import.py)

### 4. Variables de Entorno Configuradas
Las siguientes variables están configuradas correctamente:
- ✅ DB_NAME=db_ecomerce
- ✅ ENVIRONMENT=production
- ✅ SECRET_KEY=ed53d0e9d819395d703d9f6236cab23338c5bf8d82b64cfd8d62e13d18bcf179
- ✅ FRONTEND_URL=https://ecommerce-mongo-h3gxh7cjfzgme2g9.westus2-01.azurewebsites.net
- ✅ BACKEND_URL=https://ecommerce-mongo-h3gxh7cjfzgme2g9.westus2-01.azurewebsites.net
- ✅ SCM_DO_BUILD_DURING_DEPLOYMENT=true
- ✅ ENABLE_ORYX_BUILD=true

## ⚠️ Acción Requerida: Configurar MONGO_URL

Azure CLI tiene problemas con los caracteres especiales (`&`) en PowerShell. 
La variable MONGO_URL debe configurarse desde Azure Portal:

### Pasos para configurar MONGO_URL:

1. **Ir al Portal de Azure**: https://portal.azure.com

2. **Buscar y abrir** tu App Service: `ecommerce-mongo`

3. **Ir a Configuration** (Configuración):
   - En el menú izquierdo: Settings → Configuration
   
4. **Agregar o editar MONGO_URL**:
   - Click en "New application setting" o editar si ya existe
   - Name: `MONGO_URL`
   - Value: `mongodb+srv://dbadmin:Pantone123@ecommerce-db.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000`
   - Click en "OK"

5. **Guardar cambios**:
   - Click en "Save" en la parte superior
   - Confirmar "Continue" cuando pregunte si quiere reiniciar

### Alternativa: Usar Azure Cloud Shell (Bash)

Si prefieres usar comandos, abre Azure Cloud Shell en modo **Bash** (no PowerShell):

```bash
az webapp config appsettings set \
  --name ecommerce-mongo \
  --resource-group testing \
  --settings "MONGO_URL=mongodb+srv://dbadmin:Pantone123@ecommerce-db.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000"
```

Luego reiniciar:
```bash
az webapp restart --name ecommerce-mongo --resource-group testing
```

## 🔍 Verificar el Despliegue

Una vez configurado MONGO_URL:

### 1. Ver logs en tiempo real:
```powershell
az webapp log tail --name ecommerce-mongo --resource-group testing
```

### 2. Verificar que la app está corriendo:
```powershell
curl https://ecommerce-mongo-h3gxh7cjfzgme2g9.westus2-01.azurewebsites.net
```

### 3. Verificar todas las variables de entorno:
```powershell
az webapp config appsettings list --name ecommerce-mongo --resource-group testing --output table
```

## 📊 Estado del Recurso

- **Nombre**: ecommerce-mongo
- **Resource Group**: testing
- **Location**: West US 2
- **URL**: https://ecommerce-mongo-h3gxh7cjfzgme2g9.westus2-01.azurewebsites.net
- **Runtime**: Python 3.11
- **SKU**: B1 (Basic)
- **Estado**: Running

## 🔧 Comandos Útiles

### Reiniciar la aplicación:
```powershell
az webapp restart --name ecommerce-mongo --resource-group testing
```

### Ver estado de despliegues:
```powershell
az webapp deployment list --name ecommerce-mongo --resource-group testing --output table
```

### Acceder a Kudu (consola avanzada):
```
https://ecommerce-mongo-h3gxh7cjfzgme2g9.scm.westus2-01.azurewebsites.net
```

## 🗑️ Limpieza de Recursos (cuando termines)

Para eliminar el recurso y evitar cargos:
```powershell
az group delete --name testing --no-wait
```

## 📝 Notas Importantes

1. **MongoDB Connection**: La app usa Azure Cosmos DB con API de MongoDB
2. **Build Process**: Oryx build está habilitado para instalar dependencias automáticamente
3. **Static Files**: Los archivos estáticos se sirven desde la carpeta `/static`
4. **Startup**: Gunicorn usa 2 workers con UvicornWorker para FastAPI

## ⚡ Siguientes Pasos

1. Configurar MONGO_URL en Azure Portal (ver instrucciones arriba)
2. Esperar 1-2 minutos para que la app reinicie
3. Verificar que la app responde correctamente
4. Revisar logs si hay errores
