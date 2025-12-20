"""
Router de utilidades para mapas
"""
from fastapi import APIRouter
import httpx
import logging

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["mapas"],
    responses={404: {"message": "ruta no encontrada"}}
)

@router.get("/geocode")
async def geocode_address(q: str):
    """
    Endpoint para geocodificar direcciones usando Nominatim (OpenStreetMap).
    Evita problemas de CORS haciendo la request desde el servidor.
    """
    try:
        if not q or not q.strip():
            return {"error": "Dirección vacía"}

        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://nominatim.openstreetmap.org/search",
                params={
                    "format": "json",
                    "q": q,
                    "limit": 1
                },
                headers={
                    "User-Agent": "Ecommerce-Perfil/1.0 (https://github.com/JuanS1mon/nuevo-proyecto)"
                },
                timeout=10.0
            )

            if response.status_code == 200:
                data = response.json()
                if data:
                    return {
                        "lat": data[0]["lat"],
                        "lon": data[0]["lon"],
                        "display_name": data[0]["display_name"],
                        "type": data[0]["type"],
                        "importance": data[0]["importance"]
                    }
                else:
                    return {"error": "Dirección no encontrada"}
            else:
                logger.error(f"Error en Nominatim: {response.status_code} - {response.text}")
                return {"error": f"Error del servicio: {response.status_code}"}

    except httpx.TimeoutException:
        logger.error("Timeout en geocodificación")
        return {"error": "Timeout en la geocodificación"}
    except Exception as e:
        logger.error(f"Error en geocodificación: {e}")
        return {"error": f"Error interno: {str(e)}"}
