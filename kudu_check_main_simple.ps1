$user = '$ecommerce-mongo'
$pass = '9AXTgHe2lZi1JntvPBBlZJl7h9qn7BjmHfyLx7oeS8brCwe7XdtDQkGoofwl'
$pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($user + ':' + $pass))
$headers = @{ Authorization = "Basic $pair"; 'Content-Type' = 'application/json' }
$uri = 'https://ecommerce-mongo-h3gxh7cjfzgme2g9.scm.westus2-01.azurewebsites.net/api/command'

function RunCmd($pycmd){
  $body = @{ command = "python3 -c \"$pycmd\"" } | ConvertTo-Json
  $result = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body -TimeoutSec 300
  Write-Output "Cmd: python3 -c \"$pycmd\""
  Write-Output "ExitCode: $($result.ExitCode)"
  Write-Output "Output:"
  Write-Output $result.Output
  Write-Output "Error:"
  Write-Output $result.Error
  Write-Output "----"
}

RunCmd "import importlib; print(importlib.util.find_spec('main'))"
RunCmd "import main; print('IMPORT_OK')"
