# Script para configurar MercadoPago en producción
# Ejecutar con: .\setup_mercadopago_prod.ps1

Write-Host "=== CONFIGURACIÓN MERCADOPAGO PRODUCCIÓN ===" -ForegroundColor Yellow
Write-Host ""

# Solicitar credenciales
$accessToken = Read-Host "Ingresa tu Access Token de PRODUCCIÓN (PROD-...)"
$publicKey = Read-Host "Ingresa tu Public Key de PRODUCCIÓN (APP_USR-...)"
$domain = Read-Host "Ingresa tu dominio (ej: midominio.com)"

Write-Host ""
Write-Host "Configurando variables de entorno..." -ForegroundColor Cyan

# Configurar variables de entorno
$env:MERCADOPAGO_ACCESS_TOKEN = $accessToken
$env:MERCADOPAGO_PUBLIC_KEY = $publicKey
$env:MERCADOPAGO_ENVIRONMENT = "production"
$env:MERCADOPAGO_NOTIFICATION_URL = "https://$domain/ecomerce/checkout/webhook/mercadopago"
$env:MERCADOPAGO_SUCCESS_URL = "https://$domain/checkout/success"
$env:MERCADOPAGO_FAILURE_URL = "https://$domain/checkout/failure"
$env:MERCADOPAGO_PENDING_URL = "https://$domain/checkout/pending"

Write-Host ""
Write-Host "✅ Variables configuradas:" -ForegroundColor Green
Write-Host "Access Token: $env:MERCADOPAGO_ACCESS_TOKEN"
Write-Host "Public Key: $env:MERCADOPAGO_PUBLIC_KEY"
Write-Host "Environment: $env:MERCADOPAGO_ENVIRONMENT"
Write-Host "Notification URL: $env:MERCADOPAGO_NOTIFICATION_URL"
Write-Host "Success URL: $env:MERCADOPAGO_SUCCESS_URL"
Write-Host "Failure URL: $env:MERCADOPAGO_FAILURE_URL"
Write-Host "Pending URL: $env:MERCADOPAGO_PENDING_URL"

Write-Host ""
Write-Host "⚠️ IMPORTANTE: Estas variables son temporales." -ForegroundColor Yellow
Write-Host "Para hacerlas permanentes, configura variables de entorno del sistema." -ForegroundColor Yellow
Write-Host ""
Write-Host "Para probar, ejecuta:" -ForegroundColor Cyan
Write-Host "python -m uvicorn main:app --host 127.0.0.1 --port 8000 --log-level info"