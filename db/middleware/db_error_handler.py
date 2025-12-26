# Imports de bibliotecas estándar
from starlette.middleware.base import BaseHTTPMiddleware
import logging
try:
    import pyodbc
    PYODBC_AVAILABLE = True
except ImportError:
    PYODBC_AVAILABLE = False
    pyodbc = None
try:
    from sqlalchemy.exc import SQLAlchemyError
    SQLALCHEMY_AVAILABLE = True
except ImportError:
    SQLAlchemyError = Exception  # Fallback
    SQLALCHEMY_AVAILABLE = False
import re
import traceback

# Imports de terceros
from fastapi import Request, Response
from fastapi.responses import JSONResponse, HTMLResponse

logger = logging.getLogger(__name__)

class DBErrorMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            # Intenta procesar la solicitud normalmente
            return await call_next(request)
        except Exception as e:
            # Captura la excepción y verifica si es un error de columna de SQL Server
            if (SQLALCHEMY_AVAILABLE and isinstance(e, SQLAlchemyError)) or (PYODBC_AVAILABLE and isinstance(e, pyodbc.Error)):
                error_msg = str(e)
                
                # Patrones para detectar errores de columna
                column_error_pattern = r"El nombre de columna '([^']+)' no es válido"
                object_not_found_pattern = r"Invalid object name '([^']+)'"
                
                # Verificar si es un error de columna
                column_match = re.search(column_error_pattern, error_msg)
                object_match = re.search(object_not_found_pattern, error_msg)
                
                if column_match or object_match:
                    # Log del error original para diagnóstico
                    logger.error(f"Error de base de datos: {error_msg}")
                    
                    # Construir un mensaje amigable
                    if column_match:
                        column_name = column_match.group(1)
                        friendly_message = f"La columna '{column_name}' no existe en la base de datos."
                    elif object_match:
                        table_name = object_match.group(1)
                        friendly_message = f"La tabla '{table_name}' no existe en la base de datos."
                    
                    # Determinar el formato de respuesta basado en la solicitud
                    accept_header = request.headers.get("accept", "")
                    
                    if "application/json" in accept_header or request.url.path.startswith("/api/"):
                        # Respuesta JSON para API
                        return JSONResponse(
                            status_code=500,
                            content={
                                "detail": "Error de estructura de base de datos",
                                "message": friendly_message,
                                "solution": "Es necesario actualizar la estructura de la base de datos o reiniciar la aplicación."
                            }
                        )
                    else:
                        # Respuesta HTML para solicitudes web
                        html_content = f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>Error de Base de Datos</title>
                            <style>
                                body {{
                                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                                    background-color: #f5f5f5;
                                    margin: 0;
                                    padding: 20px;
                                    color: #333;
                                }}
                                .container {{
                                    max-width: 800px;
                                    margin: 40px auto;
                                    background-color: white;
                                    padding: 30px;
                                    border-radius: 8px;
                                    box-shadow: 0 2px 15px rgba(0,0,0,0.1);
                                }}
                                .error-icon {{
                                    color: #e74c3c;
                                    font-size: 48px;
                                    margin-bottom: 20px;
                                    text-align: center;
                                }}
                                h1 {{
                                    color: #e74c3c;
                                    margin-bottom: 20px;
                                    padding-bottom: 10px;
                                    border-bottom: 1px solid #eee;
                                }}
                                .message {{
                                    background-color: #fff8e1;
                                    border-left: 5px solid #ffc107;
                                    padding: 15px;
                                    margin-bottom: 20px;
                                }}
                                .solution {{
                                    background-color: #e8f5e9;
                                    border-left: 5px solid #4caf50;
                                    padding: 15px;
                                    margin-bottom: 20px;
                                }}
                                .details {{
                                    background-color: #f8f9fa;
                                    padding: 15px;
                                    border-radius: 4px;
                                    font-family: monospace;
                                    font-size: 14px;
                                    overflow-x: auto;
                                }}
                                .button {{
                                    display: inline-block;
                                    padding: 10px 20px;
                                    background-color: #3498db;
                                    color: white;
                                    text-decoration: none;
                                    border-radius: 4px;
                                    margin-top: 20px;
                                }}
                                .button:hover {{
                                    background-color: #2980b9;
                                }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="error-icon">⚠️</div>
                                <h1>Error de Base de Datos</h1>
                                <div class="message">
                                    <strong>Problema detectado:</strong> {friendly_message}
                                </div>
                                <div class="solution">
                                    <strong>Solución:</strong> Es necesario actualizar la estructura de la base de datos o reiniciar la aplicación.
                                    <ul>
                                        <li>Ejecute el script de actualización de base de datos</li>
                                        <li>Reinicie la aplicación después de la actualización</li>
                                        <li>Si el problema persiste, contacte al administrador del sistema</li>
                                    </ul>
                                </div>
                                <div class="details">
                                    <strong>Detalles técnicos:</strong><br>
                                    {error_msg}
                                </div>
                                <a href="/" class="button">Volver al inicio</a>
                            </div>
                        </body>
                        </html>
                        """
                        return HTMLResponse(content=html_content, status_code=500)
            
            # Para otros errores, registrar y reenviar la excepción original
            logger.error(f"Error no manejado: {str(e)}")
            raise e
