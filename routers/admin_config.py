# routers/admin_config.py
from fastapi import APIRouter, HTTPException
from models.models_beanie import Configuracion
from pydantic import BaseModel
from typing import Dict, Any
import json
from datetime import datetime

router = APIRouter()

class IndexSectionsUpdate(BaseModel):
    index_sections: str  # JSON string

@router.get("/admin/config")
async def get_config():
    try:
        config = {}
        configs = await Configuracion.find_all().to_list()
        print(f"[DEBUG] Found {len(configs)} config entries")
        for c in configs:
            print(f"[DEBUG] Config entry: {c.key} = {c.value} (type: {type(c.value)})")
            # Convertir a string si no lo es
            if not isinstance(c.value, str):
                print(f"[WARNING] Converting {c.key} from {type(c.value)} to string")
                c.value = str(c.value)
                await c.save()
            config[c.key] = c.value
        return config
    except Exception as e:
        print(f"Error in get_config: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/config")
async def update_config(data: Dict[str, Any]):
    try:
        print(f"[DEBUG] Updating config with data: {list(data.keys())}")
        for key, value in data.items():
            # Convertir a string si no lo es
            if not isinstance(value, str):
                print(f"[WARNING] Converting {key} from {type(value)} to string")
                value = str(value)
            print(f"[DEBUG] Processing key: {key}, value: {value}")
            existing = await Configuracion.find_one(Configuracion.key == key)
            if existing:
                existing.value = value
                existing.updated_at = datetime.utcnow()
                await existing.save()
                print(f"[DEBUG] Updated existing config: {key}")
            else:
                new_config = Configuracion(key=key, value=value)
                await new_config.insert()
                print(f"[DEBUG] Created new config: {key}")
        return {"message": "Configuración actualizada"}
    except Exception as e:
        print(f"Error in update_config: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/index/sections")
async def get_index_sections():
    try:
        config = await Configuracion.find_one(Configuracion.key == "index_sections")
        print(f"[DEBUG] get_index_sections: config found = {config is not None}")
        if config:
            print(f"[DEBUG] get_index_sections: config.value = {config.value[:200]}...")
            try:
                result = json.loads(config.value)
                print(f"[DEBUG] get_index_sections: parsed successfully, keys = {list(result.keys())}")
                return result
            except Exception as parse_error:
                print(f"[DEBUG] get_index_sections: parse error = {parse_error}")
                return {}
        print("[DEBUG] get_index_sections: no config found, returning empty dict")
        return {}
    except Exception as e:
        print(f"Error in get_index_sections: {e}")
        return {}