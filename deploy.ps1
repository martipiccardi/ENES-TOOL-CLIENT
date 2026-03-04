param(
    [string]$ResourceGroup = "martina.piccardi_rg_3178",
    [string]$AppName = "question-bank-search-tool"
)

$ErrorActionPreference = "Stop"
$ZipPath = "deploy.zip"
$TempDir = "deploy_tmp"

Write-Host "=== ENES Tool - Azure Deployment ===" -ForegroundColor Cyan

if (-not (Test-Path "frontend\dist")) {
    Write-Host "ERROR: frontend/dist not found. Run 'npm run build' in the frontend folder first." -ForegroundColor Red
    exit 1
}

if (-not (Test-Path "data\enes.duckdb")) {
    Write-Host "ERROR: data/enes.duckdb not found." -ForegroundColor Red
    exit 1
}

if (Test-Path $ZipPath) { Remove-Item $ZipPath }
if (Test-Path $TempDir) { Remove-Item $TempDir -Recurse -Force }

Write-Host "Copying files..." -ForegroundColor Cyan
New-Item -ItemType Directory -Path $TempDir | Out-Null
Copy-Item -Path "backend" -Destination $TempDir -Recurse
Copy-Item -Path "data" -Destination $TempDir -Recurse
Copy-Item -Path "requirements.txt" -Destination $TempDir
Copy-Item -Path "startup.sh" -Destination $TempDir
New-Item -ItemType Directory -Path "$TempDir\frontend" | Out-Null
Copy-Item -Path "frontend\dist" -Destination "$TempDir\frontend" -Recurse

Write-Host "Creating deploy.zip..." -ForegroundColor Cyan
Compress-Archive -Path "$TempDir\*" -DestinationPath $ZipPath
Remove-Item $TempDir -Recurse -Force
$SizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 1)
Write-Host "ZIP size: $SizeMB MB" -ForegroundColor Green

Write-Host "Setting startup command..." -ForegroundColor Cyan
az webapp config set --resource-group $ResourceGroup --name $AppName --startup-file "/home/site/wwwroot/startup.sh"

Write-Host "Deploying to Azure..." -ForegroundColor Cyan
az webapp deploy --resource-group $ResourceGroup --name $AppName --src-path $ZipPath --type zip --clean true --restart true

Write-Host ""
Write-Host "Done! URL: https://$AppName.azurewebsites.net" -ForegroundColor Green
Write-Host "Watch logs: az webapp log tail --name $AppName --resource-group $ResourceGroup" -ForegroundColor Yellow
