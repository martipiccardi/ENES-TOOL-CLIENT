param(
    [string]$ResourceGroup = "martina.piccardi_rg_3178",
    [string]$AppName = "question-bank-search-tool"
)

Write-Host "Stopping app..." -ForegroundColor Cyan
az webapp stop --resource-group $ResourceGroup --name $AppName
Write-Host "Waiting 10s..." -ForegroundColor Cyan
Start-Sleep -Seconds 10

Write-Host "Deploying to Azure..." -ForegroundColor Cyan
az webapp deploy --resource-group $ResourceGroup --name $AppName --src-path deploy.zip --type zip --clean true

Write-Host "Starting app..." -ForegroundColor Cyan
az webapp start --resource-group $ResourceGroup --name $AppName

Write-Host "Done! https://$AppName.azurewebsites.net" -ForegroundColor Green
