$user = '$ecommerce-mongo'
$pass = '9AXTgHe2lZi1JntvPBBlZJl7h9qn7BjmHfyLx7oeS8brCwe7XdtDQkGoofwl'
$pair = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes($user + ':' + $pass))
$headers = @{ Authorization = "Basic $pair"; 'Content-Type' = 'application/json' }
$uri = 'https://ecommerce-mongo-h3gxh7cjfzgme2g9.scm.westus2-01.azurewebsites.net/api/command'
$body = @{ command = 'bash -lc "python3 /home/site/wwwroot/ensure_uvicorn.py; /home/site/wwwroot/startup.sh"' } | ConvertTo-Json
$result = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body -TimeoutSec 600
Write-Output $result

# Check uvicorn
$body2 = @{ command = 'python3 -c "import uvicorn; print(\"uv:\", uvicorn.__version__)"' } | ConvertTo-Json
$result2 = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body2
Write-Output $result2

# List /tmp to find virtualenv
$body3 = @{ command = 'ls -la /tmp > /home/site/wwwroot/tmp_list.txt; ls -la /tmp | grep antenv || true' } | ConvertTo-Json
$result3 = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body3
Write-Output $result3

# Check importability of main
$body4 = @{ command = 'python3 -c "import importlib; print(importlib.util.find_spec(\"main\"))"' } | ConvertTo-Json
$result4 = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body4
Write-Output "result4.ExitCode: $($result4.ExitCode)"
Write-Output "result4.Output:"
Write-Output $result4.Output
Write-Output "result4.Error:"
Write-Output $result4.Error

# Try importing main to surface errors (with explicit site path)
$body5 = @{ command = 'python3 -c "import sys; sys.path.insert(0, \"/home/site/wwwroot\"); import main; print(\"IMPORT_OK\")"' } | ConvertTo-Json
$result5 = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body5
Write-Output "result5.ExitCode: $($result5.ExitCode)"
Write-Output "result5.Output:"
Write-Output $result5.Output
Write-Output "result5.Error:"
Write-Output $result5.Error
# Inspect environment and files
$body6 = @{ command = 'python3 -c "import sys, os; print(\"CWD:\", os.getcwd()); print(\"PATH0:\", sys.path[0:5]); print(\"LIST_ROOT:\", os.listdir(\"/home/site/wwwroot\")[0:40])"' } | ConvertTo-Json
$result6 = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body6
Write-Output "result6.ExitCode: $($result6.ExitCode)"
Write-Output "result6.Output:"
Write-Output $result6.Output
Write-Output "result6.Error:"
Write-Output $result6.Error

# List uvicorn/gunicorn processes
$body7 = @{ command = 'bash -lc "ps aux | egrep \"uvicorn|gunicorn\" || true"' } | ConvertTo-Json
$result7 = Invoke-RestMethod -Uri $uri -Method Post -Headers $headers -Body $body7
Write-Output "result7.ExitCode: $($result7.ExitCode)"
Write-Output "result7.Output:"
Write-Output $result7.Output
Write-Output "result7.Error:"
Write-Output $result7.Error
Write-Output 'Done'