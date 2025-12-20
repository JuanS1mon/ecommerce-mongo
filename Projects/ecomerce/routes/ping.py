"""
Endpoint ping protegido con contraseña 1231
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from passlib.context import CryptContext

router = APIRouter()

class PingRequest(BaseModel):
    password: str

@router.post("/ping")
async def ping_protected(request: PingRequest):
    """Endpoint ping protegido con contraseña"""
    # Verificar contraseña
    if request.password != "1231":
        raise HTTPException(status_code=401, detail="Contraseña incorrecta")
    
    return {
        "status": "ok",
        "message": "Sistema funcionando correctamente",
        "authenticated": True,
        "ping": "pong"
    }

@router.get("/ping/status")
async def ping_status():
    """Endpoint público para verificar estado"""
    return {
        "status": "online",
        "service": "Sistema de autenticación",
        "version": "1.0.0"
    }
