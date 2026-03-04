az webapp log config --name question-bank-search-tool --resource-group martina.piccardi_rg_3178 --application-logging filesystem --level information 2>$null
Write-Host "Logging enabled. Streaming logs..." -ForegroundColor Cyan
az webapp log tail --name question-bank-search-tool --resource-group martina.piccardi_rg_3178 2>$null
