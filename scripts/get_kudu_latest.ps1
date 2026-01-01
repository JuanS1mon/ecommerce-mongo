$username = '$ecommerce-mongo'
$pwd = '9AXTgHe2lZi1JntvPBBlZJl7h9qn7BjmHfyLx7oeS8brCwe7XdtDQkGoofwl'
$pair = $username + ':' + $pwd
$b = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($pair))
$headers = @{ Authorization = 'Basic ' + $b }
$res = Invoke-RestMethod -Uri 'https://ecommerce-mongo-h3gxh7cjfzgme2g9.scm.westus2-01.azurewebsites.net/api/deployments/latest' -Headers $headers
$res | ConvertTo-Json -Depth 5 | Out-File -Encoding utf8 .\kudu_latest.json
Get-Content .\kudu_latest.json -Raw | Write-Output
