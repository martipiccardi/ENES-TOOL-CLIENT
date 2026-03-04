az webapp log deployment show --name question-bank-search-tool --resource-group martina.piccardi_rg_3178 2>$null | ConvertFrom-Json | ForEach-Object { $_.message } | Select-Object -Last 20
