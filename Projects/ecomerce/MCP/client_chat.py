"""
Cliente de chat para API e-commerce.
Simple chat web con FastAPI. Para WhatsApp, usar Twilio.
"""

from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import json
import requests
import asyncio
import os

API_BASE = "http://localhost:8000/api"  # URL del servidor API

app = FastAPI()
templates = Jinja2Templates(directory=os.path.dirname(__file__))  # Usar directorio del archivo

@app.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        response = await procesar_mensaje(data)
        await websocket.send_text(response)

async def procesar_mensaje(mensaje: str) -> str:
    """Procesa mensaje y llama a API."""
    msg = mensaje.lower()
    try:
        if "listar productos" in msg:
            resp = requests.get(f"{API_BASE}/productos")
            return resp.json() if resp.status_code == 200 else {"error": "Error al listar productos"}
        elif "buscar producto id" in msg:
            parts = msg.split()
            if len(parts) > 3:
                resp = requests.get(f"{API_BASE}/productos/{parts[3]}")
                return resp.json() if resp.status_code == 200 else {"error": "Producto no encontrado"}
        elif "verificar usuario" in msg:
            email = msg.split("verificar usuario ")[-1]
            resp = requests.get(f"{API_BASE}/usuarios/verificar", params={"email": email})
            return resp.json() if resp.status_code == 200 else {"error": "Error al verificar"}
        # Agregar más comandos
        return json.dumps({"respuesta": "Comando no reconocido"})
    except Exception as e:
        return json.dumps({"error": str(e)})

# Para WhatsApp: Integrar con Twilio
# from twilio.rest import Client
# client = Client(account_sid, auth_token)
# message = client.messages.create(body=response, from_='whatsapp:+1234567890', to='whatsapp:+0987654321')

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)