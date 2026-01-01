"""
Router para la landing page del panel de administración
Página de inicio con enlaces al dashboard y login
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from Projects.Admin.utils.template_helpers import render_admin_template

router = APIRouter(prefix="/admin", tags=["Admin Landing"])


@router.get("/", response_class=HTMLResponse, name="admin_landing")
async def admin_landing(request: Request):
    """
    Landing page del panel de administración
    Muestra opciones para ir al dashboard o al login
    """
    return render_admin_template("index.html", request)
