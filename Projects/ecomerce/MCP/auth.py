"""
Autenticación básica para MCP.
Reutiliza JWT de middleware.
"""

import jwt
from config import SECRET_KEY, ALGORITHM

def validar_token(token: str) -> str:
    """Valida JWT y retorna user_id si válido."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None