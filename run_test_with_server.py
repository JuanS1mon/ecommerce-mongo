#!/usr/bin/env python3
"""
Script para ejecutar el test HTTP inmediatamente despues de que el servidor este listo.
"""
import subprocess
import time
import sys
import os
import threading

def monitor_server(process):
    """Monitor the server process and print output in real-time"""
    while True:
        output = process.stdout.readline()
        if output:
            print(f"SERVER: {output.strip()}")
        error = process.stderr.readline()
        if error:
            print(f"SERVER ERROR: {error.strip()}")

        if process.poll() is not None:
            print(f"Server process ended with code: {process.poll()}")
            break

def main():
    # Cambiar al directorio del proyecto
    project_dir = r"c:\Users\PCJuan\Desktop\sql_app_Ecomerce_orm"
    os.chdir(project_dir)

    print("Iniciando servidor en background...")
    # Iniciar servidor en background
    server_process = subprocess.Popen([
        sys.executable, "main_fixed.py"
    ], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, universal_newlines=True)

    # Start monitoring thread
    monitor_thread = threading.Thread(target=monitor_server, args=(server_process,))
    monitor_thread.daemon = True
    monitor_thread.start()

    print("Esperando que el servidor se inicie...")
    time.sleep(2)  # Esperar menos tiempo

    # Verificar si el servidor sigue corriendo
    if server_process.poll() is None:
        print("Servidor parece estar corriendo. Ejecutando test...")

        # Ejecutar el test
        test_result = subprocess.run([
            sys.executable, "test_config_http.py"
        ], capture_output=True, text=True, timeout=30)

        print("\n=== RESULTADO DEL TEST ===")
        print("STDOUT:", test_result.stdout)
        print("STDERR:", test_result.stderr)
        print("Return code:", test_result.returncode)

        # Detener el servidor
        print("Deteniendo servidor...")
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
            print("Servidor detenido correctamente")
        except subprocess.TimeoutExpired:
            print("Forzando terminacion del servidor...")
            server_process.kill()

    else:
        print("Servidor se detuvo antes de ejecutar el test")
        stdout, stderr = server_process.communicate()
        print("Server STDOUT:", stdout)
        print("Server STDERR:", stderr)

    print("Script terminado")

if __name__ == "__main__":
    main()