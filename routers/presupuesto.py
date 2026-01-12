# routers/presupuesto.py
from fastapi import APIRouter, HTTPException, Depends
from models.models_beanie import Presupuesto, Servicio
from security.jwt_auth import get_current_user
from pydantic import BaseModel
from typing import List

router = APIRouter()

class PresupuestoCreate(BaseModel):
    servicio_id: str
    descripcion: str
    precio_estimado: float

@router.post("/presupuestos")
async def crear_presupuesto(presupuesto: PresupuestoCreate, current_user: dict = Depends(get_current_user)):
    servicio = await Servicio.get(presupuesto.servicio_id)
    if not servicio:
        raise HTTPException(status_code=404, detail="Servicio no encontrado")
    
    nuevo_presupuesto = Presupuesto(
        usuario_id=current_user["user_id"],
        servicio_id=presupuesto.servicio_id,
        descripcion=presupuesto.descripcion,
        precio_estimado=presupuesto.precio_estimado
    )
    await nuevo_presupuesto.insert()
    return {"message": "Presupuesto solicitado"}

@router.get("/presupuestos", response_model=List[Presupuesto])
async def listar_presupuestos(current_user: dict = Depends(get_current_user)):
    presupuestos = await Presupuesto.find(Presupuesto.usuario_id == current_user["user_id"]).to_list()
    return presupuestos