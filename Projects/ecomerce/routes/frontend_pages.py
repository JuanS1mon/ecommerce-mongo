from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

router = APIRouter(
    prefix="",
    tags=["Frontend"],
    include_in_schema=False
)

templates = Jinja2Templates(directory="Projects/ecomerce/templates")

@router.get("/login", response_class=HTMLResponse)
async def login_page():
    """Página de login simplificada sin interferencias JS"""
    try:
        with open("static/login_simple.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        # Fallback al login original si no existe el simplificado
        try:
            with open("static/login.html", "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        except FileNotFoundError:
            return HTMLResponse("""
            <html><body>
            <h1>Login no encontrado</h1>
            <p>Los archivos de login no están disponibles</p>
            </body></html>
            """, status_code=404)

@router.get("/admin-dashboard.html", response_class=HTMLResponse)
async def admin_dashboard_page():
    """Carga segura del panel de administración con autenticación AJAX"""
    try:
        with open("admin-loader.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Error</h1>
        <p>El cargador del panel de administración no está disponible</p>
        <a href="/loginpage">Ir al login</a>
        </body></html>
        """, status_code=404)

@router.get("/test-auth-direct.html", response_class=HTMLResponse)
async def test_auth_direct():
    """Página de prueba directa de autenticación"""
    try:
        with open("test-auth-direct.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Error</h1>
        <p>La página de prueba no está disponible</p>
        </body></html>
        """, status_code=404)

@router.get("/ejemplo-cart", response_class=HTMLResponse)
async def ejemplo_cart_page():
    """Página de ejemplo para probar botones de carrito"""
    try:
        with open("static/ejemplo_cart_buttons.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Error</h1>
        <p>La página de ejemplo no está disponible</p>
        </body></html>
        """, status_code=404)

@router.get("/ecomerce/carrito", response_class=HTMLResponse)
async def carrito_page(request: Request):
    """Página completa del carrito de compras"""
    return templates.TemplateResponse("carrito.html", {"request": request})

@router.get("/static/servicio_al_cliente.html", response_class=HTMLResponse)
async def servicio_al_cliente_page():
    """Página de Servicio al Cliente"""
    try:
        with open("static/servicio_al_cliente.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Error</h1>
        <p>La página de Servicio al Cliente no está disponible</p>
        <a href="/">Volver al inicio</a>
        </body></html>
        """, status_code=404)

@router.get("/static/centro_de_ayuda.html", response_class=HTMLResponse)
async def centro_de_ayuda_page():
    """Página del Centro de Ayuda"""
    try:
        with open("static/centro_de_ayuda.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Error</h1>
        <p>La página del Centro de Ayuda no está disponible</p>
        <a href="/">Volver al inicio</a>
        </body></html>
        """, status_code=404)

@router.get("/static/envios_devoluciones.html", response_class=HTMLResponse)
async def envios_devoluciones_page():
    """Página de Envíos y Devoluciones"""
    try:
        with open("static/envios_devoluciones.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Error</h1>
        <p>La página de Envíos y Devoluciones no está disponible</p>
        <a href="/">Volver al inicio</a>
        </body></html>
        """, status_code=404)

@router.get("/ecomerce/checkout", response_class=HTMLResponse)
async def checkout_page():
    """Página de checkout del ecommerce"""
    try:
        with open("static/checkout.html", "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse("""
        <html><body>
        <h1>Error</h1>
        <p>La página de checkout no está disponible</p>
        <a href="/ecomerce/productos/tienda">Ir a la tienda</a>
        </body></html>
        """, status_code=404)


@router.get("/ecomerce/productos/tienda", response_class=HTMLResponse)
async def productos_tienda_page(request: Request):
    """Página pública de la tienda renderizada con Jinja2"""
    return templates.TemplateResponse("productos_tienda.html", {"request": request})

@router.get("/ecomerce/productos/{producto_id}", response_class=HTMLResponse)
async def producto_detalle_page(request: Request, producto_id: str):
    """Página de detalle de producto"""
    return templates.TemplateResponse(
        "producto_detalle.html",
        {
            "request": request,
            "producto_id": producto_id,
        },
    )
