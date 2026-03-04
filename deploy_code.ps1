param(
    [string]$ResourceGroup = "martina.piccardi_rg_3178",
    [string]$AppName = "question-bank-search-tool"
)

$ErrorActionPreference = "Stop"
$ZipPath = "deploy_code.zip"

Write-Host "=== Code-only deploy (no data files) ===" -ForegroundColor Cyan

if (Test-Path $ZipPath) { Remove-Item $ZipPath }

Write-Host "Creating zip with forward-slash paths (Linux-compatible)..." -ForegroundColor Cyan
python -c @"
import zipfile, os

files = {
    'startup.sh': 'startup.sh',
    'backend/__init__.py': 'backend/__init__.py',
    'backend/app/__init__.py': 'backend/app/__init__.py',
    'backend/app/main.py': 'backend/app/main.py',
    'backend/app/queries.py': 'backend/app/queries.py',
    'backend/app/semantic_search.py': 'backend/app/semantic_search.py',
    'backend/app/data_store.py': 'backend/app/data_store.py',
    'backend/app/vol_a.py': 'backend/app/vol_a.py',
    'data/vol_a_overrides.json': 'data/vol_a_overrides.json',
}

with zipfile.ZipFile('deploy_code.zip', 'w', zipfile.ZIP_DEFLATED) as zf:
    for src, dst in files.items():
        if os.path.exists(src):
            with open(src, 'r', encoding='utf-8') as f:
                content = f.read()
            zf.writestr(dst, content.replace('\r\n', '\n'))
            print('  + ' + dst)
        else:
            print('  SKIP (not found): ' + src)
print('Zip created.')
"@

$SizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
Write-Host "ZIP size: $SizeMB MB" -ForegroundColor Green

Write-Host "Deploying code to Azure (--clean false keeps existing data)..." -ForegroundColor Cyan
az webapp deploy --resource-group $ResourceGroup --name $AppName --src-path $ZipPath --type zip --clean false --restart true

Write-Host ""
Write-Host "Done! URL: https://$AppName.azurewebsites.net" -ForegroundColor Green
