"""
Utilidades para templates de Admin
Funciones helper para renderizar templates con variables comunes
"""
from fastapi.templating import Jinja2Templates
from fastapi import Request
from config import PROJECT_NAME

templates = Jinja2Templates(directory="Projects/Admin/templates")

def render_admin_template(
    template_name: str,
    request: Request,
    active_page: str = "",
    **kwargs
):
    """
    Renderiza un template de admin con variables comunes
    
    Args:
        template_name: Nombre del archivo de template
        request: Request de FastAPI
        active_page: Página activa para el menú de navegación
        **kwargs: Variables adicionales para el template
    
    Returns:
        TemplateResponse con todas las variables necesarias
    """
    context = {
        "request": request,
        "project_name": PROJECT_NAME,
        "active_page": active_page,
        **kwargs
    }
    
    return templates.TemplateResponse(template_name, context)
