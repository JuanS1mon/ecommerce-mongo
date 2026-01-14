# routers/admin_auth.py
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import timedelta
from security.jwt_auth import create_access_token, verificar_clave
from models.models_beanie import AdminUsuarios
from beanie import PydanticObjectId
from jose import jwt, JWTError
from config import SECRET_KEY, ALGORITHM

router = APIRouter()

security = HTTPBearer()

class LoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def decode_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Token inválido")

async def get_current_admin_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    print(f"DEBUG: Verificando token de admin: {credentials.credentials[:20]}...")
    token = credentials.credentials
    payload = decode_token(token)
    print(f"DEBUG: Payload decodificado: {payload}")
    if payload.get("role") != "admin":
        print(f"DEBUG: Role incorrecto: {payload.get('role')}")
        raise HTTPException(status_code=403, detail="Acceso denegado")
    print("DEBUG: Token de admin válido")
    return payload

@router.post("/admin/login", response_model=TokenResponse)
async def login_admin(request: LoginRequest):
    # Buscar usuario por email
    usuario = await AdminUsuarios.find_one(AdminUsuarios.mail == request.email)
    if not usuario:
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
    
    # Verificar que esté activo
    if not usuario.activo:
        raise HTTPException(status_code=400, detail="Usuario inactivo")
    
    # Verificar contraseña
    if not verificar_clave(request.password, usuario.clave_hash):
        raise HTTPException(status_code=400, detail="Credenciales incorrectas")
    
    # Crear token con rol admin
    access_token_expires = timedelta(minutes=1440)  # 24 horas
    access_token = create_access_token(
        data={"sub": str(usuario.id), "role": "admin"},
        expires_delta=access_token_expires
    )
    
    return TokenResponse(access_token=access_token)