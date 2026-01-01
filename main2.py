"""Minimal FastAPI app for smoke testing on Azure
Provides a single route `/` that renders an HTML page with one document
from MongoDB (collection `sample`).
"""
import os
import asyncio
from typing import Optional
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from motor.motor_asyncio import AsyncIOMotorClient
import socket
import time
from typing import Dict, Any

# Template location
templates = Jinja2Templates(directory="./templates")

MONGO_URL = os.getenv("MONGO_URL")
DB_NAME = os.getenv("DB_NAME", "db_ecomerce")
# When SKIP_DB is truthy, skip any MongoDB access to allow fast HTTP checks in constrained environments
SKIP_DB = str(os.getenv("SKIP_DB", "false")).lower() in ("1", "true", "yes")

app = FastAPI(title="Minimal check app (main2)")

# Lazy-initialized Mongo client
_mongo_client: Optional[AsyncIOMotorClient] = None

async def get_mongo_client() -> AsyncIOMotorClient:
    global _mongo_client
    if _mongo_client is None:
        if not MONGO_URL:
            raise RuntimeError("MONGO_URL env var is not set")
        _mongo_client = AsyncIOMotorClient(MONGO_URL)
    return _mongo_client

@app.on_event("shutdown")
async def shutdown_db():
    global _mongo_client
    if _mongo_client:
        _mongo_client.close()
        _mongo_client = None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Render a simple page showing a sample document from `sample` collection.
    If SKIP_DB is true, return a simple static response and skip DB access."""
    # Fast path for debugging: skip DB entirely when SKIP_DB is enabled
    if SKIP_DB:
        from fastapi.responses import HTMLResponse
        return HTMLResponse("<html><body><h1>main2 OK (DB skipped)</h1></body></html>", status_code=200)

    sample = None
    try:
        client = await get_mongo_client()
        db = client[DB_NAME]
        coll = db.get_collection("sample")
        sample = await coll.find_one({})
        # If collection empty, insert a test doc and read it
        if not sample:
            res = await coll.insert_one({"name": "demo", "value": "hello from mongo"})
            sample = await coll.find_one({"_id": res.inserted_id})
    except Exception as e:
        # Keep sample as None; template will display an error message
        sample = {"error": str(e)}

    # Intentional fallback: if template missing or rendering fails, return a simple HTML response
    try:
        return templates.TemplateResponse("main2.html", {"request": request, "sample": sample})
    except Exception as tmpl_err:
        # Avoid leaking internals; show a short fallback page with the sample or error
        from fastapi.responses import HTMLResponse
        body = f"<html><body><h1>main2 fallback</h1><pre>{sample}</pre></body></html>"
        return HTMLResponse(body, status_code=200)

@app.get("/health")
async def health():
    """Simple health endpoint that always responds quickly and indicates whether DB access is skipped."""
    return {"status": "ok", "db_skipped": SKIP_DB}


@app.get("/probe_mongo_tcp")
async def probe_mongo_tcp() -> Dict[str, Any]:
    """Probe basic TCP connectivity to the Mongo host (tries common ports)."""
    if not MONGO_URL:
        return {"ok": False, "error": "MONGO_URL not set"}

    # Extract host from common connection string forms
    # e.g. mongodb+srv://user:pw@ecommerce-db.mongocluster.cosmos.azure.com/... or mongodb://host:port
    try:
        s = MONGO_URL
        # strip prefix
        if s.startswith("mongodb+srv://") or s.startswith("mongodb://"):
            s2 = s.split("@", 1)[-1]
        else:
            s2 = s
        hostpart = s2.split("/", 1)[0]
        # If auth info present (unlikely after split) remove it
        host = hostpart.split(",")[0]
        host = host.split(":")[0]
    except Exception as e:
        return {"ok": False, "error": f"parse_error: {e}"}

    ports_to_try = [10260, 27017]
    results = []
    for port in ports_to_try:
        t0 = time.time()
        try:
            sock = socket.create_connection((host, port), timeout=5)
            sock.close()
            elapsed = time.time() - t0
            results.append({"port": port, "reachable": True, "time_s": round(elapsed, 3)})
        except Exception as e:
            elapsed = time.time() - t0
            results.append({"port": port, "reachable": False, "time_s": round(elapsed, 3), "error": str(e)})

    return {"ok": True, "host": host, "probes": results}


@app.get("/probe_mongo_ping")
async def probe_mongo_ping() -> Dict[str, Any]:
    """Try a short pymongo ping using small serverSelectionTimeoutMS to avoid long blocks."""
    if not MONGO_URL:
        return {"ok": False, "error": "MONGO_URL not set"}

    try:
        from pymongo import MongoClient
    except Exception as e:
        return {"ok": False, "error": f"pymongo_import_error: {e}"}

    try:
        t0 = time.time()
        client = MongoClient(MONGO_URL, serverSelectionTimeoutMS=5000, connectTimeoutMS=5000)
        client.admin.command("ping")
        elapsed = time.time() - t0
        return {"ok": True, "time_s": round(elapsed, 3)}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@app.get("/probe_mongo_dns")
async def probe_mongo_dns() -> Dict[str, Any]:
    """Perform DNS SRV and A/AAAA lookups for the Mongo host."""
    if not MONGO_URL:
        return {"ok": False, "error": "MONGO_URL not set"}

    try:
        import dns.resolver
    except Exception as e:
        return {"ok": False, "error": f"dnspython_import_error: {e}"}

    try:
        s = MONGO_URL
        if s.startswith("mongodb+srv://") or s.startswith("mongodb://"):
            s2 = s.split("@", 1)[-1]
        else:
            s2 = s
        hostpart = s2.split("/", 1)[0]
        host = hostpart.split(",")[0]
        host = host.split(":")[0]
    except Exception as e:
        return {"ok": False, "error": f"parse_error: {e}"}

    result = {"ok": True, "host": host}

    # SRV lookup
    try:
        answers = dns.resolver.resolve(f"_mongodb._tcp.{host}", "SRV")
        srv = []
        for r in answers:
            srv.append({"target": r.target.to_text().rstrip("."), "priority": r.priority, "weight": r.weight, "port": r.port})
        result["srv"] = srv
    except Exception as e:
        result["srv_error"] = str(e)

    # A/AAAA lookup for host
    try:
        a_ans = dns.resolver.resolve(host, "A")
        result["A"] = [r.address for r in a_ans]
    except Exception as e:
        result["A_error"] = str(e)
    try:
        aaaa_ans = dns.resolver.resolve(host, "AAAA")
        result["AAAA"] = [r.address for r in aaaa_ans]
    except Exception as e:
        result["AAAA_error"] = str(e)

    # Resolve targets from SRV if any
    if "srv" in result:
        targets_info = {}
        for t in result["srv"]:
            tgt = t["target"]
            try:
                a = [r.address for r in dns.resolver.resolve(tgt, "A")]
            except Exception as e:
                a = f"error:{e}"
            try:
                aaaa = [r.address for r in dns.resolver.resolve(tgt, "AAAA")]
            except Exception as e:
                aaaa = f"error:{e}"
            targets_info[tgt] = {"A": a, "AAAA": aaaa}
        result["targets"] = targets_info

    return result


@app.get("/probe_mongo_srv_tcp")
async def probe_mongo_srv_tcp() -> Dict[str, Any]:
    """Resolve SRV targets and attempt TCP connect to each target:port."""
    dns_res = await probe_mongo_dns()
    if not dns_res.get("ok"):
        return {"ok": False, "error": "dns_lookup_failed", "details": dns_res}

    probes = []
    srv = dns_res.get("srv", [])

    # Prefer resolved A addresses for each SRV target when available
    if "targets" in dns_res:
        for tgt, info in dns_res["targets"].items():
            addrs = info.get("A") if isinstance(info.get("A"), list) else []
            port = next((s["port"] for s in srv if s["target"] == tgt), 10260)
            for addr in addrs:
                t0 = time.time()
                try:
                    sock = socket.create_connection((addr, port), timeout=5)
                    sock.close()
                    elapsed = time.time() - t0
                    probes.append({"target": tgt, "addr": addr, "port": port, "reachable": True, "time_s": round(elapsed, 3)})
                except Exception as e:
                    elapsed = time.time() - t0
                    probes.append({"target": tgt, "addr": addr, "port": port, "reachable": False, "time_s": round(elapsed, 3), "error": str(e)})
    else:
        for s in srv:
            tgt = s["target"]
            port = s["port"]
            t0 = time.time()
            try:
                sock = socket.create_connection((tgt, port), timeout=5)
                sock.close()
                elapsed = time.time() - t0
                probes.append({"target": tgt, "addr": tgt, "port": port, "reachable": True, "time_s": round(elapsed, 3)})
            except Exception as e:
                elapsed = time.time() - t0
                probes.append({"target": tgt, "addr": tgt, "port": port, "reachable": False, "time_s": round(elapsed, 3), "error": str(e)})

    return {"ok": True, "probes": probes, "dns": dns_res}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print("Starting main2 on port", port)
    uvicorn.run("main2:app", host="0.0.0.0", port=port, reload=False)
