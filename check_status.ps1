Write-Host "=== App state ===" -ForegroundColor Cyan
az webapp show --name question-bank-search-tool --resource-group martina.piccardi_rg_3178 --query "{state:state, lastModified:lastModifiedTimeUtc}" -o table 2>$null

Write-Host "`n=== Recent logs ===" -ForegroundColor Cyan
az webapp log download --name question-bank-search-tool --resource-group martina.piccardi_rg_3178 --log-file recent_logs.zip 2>$null
if (Test-Path recent_logs.zip) {
    Expand-Archive recent_logs.zip -DestinationPath recent_logs -Force
    Get-ChildItem recent_logs -Recurse -Filter "*.log" | ForEach-Object {
        Write-Host "`n--- $($_.Name) ---" -ForegroundColor Yellow
        Get-Content $_.FullName | Select-Object -Last 30
    }
}
