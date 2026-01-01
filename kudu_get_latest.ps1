$user = '$ecommerce-mongo'
$pass = '9AXTgHe2lZi1JntvPBBlZJl7h9qn7BjmHfyLx7oeS8brCwe7XdtDQkGoofwl'
$pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($user + ':' + $pass))
$headers = @{ Authorization = "Basic $pair" }
$uri = 'https://ecommerce-mongo-h3gxh7cjfzgme2g9.scm.westus2-01.azurewebsites.net/api/deployments/latest'

try {
  $result = Invoke-RestMethod -Uri $uri -Headers $headers -Method Get
  $result | Format-List id,status,received_time,deployer,complete,progress
} catch {
  Write-Output "Error calling Kudu deployments/latest: $_"
}
