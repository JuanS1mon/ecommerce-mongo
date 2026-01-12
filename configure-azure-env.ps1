# Script para configurar variables de entorno en Azure App Service
# Ejecutar con PowerShell

$appName = "ecommerce-mongo"
$resourceGroup = "testing"

# Variables de entorno a configurar
Write-Host "Configurando variables de entorno..." -ForegroundColor Green

# Variable 1: MONGO_URL
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "MONGO_URL=mongodb+srv://dbadmin:Pantone123@ecommerce-db.mongocluster.cosmos.azure.com/?tls=true&authMechanism=SCRAM-SHA-256&retrywrites=false&maxIdleTimeMS=120000" | Out-Null

Write-Host "✓ MONGO_URL configurado" -ForegroundColor Cyan

# Variable 2: DB_NAME
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "DB_NAME=db_sysne" | Out-Null

Write-Host "✓ DB_NAME configurado" -ForegroundColor Cyan

# Variable 3: ENVIRONMENT
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "ENVIRONMENT=production" | Out-Null

Write-Host "✓ ENVIRONMENT configurado" -ForegroundColor Cyan

# Variable 4: FRONTEND_URL
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "FRONTEND_URL=https://ecommerce-mongo-h3gxh7cjfzgme2g9.westus2-01.azurewebsites.net" | Out-Null

Write-Host "✓ FRONTEND_URL configurado" -ForegroundColor Cyan

# Variable 5: BACKEND_URL
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "BACKEND_URL=https://ecommerce-mongo-h3gxh7cjfzgme2g9.westus2-01.azurewebsites.net" | Out-Null

Write-Host "✓ BACKEND_URL configurado" -ForegroundColor Cyan

# Variable 6: SECRET_KEY
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "SECRET_KEY=ed53d0e9d819395d703d9f6236cab23338c5bf8d82b64cfd8d62e13d18bcf179" | Out-Null

Write-Host "✓ SECRET_KEY configurado" -ForegroundColor Cyan

# Variable 7: SCM_DO_BUILD_DURING_DEPLOYMENT
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "SCM_DO_BUILD_DURING_DEPLOYMENT=true" | Out-Null

Write-Host "✓ SCM_DO_BUILD_DURING_DEPLOYMENT configurado" -ForegroundColor Cyan

# Variable 8: ENABLE_ORYX_BUILD
az webapp config appsettings set `
    --name $appName `
    --resource-group $resourceGroup `
    --settings "ENABLE_ORYX_BUILD=true" | Out-Null

Write-Host "✓ ENABLE_ORYX_BUILD configurado" -ForegroundColor Cyan

Write-Host "`n✅ Todas las variables de entorno configuradas exitosamente" -ForegroundColor Green

# Habilitar Always On (recomendado para apps en producción que usan background tasks o websockets)
az webapp config set `
    --name $appName `
    --resource-group $resourceGroup `
    --always-on true | Out-Null
Write-Host "✓ Always On habilitado" -ForegroundColor Cyan

# Establecer comando de arranque para usar gunicorn + uvicorn worker
$startup = "gunicorn -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 main:app --timeout 120 --log-level info"
az webapp config set `
    --name $appName `
    --resource-group $resourceGroup `
    --startup-file $startup | Out-Null
Write-Host "✓ Startup command configurado: $startup" -ForegroundColor Cyan

# Placeholders para secrets y configuración de integraciones (ajusta antes de ejecutar)
Write-Host "Configura las credenciales sensibles (SMTP, MERCADOPAGO, etc.) usando variables de entorno o Key Vault. Ejemplo:" -ForegroundColor Yellow
Write-Host "  az webapp config appsettings set --name $appName --resource-group $resourceGroup --settings \"SMTP_USERNAME=you@example.com SMTP_PASSWORD=secret MERCADOPAGO_ACCESS_TOKEN=token ADMIN_EMAIL=admin@example.com\"" -ForegroundColor Yellow

Write-Host "`nReiniciando aplicación..." -ForegroundColor Yellow

# Reiniciar la aplicación
az webapp restart --name $appName --resource-group $resourceGroup

Write-Host "✅ Aplicación reiniciada" -ForegroundColor Green
