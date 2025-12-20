# routers/config/__init__.py
# Archivo de inicialización para el paquete routers.config

# Importar solo módulos que no requieren dependencias opcionales
from . import (
    Admin,
    AdminNew,
    Analisis,
    configDB,
    usuarios_admin
)

# Importar módulos con dependencias opcionales de forma condicional
try:
    from . import MigracionesBD
    _migraciones_bd_available = True
except ImportError:
    _migraciones_bd_available = False

try:
    from . import MigracionesArchivosGrandes
    _migraciones_grandes_available = True
except ImportError:
    _migraciones_grandes_available = False

__all__ = [
    'Admin',
    'AdminNew',
    'Analisis',
    'usuarios_admin'
]

# Agregar los opcionales si están disponibles
if _migraciones_bd_available:
    __all__.append('MigracionesBD')

if _migraciones_grandes_available:
    __all__.append('MigracionesArchivosGrandes')
