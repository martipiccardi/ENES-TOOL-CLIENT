Get-ChildItem 'backend' -Recurse -File | Sort-Object Length -Descending | Select-Object -First 15 FullName, @{N='MB';E={[math]::Round($_.Length/1MB,2)}} | Format-Table
