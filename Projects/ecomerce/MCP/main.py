"""
Main FastAPI app que monta el servidor MCP y el cliente de chat.
Ejecuta con: uvicorn Projects.ecomerce.MCP.main:app --host 0.0.0.0 --port 8000 --reload
"""

from fastapi import FastAPI
from .server import app as api_app
from .client_chat import app as chat_app

app = FastAPI(title="E-commerce MCP Main App", version="1.0.0")

# Montar el servidor API en /api
app.mount("/api", api_app)

# Montar el cliente de chat en / (raíz)
app.mount("/", chat_app)

@app.get("/health")
def health_check():
    return {"status": "MCP y Chat corriendo"}