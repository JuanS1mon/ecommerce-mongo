# exception_handlers.py
# =============================
# Manejadores de excepciones para FastAPI
# =============================

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import logging

logger = logging.getLogger(__name__)

def register_exception_handlers(app):
    """
    Registra todos los manejadores de excepciones en la aplicación FastAPI
    """

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Manejador para excepciones HTTP"""
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        """Manejador para errores de validación de Pydantic"""
        return JSONResponse(
            status_code=422,
            content={"detail": "Datos de entrada inválidos", "errors": exc.errors()}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        """Manejador para excepciones generales"""
        try:
            logger.error(f"Error no manejado: {str(exc)}", exc_info=True)
        except Exception as log_exc:
            print(f"Error en logging: {str(log_exc)}")
            print(f"Error original: {str(exc)}")
        return JSONResponse(
            status_code=500,
            content={"detail": "Error interno del servidor"}
        )

    logger.info("Manejadores de excepciones registrados")
