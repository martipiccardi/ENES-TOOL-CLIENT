Get-ChildItem 'data' -File | Sort-Object Length -Descending | Select-Object Name, @{N='MB';E={[math]::Round($_.Length/1MB,1)}} | Format-Table
