"""
Router para rutas de SEO (sitemap, robots.txt, etc)
"""
from fastapi import APIRouter, Response
from fastapi.responses import FileResponse
import os
from datetime import datetime
from Projects.ecomerce.models.productos_beanie import EcomerceProductos
from Projects.ecomerce.models.categorias_beanie import EcomerceCategorias

router = APIRouter(
    tags=["seo"],
)

@router.get("/sitemap.xml", response_class=Response)
async def get_sitemap():
    """
    Genera el sitemap.xml dinámicamente
    Incluye páginas principales y todos los productos activos
    """
    try:
        # Obtener todos los productos activos
        productos = await EcomerceProductos.find({"active": True}).to_list()
        
        # Obtener todas las categorías activas
        categorias = await EcomerceCategorias.find({"active": True}).to_list()
        
        # Construir sitemap XML
        xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
        xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        
        # Página principal
        xml += '  <url>\n'
        xml += '    <loc>https://tu-sitio.com/</loc>\n'
        xml += f'    <lastmod>{datetime.now().isoformat()}</lastmod>\n'
        xml += '    <changefreq>daily</changefreq>\n'
        xml += '    <priority>1.0</priority>\n'
        xml += '  </url>\n'
        
        # Página de tienda
        xml += '  <url>\n'
        xml += '    <loc>https://tu-sitio.com/ecomerce/productos/tienda</loc>\n'
        xml += f'    <lastmod>{datetime.now().isoformat()}</lastmod>\n'
        xml += '    <changefreq>daily</changefreq>\n'
        xml += '    <priority>0.9</priority>\n'
        xml += '  </url>\n'
        
        # Categorías
        for categoria in categorias:
            xml += '  <url>\n'
            xml += f'    <loc>https://tu-sitio.com/ecomerce/productos/tienda?categoria={categoria.id}</loc>\n'
            xml += f'    <lastmod>{datetime.now().isoformat()}</lastmod>\n'
            xml += '    <changefreq>weekly</changefreq>\n'
            xml += '    <priority>0.8</priority>\n'
            xml += '  </url>\n'
        
        # Productos (máximo 50,000 para Google)
        for producto in productos[:50000]:
            xml += '  <url>\n'
            xml += f'    <loc>https://tu-sitio.com/ecomerce/productos/{producto.id}</loc>\n'
            xml += f'    <lastmod>{datetime.now().isoformat()}</lastmod>\n'
            xml += '    <changefreq>weekly</changefreq>\n'
            xml += '    <priority>0.7</priority>\n'
            xml += '  </url>\n'
        
        xml += '</urlset>'
        
        return Response(content=xml, media_type="application/xml")
    
    except Exception as e:
        print(f"Error generando sitemap: {e}")
        return Response(
            content='<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>',
            media_type="application/xml"
        )

@router.get("/sitemap-index.xml", response_class=Response)
async def get_sitemap_index():
    """
    Retorna índice de sitemaps
    """
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    xml += '  <sitemap>\n'
    xml += '    <loc>https://tu-sitio.com/sitemap.xml</loc>\n'
    xml += f'    <lastmod>{datetime.now().isoformat()}</lastmod>\n'
    xml += '  </sitemap>\n'
    xml += '</sitemapindex>'
    
    return Response(content=xml, media_type="application/xml")

@router.get("/robots.txt", response_class=Response)
async def get_robots_txt():
    """
    Retorna el archivo robots.txt
    """
    robots = """# Robots.txt - Configuración para bots de búsqueda
User-agent: *
Allow: /
Disallow: /admin
Disallow: /api/admin
Disallow: /private
Allow: /ecomerce/productos/tienda
Allow: /ecomerce/api/productos/publicos
Allow: /ecomerce/api/categorias/publicas
Allow: /*.js
Allow: /*.css

# Google Bot
User-agent: Googlebot
Allow: /
Disallow: /admin
Crawl-delay: 0

# Bing Bot
User-agent: Bingbot
Allow: /
Disallow: /admin
Crawl-delay: 1

# Yahoo Bot
User-agent: Slurp
Allow: /
Disallow: /admin
Crawl-delay: 1

# Sitemap location
Sitemap: https://tu-sitio.com/sitemap.xml
Sitemap: https://tu-sitio.com/sitemap-index.xml

# Rate limit
Request-rate: 1/s
"""
    return Response(content=robots, media_type="text/plain")

@router.get("/.well-known/security.txt", response_class=Response)
async def get_security_txt():
    """
    Archivo de seguridad para divulgar vulnerabilidades
    """
    security = """Contact: security@tu-sitio.com
Expires: 2026-12-20T00:00:00.000Z
Preferred-Languages: es, en
"""
    return Response(content=security, media_type="text/plain")
