<#
Script: setup_azure_github_secrets.ps1
Descripción: Crea un Service Principal en Azure y sube Secrets a GitHub usando `gh`.
Uso: Ejecutar en PowerShell local o Cloud Shell tras hacer `az login` y `gh auth login`.
#>
param(
    [string]$SubscriptionId = "e08987ee-0468-4b1f-bcab-cf039163ccb6",
    [string]$ResourceGroup = "testing",
    [string]$SPName = "github-action-ecommerce-mongo",
    [string]$Repo = "JuanS1mon/ecommerce-mongo",
    [string]$EnvFile = "envi2.env"
)

function Ensure-CommandExists([string]$cmd) {
    $exists = Get-Command $cmd -ErrorAction SilentlyContinue
    if (-not $exists) {
        Write-Error "Se requiere '$cmd' en PATH. Instala y autentica antes de ejecutar este script."
        exit 1
    }
}

Ensure-CommandExists -cmd az
Ensure-CommandExists -cmd gh

Write-Host "1) Seleccionando suscripción $SubscriptionId..." -ForegroundColor Cyan
$null = az account set --subscription $SubscriptionId
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error seleccionando suscripción. Ejecuta 'az login' y verifica permisos." 
    exit 1
}

# Verificar que la subscripción seleccionada es la correcta
$sel = az account show --query id -o tsv 2>$null
if ($sel -ne $SubscriptionId) {
    Write-Error "La suscripción activa ($sel) difiere de la esperada ($SubscriptionId). Asegúrate de seleccionar la suscripción correcta con 'az account set'."
    exit 1
}

# Verificar login de gh
$null = gh auth status 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Error "GitHub CLI no autenticado. Ejecuta 'gh auth login' antes de correr el script."
    exit 1
}

Write-Host "2) Creando Service Principal (se guardará en memoria)..." -ForegroundColor Cyan
$spJson = az ad sp create-for-rbac --name $SPName --role contributor --scopes "/subscriptions/$SubscriptionId/resourceGroups/$ResourceGroup" --sdk-auth -o json 2>$null
if ($LASTEXITCODE -ne 0 -or -not $spJson) {
    Write-Error "Error creando Service Principal. Revisa permisos y vuelve a intentar." 
    exit 1
}

Write-Host "3) Subiendo AZURE_CREDENTIALS (Service Principal) a GitHub Secrets..." -ForegroundColor Green
$null = gh secret set AZURE_CREDENTIALS --repo $Repo --body "$spJson"
if ($LASTEXITCODE -ne 0) {
    Write-Error "Error subiendo AZURE_CREDENTIALS a GitHub: verifica permisos en el repo y 'gh auth status'"
    exit 1
}
Write-Host "  OK AZURE_CREDENTIALS creado" -ForegroundColor Green

# Función para parsear env file
function Parse-EnvFile($path) {
    if (-not (Test-Path $path)) { throw "No se encontró $path" }
    $lines = Get-Content $path | ForEach-Object { $_.Trim() } | Where-Object { $_ -and -not ($_ -like '#*') }
    $dict = @{ }
    foreach ($l in $lines) {
        if ($l -match '^(.*?)=(.*)$') {
            $k = $matches[1].Trim()
            $v = $matches[2].Trim()
            # remover comillas si existen
            if ($v.StartsWith('"') -and $v.EndsWith('"')) { $v = $v.Trim('"') }
            if ($v.StartsWith("'") -and $v.EndsWith("'")) { $v = $v.Trim("'") }
            $dict[$k] = $v
        }
    }
    return $dict
}

Write-Host "4 - Leyendo variables de $EnvFile..." -ForegroundColor Cyan
try {
    $envDict = Parse-EnvFile $EnvFile
} catch {
    Write-Error ("Error leyendo {0} - revisa que el archivo exista y tenga formato KEY=VALUE. Error: {1}" -f $EnvFile, $_)
    exit 1
}

$wanted = @(
    "MONGO_URL",
    "DB_NAME",
    "SECRET_KEY",
    "FRONTEND_URL",
    "BACKEND_URL",
    "MERCADOPAGO_ACCESS_TOKEN",
    "MERCADOPAGO_PUBLIC_KEY",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "ADMIN_EMAIL"
)

Write-Host "5 - Subiendo secrets a GitHub (si existen en $EnvFile)..." -ForegroundColor Cyan
foreach ($k in $wanted) {
    if ($envDict.ContainsKey($k)) {
        $val = $envDict[$k]
        $null = gh secret set $k --repo $Repo --body "$val"
        if ($LASTEXITCODE -ne 0) {
            Write-Warning ([string]::Format("ERROR subiendo {0}: revisa permisos o el valor", $k))
        } else {
            Write-Host "  OK $k subido" -ForegroundColor Green
        }
    } else {
        Write-Host "  - SKIP $k (no presente en $EnvFile)" -ForegroundColor Yellow
    }
}

Write-Host "`nListado de secrets en repo (verifica):" -ForegroundColor Cyan
gh secret list --repo $Repo

Write-Host "`nHecho. Para lanzar el workflow manualmente usa:" -ForegroundColor Green
Write-Host "gh workflow run deploy-azure-webapp.yml --repo $Repo --ref main" -ForegroundColor Yellow
Write-Host "O ve a GitHub -> Actions -> Deploy to Azure Web App -> Run workflow." -ForegroundColor Yellow

# Eliminar sp.json por seguridad
if (Test-Path sp.json) {
    try {
        Remove-Item sp.json -Force
        Write-Host "sp.json eliminado por seguridad" -ForegroundColor Cyan
    } catch {
        Write-Warning "No se pudo eliminar sp.json automáticamente. Por favor elimínalo manualmente." -ForegroundColor Yellow
    }
}
