@echo off
echo Iniciando servidor...
start /B python main.py
timeout /t 5 /nobreak > nul
echo Ejecutando pruebas...
python test_password_reset.py
echo Pruebas completadas.
pause