$user = '$ecommerce-mongo'
$pass = '9AXTgHe2lZi1JntvPBBlZJl7h9qn7BjmHfyLx7oeS8brCwe7XdtDQkGoofwl'
$pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($user + ':' + $pass))
$headers = @{ Authorization = "Basic $pair"; 'Content-Type' = 'application/json' }
$uri = 'https://ecommerce-mongo-h3gxh7cjfzgme2g9.scm.westus2-01.azurewebsites.net/api/command'
$cmd = 'python3 -c "import importlib, sys, traceback; spec=importlib.util.find_spec(\"main\"); print(\"spec:\", spec);\ntry:\n import main\n print(\"main OK\")\nexcept Exception as e:\n print(\"main IMPORT ERROR:\", e)\n traceback.print_exc()"'
$body = @{ command = $cmd } | ConvertTo-Json
$result = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body -TimeoutSec 300
Write-Output "ExitCode: $($result.ExitCode)"
Write-Output "Output:"
Write-Output $result.Output
Write-Output "Error:"
Write-Output $result.Error
Write-Output 'Done'