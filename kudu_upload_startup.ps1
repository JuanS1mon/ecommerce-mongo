$user = '$ecommerce-mongo'
$pass = '9AXTgHe2lZi1JntvPBBlZJl7h9qn7BjmHfyLx7oeS8brCwe7XdtDQkGoofwl'
$pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($user + ':' + $pass))
$headers = @{ Authorization = "Basic $pair"; 'If-Match' = '*' }
$uri = 'https://ecommerce-mongo-h3gxh7cjfzgme2g9.scm.westus2-01.azurewebsites.net/api/vfs/site/wwwroot/startup.sh'
Invoke-RestMethod -Uri $uri -Method Put -InFile 'C:\Users\PCJuan\Desktop\sql_app_Ecomerce_orm\startup.sh' -Headers $headers -ContentType 'application/octet-stream'
Write-Output 'Uploaded startup.sh'