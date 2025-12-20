from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, FileResponse
from utils.templates import templates
import logging
logger = logging.getLogger("main")

router = APIRouter()

@router.get("/debug-template", include_in_schema=False)
async def debug_template(request: Request):
    try:
        import os
        current_dir = os.getcwd()
        template_dir = templates.env.loader.searchpath
        static_path = "static/index.html"
        static_exists = os.path.exists(static_path)
        return JSONResponse({
            "current_directory": current_dir,
            "template_searchpath": template_dir,
            "static_file_path": static_path,
            "static_file_exists": static_exists,
            "available_files": os.listdir("static") if os.path.exists("static") else "Directory not found"
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)

@router.get("/index", response_class=HTMLResponse, include_in_schema=False)
async def read_index():
    try:    
        with open("static/index.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except Exception as e:
        logger.error(f"Error en index: {e}")
        # En caso de error, devolver mensaje de error
        return HTMLResponse(content=f"<h1>Error: {e}</h1>", status_code=500)

@router.get("/terminos", response_class=HTMLResponse, include_in_schema=False)
async def get_terminos():
    with open("static/terminos.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)

@router.get("/privacidad", response_class=HTMLResponse, include_in_schema=False)
async def get_privacidad():
    with open("static/privacidad.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)

@router.get("/registerpage", response_class=HTMLResponse, include_in_schema=False)
async def get_register_page():
    with open("static/register.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)

@router.get("/logintest", response_class=HTMLResponse, include_in_schema=False)
async def get_login_test():
    """Endpoint de prueba para verificar que el router funciona"""
    logger.info("🟢 TEST: Endpoint de prueba alcanzado exitosamente")
    return HTMLResponse(content="<h1>✅ TEST EXITOSO: El router static_pages funciona correctamente</h1>", status_code=200)

@router.get("/loginpage", response_class=HTMLResponse, include_in_schema=False)
async def get_ecommerce_login_page_simple():
    """Página de login para usuarios de ecommerce (ruta alternativa)"""
    try:
        with open("static/ecommerce_login.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página de login de ecommerce no encontrada</h1>", status_code=404)


@router.get("/login-simple", response_class=HTMLResponse, include_in_schema=False)
async def get_login_simple():
    with open("static/login.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)

@router.get("/test-interceptor", response_class=HTMLResponse, include_in_schema=False)
async def get_test_interceptor():
    with open("static/test-interceptor.html", "r", encoding="utf-8") as file:
        return HTMLResponse(content=file.read(), status_code=200)

@router.get("/ecomerce/register", response_class=HTMLResponse, include_in_schema=False)
async def get_ecommerce_register_page():
    """Página de registro para usuarios de ecommerce"""
    try:
        with open("static/ecommerce_register.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página de registro no encontrada</h1>", status_code=404)

@router.get("/ecomerce/login", response_class=HTMLResponse, include_in_schema=False)
async def get_ecommerce_login_page():
    """Página de login para usuarios de ecommerce"""
    try:
        with open("static/ecommerce_login.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página de login no encontrada</h1>", status_code=404)

@router.get("/checkout/mercadopago/test", response_class=HTMLResponse, include_in_schema=False)
async def get_checkout_mercadopago_test():
    """Página de checkout de prueba solo para MercadoPago"""
    try:
        with open("static/checkout_mercadopago_test.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página de checkout de prueba no encontrada</h1>", status_code=404)

@router.get("/checkout/success", response_class=HTMLResponse, include_in_schema=False)
async def get_checkout_success():
    """Página de resultado exitoso del checkout de MercadoPago"""
    try:
        with open("static/checkout_success.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página de éxito no encontrada</h1>", status_code=404)

@router.get("/checkout/failure", response_class=HTMLResponse, include_in_schema=False)
async def get_checkout_failure():
    """Página de resultado fallido del checkout de MercadoPago"""
    try:
        with open("static/checkout_failure.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página de error no encontrada</h1>", status_code=404)

@router.get("/checkout/pending", response_class=HTMLResponse, include_in_schema=False)
async def get_checkout_pending():
    """Página de resultado pendiente del checkout de MercadoPago"""
    try:
        with open("static/checkout_pending.html", "r", encoding="utf-8") as file:
            return HTMLResponse(content=file.read(), status_code=200)
    except FileNotFoundError:
        return HTMLResponse(content="<h1>Error: Página pendiente no encontrada</h1>", status_code=404)

@router.get("/ecomerce/perfil", response_class=HTMLResponse, include_in_schema=False)
async def get_perfil_page(request: Request):
    """Página de perfil de usuario con lista de deseos"""
    try:
        return templates.TemplateResponse("perfil.html", {"request": request})
    except Exception as e:
        logger.error(f"Error al cargar página de perfil: {e}")
        return HTMLResponse(content=f"<h1>Error al cargar perfil: {e}</h1>", status_code=500)

@router.get("/ecomerce/usuarios/perfil", response_class=HTMLResponse, include_in_schema=False)
async def get_usuario_perfil_page(request: Request):
    """Página de perfil de usuario (alternativa)"""
    try:
        return templates.TemplateResponse("perfil.html", {"request": request})
    except Exception as e:
        logger.error(f"Error al cargar página de perfil: {e}")
        return HTMLResponse(content=f"<h1>Error al cargar perfil: {e}</h1>", status_code=500)
