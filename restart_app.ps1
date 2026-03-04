az webapp restart --name question-bank-search-tool --resource-group martina.piccardi_rg_3178 2>$null
Write-Host "Restarted. Waiting 10s then checking..." -ForegroundColor Cyan
Start-Sleep -Seconds 10
az webapp show --name question-bank-search-tool --resource-group martina.piccardi_rg_3178 --query state -o tsv 2>$null
