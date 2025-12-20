"""Rutas de compatibilidad para alias y spellings mixtos.
Proporciona redirecciones rápidas para evitar 404 por diferencias
entre '/ecomerce' y '/ecommerce'."""
from fastapi import APIRouter
from fastapi.responses import RedirectResponse

router = APIRouter()


@router.get('/ecommerce/productos/tienda')
async def redirect_ecommerce_productos_tienda():
    return RedirectResponse(url='/ecomerce/productos/tienda', status_code=303)


@router.get('/ecommerce/productos/{rest:path}')
async def redirect_ecommerce_productos(rest: str):
    return RedirectResponse(url=f'/ecomerce/productos/{rest}', status_code=303)


@router.get('/ecommerce/login')
async def redirect_ecommerce_login():
    return RedirectResponse(url='/ecomerce/login', status_code=303)


@router.get('/ecommerce/register')
async def redirect_ecommerce_register():
    return RedirectResponse(url='/ecomerce/register', status_code=303)


@router.get('/ecommerce')
async def redirect_ecommerce_root():
    return RedirectResponse(url='/ecomerce', status_code=303)
