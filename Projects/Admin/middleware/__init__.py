"""
Middleware para el panel de administración
"""
from .admin_auth import require_admin

__all__ = ['require_admin']
