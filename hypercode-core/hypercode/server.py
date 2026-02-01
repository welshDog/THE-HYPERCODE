from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
import time
import uuid
import hashlib
import os
from sqlalchemy import create_engine, text
from alembic.config import Config as AlembicConfig
from alembic import command as alembic_command
from celery import Celery
import redis
from .worker import app as celery_app, queue_depth
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

from hypercode.compiler import compile_flow
from hypercode.simulator import simulate_flow, simulate_flow_generator

app = FastAPI(title="HyperCode Backend API")

IDEMPOTENCY_STORE: Dict[str, Dict[str, Any]] = {}
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 10
REQUEST_TIMES: Dict[str, List[float]] = {}
RUNS: Dict[str, Dict[str, Any]] = {}
CACHE_STATS: Dict[str, Dict[str, int]] = {"dev": {"hit": 0, "miss": 0}, "staging": {"hit": 0, "miss": 0}, "prod": {"hit": 0, "miss": 0}}
JWT_ALG = "HS256"
JWT_SECRET = os.getenv("HYPERCODE_JWT_SECRET", "")

HTTP_REQUESTS = Counter("http_requests_total", "Total HTTP requests", ["method", "path", "status"])
HTTP_ERRORS = Counter("http_errors_total", "Total HTTP errors", ["path", "status"])
HTTP_DURATION = Histogram("http_request_duration_seconds", "Request duration seconds", ["method", "path"])

def now() -> float:
    return time.time()

def flow_hash(flow: Dict[str, Any]) -> str:
    payload = json.dumps(flow, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def get_request_id(req: Request) -> str:
    hdr = req.headers.get("x-request-id")
    return hdr if hdr else str(uuid.uuid4())

def check_rate_limit(ip: str) -> bool:
    ts_list = REQUEST_TIMES.get(ip, [])
    cutoff = now() - RATE_LIMIT_WINDOW_SECONDS
    ts_list = [ts for ts in ts_list if ts >= cutoff]
    REQUEST_TIMES[ip] = ts_list
    if len(ts_list) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    ts_list.append(now())
    REQUEST_TIMES[ip] = ts_list
    return True

def decode_jwt(token: str) -> Dict[str, Any]:
    try:
        import jwt
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG]) if JWT_SECRET else jwt.decode(token, options={"verify_signature": False})
    except Exception:
        return {}

def require_scopes(required: List[str]):
    async def dependency(request: Request) -> None:
        auth = request.headers.get("authorization") or request.headers.get("Authorization")
        if not auth or not auth.lower().startswith("bearer "):
            raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing bearer token"})
        token = auth.split(" ", 1)[1]
        claims = decode_jwt(token)
        scopes: List[str] = claims.get("scopes", []) if isinstance(claims.get("scopes", []), list) else []
        for s in required:
            if s not in scopes:
                raise HTTPException(status_code=403, detail={"code": "FORBIDDEN", "message": "Insufficient scope", "required": required})
    return dependency

class CacheManager:
    def __init__(self):
        self.env = os.getenv("HYPERCODE_ENV", "dev")
        self._mem: Dict[str, Any] = {}
        self._redis = None
        url = os.getenv("HYPERCODE_REDIS_URL")
        if url:
            try:
                self._redis = redis.Redis.from_url(url)
            except Exception:
                self._redis = None

    def get(self, key: str) -> Any:
        if self._redis:
            val = self._redis.get(f"cache:{self.env}:{key}")
            hit = 1 if val is not None else 0
        else:
            val = self._mem.get(key)
            hit = 1 if key in self._mem else 0
        if hit:
            CACHE_STATS[self.env]["hit"] += 1
        else:
            CACHE_STATS[self.env]["miss"] += 1
        return json.loads(val) if isinstance(val, (bytes, bytearray)) else val

    def set(self, key: str, value: Any) -> None:
        if self._redis:
            self._redis.set(f"cache:{self.env}:{key}", json.dumps(value))
        else:
            self._mem[key] = value

    def invalidate_stage(self, stage: str) -> None:
        if self._redis:
            for k in self._redis.scan_iter(f"cache:{stage}:*"):
                self._redis.delete(k)
        else:
            if stage == self.env:
                self._mem.clear()

    def warm(self, keys: List[str]) -> None:
        for k in keys:
            self.set(k, {"warmed": True, "ts": int(time.time()*1000)})

CACHE = CacheManager()

def check_db() -> bool:
    try:
        db_url = os.getenv("HYPERCODE_DB_URL")
        if not db_url:
            return False
        engine = create_engine(db_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False

def check_redis() -> bool:
    try:
        url = os.getenv("HYPERCODE_REDIS_URL")
        if not url:
            return False
        r = redis.Redis.from_url(url)
        return r.ping()
    except Exception:
        return False

def check_ready() -> Dict[str, Any]:
    deps = {
        "db": check_db(),
        "redis": check_redis(),
        "jwt_secret": bool(JWT_SECRET),
    }
    status = "ready" if all(deps.values()) else "degraded"
    code = 200 if status == "ready" else 503
    return {"status": status, "deps": deps, "code": code}

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5174", "http://127.0.0.1:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FlowRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    viewport: Optional[Dict[str, Any]] = None

class CompileResponse(BaseModel):
    success: bool
    code: str
    simulation: Dict[str, Any]
    message: str
    runId: str
    requestId: str

class ErrorResponse(BaseModel):
    error: Dict[str, Any]
    requestId: str

@app.get("/")
async def root() -> Dict[str, Any]:
    return {"message": "HyperCode Backend Online", "status": "ready"}

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    return {"status": "ok", "services": {"compiler": "ok", "simulator": "ok"}}

@app.get("/ready")
async def ready() -> Any:
    res = check_ready()
    from fastapi import Response
    return Response(content=json.dumps({"status": res["status"], "deps": res["deps"]}), media_type="application/json", status_code=res["code"])

@app.get("/metrics")
async def metrics() -> Any:
    from fastapi import Response
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

@app.get("/celery/health")
async def celery_health() -> Dict[str, Any]:
    import time
    import os
    import redis as _redis
    r = _redis.Redis.from_url(os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0"))
    names: List[str] = []
    for k in r.scan_iter("celery:worker:*:success"):
        try:
            names.append(k.decode().split(":")[2])
        except Exception:
            pass
    pipe = r.pipeline()
    for name in names:
        pipe.get(f"celery:worker:{name}:last_task_ts")
        pipe.get(f"celery:worker:{name}:success")
        pipe.get(f"celery:worker:{name}:failure")
        pipe.get(f"celery:worker:{name}:retries")
    vals = pipe.execute() if names else []
    workers: List[Dict[str, Any]] = []
    now = int(time.time())
    i = 0
    for name in names:
        last = int(vals[i] or 0); i += 1
        success = int(vals[i] or 0); i += 1
        failure = int(vals[i] or 0); i += 1
        retries = int(vals[i] or 0); i += 1
        workers.append({"name": name, "success": success, "failure": failure, "retries": retries, "last_task_ts": last})
    cpipe = r.pipeline()
    cpipe.get("celery:cluster_total:success")
    cpipe.get("celery:cluster_total:failure")
    cpipe.get("celery:cluster_total:retries")
    cvals = cpipe.execute()
    cluster_total = {"success": int(cvals[0] or 0), "failure": int(cvals[1] or 0), "retries": int(cvals[2] or 0)}
    code = 200 if (not workers or all((now - w["last_task_ts"]) <= 60 for w in workers)) else 503
    from fastapi import Response
    return Response(content=json.dumps({"workers": workers, "cluster_total": cluster_total}), media_type="application/json", status_code=code)

# --- Simple Workflows Storage ---
WORKFLOWS: Dict[str, Dict[str, Any]] = {}

@app.get("/workflows")
async def list_workflows(_: None = Depends(require_scopes(["workflows:read"]))) -> Dict[str, Any]:
    start = time.time()
    items = list(WORKFLOWS.values())
    dur = time.time() - start
    HTTP_DURATION.labels(method="GET", path="/workflows").observe(dur)
    HTTP_REQUESTS.labels(method="GET", path="/workflows", status="200").inc()
    return {"items": items}

class Workflow(BaseModel):
    id: Optional[str] = None
    name: str
    flow: Dict[str, Any]

@app.post("/workflows", status_code=201)
async def create_workflow(wf: Workflow, _: None = Depends(require_scopes(["workflows:write"]))) -> Dict[str, Any]:
    start = time.time()
    wf_id = wf.id or str(uuid.uuid4())
    payload = {"id": wf_id, "name": wf.name, "flow": wf.flow}
    WORKFLOWS[wf_id] = payload
    dur = time.time() - start
    HTTP_DURATION.labels(method="POST", path="/workflows").observe(dur)
    HTTP_REQUESTS.labels(method="POST", path="/workflows", status="201").inc()
    return payload

AUDIT_KEY = "audit:admin"

def record_admin_audit(action: str, details: Dict[str, Any]) -> None:
    try:
        r = redis.Redis.from_url(os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0"))
        item = {"ts": int(time.time()*1000), "action": action, "details": details}
        r.lpush(AUDIT_KEY, json.dumps(item))
        r.ltrim(AUDIT_KEY, 0, 1000)
    except Exception:
        pass

@app.get("/admin/audit/logs")
async def admin_audit_logs(_: None = Depends(require_scopes(["admin:read"]))) -> Dict[str, Any]:
    try:
        r = redis.Redis.from_url(os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0"))
        raw = r.lrange(AUDIT_KEY, 0, 100)
        items = [json.loads(x.decode()) for x in raw]
        return {"items": items}
    except Exception:
        return {"items": []}

@app.delete("/admin/workflows/{wf_id}")
async def admin_delete_workflow(wf_id: str, _: None = Depends(require_scopes(["admin:delete"]))) -> Dict[str, Any]:
    deleted = WORKFLOWS.pop(wf_id, None)
    record_admin_audit("workflows.delete", {"id": wf_id, "deleted": bool(deleted)})
    if not deleted:
        from fastapi import Response
        return Response(content=json.dumps({"deleted": False}), media_type="application/json", status_code=404)
    return {"deleted": True}

@app.get("/runs/{run_id}")
async def get_run(run_id: str, _: None = Depends(require_scopes(["runs:read"]))) -> Dict[str, Any]:
    start = time.time()
    r = RUNS.get(run_id)
    if not r:
        HTTP_ERRORS.labels(path="/runs/{run_id}", status="404").inc()
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Run not found"})
    dur = time.time() - start
    HTTP_DURATION.labels(method="GET", path="/runs/{run_id}").observe(dur)
    HTTP_REQUESTS.labels(method="GET", path="/runs/{run_id}", status="200").inc()
    return r

@app.post("/compile", response_model=CompileResponse)
async def compile_endpoint(flow: FlowRequest, request: Request, _: None = Depends(require_scopes(["compile:write"]))) -> Dict[str, Any]:
    """
    Compiles a Visual Flow into HyperCode source text.
    """
    try:
        start = time.time()
        client_ip = request.client.host if request.client else "unknown"
        if not check_rate_limit(client_ip):
            req_id = get_request_id(request)
            raise HTTPException(status_code=429, detail={
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests",
                "requestId": req_id
            })

        request_id = get_request_id(request)
        idem_key = request.headers.get("x-idempotency-key")

        if idem_key and idem_key in IDEMPOTENCY_STORE:
            cached = IDEMPOTENCY_STORE[idem_key]
            cached["requestId"] = request_id
            return cached

        # Convert Pydantic model to dict
        flow_data = flow.model_dump()
        run_id = flow_hash(flow_data)
        
        # Generate Code
        source_code = compile_flow(flow_data)
        
        # Run Simulation
        simulation_results = simulate_flow(flow_data)
        
        resp = {
            "success": True,
            "code": source_code,
            "simulation": simulation_results,
            "message": "Compilation and Simulation successful",
            "runId": run_id,
            "requestId": request_id
        }
        RUNS[run_id] = {"status": "succeeded", "code": source_code, "simulation": simulation_results}
        if idem_key:
            IDEMPOTENCY_STORE[idem_key] = resp
        dur = time.time() - start
        HTTP_DURATION.labels(method="POST", path="/compile").observe(dur)
        HTTP_REQUESTS.labels(method="POST", path="/compile", status="200").inc()
        return resp
    except HTTPException:
        raise
    except Exception as e:
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        HTTP_ERRORS.labels(path="/compile", status="500").inc()
        raise HTTPException(status_code=500, detail={
            "code": "COMPILER_ERROR",
            "message": str(e),
            "requestId": req_id
        }) from e

@app.post("/cache/warm")
async def cache_warm(body: Dict[str, Any], _: None = Depends(require_scopes(["cache:warm"]))) -> Dict[str, Any]:
    keys = body.get("keys", [])
    CACHE.warm(keys)
    return {"warmed": keys}

@app.get("/cache/metrics")
async def cache_metrics() -> Dict[str, Any]:
    info: Dict[str, Any] = {}
    try:
        if CACHE._redis:
            mi = CACHE._redis.info(section="memory")
            info = {"used_memory": mi.get("used_memory", 0)}
    except Exception:
        info = {}
    return {"stats": CACHE_STATS, "memory": info}

@app.post("/auth/refresh")
async def auth_refresh(request: Request) -> Dict[str, Any]:
    auth = request.headers.get("authorization") or request.headers.get("Authorization")
    if not auth or not auth.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED", "message": "Missing bearer token"})
    token = auth.split(" ", 1)[1]
    claims = decode_jwt(token)
    try:
        import jwt
        if not JWT_SECRET:
            raise HTTPException(status_code=500, detail={"code": "JWT_SECRET_MISSING", "message": "Server misconfigured"})
        new = jwt.encode({"sub": claims.get("sub"), "scopes": claims.get("scopes", []), "ts": int(time.time())}, JWT_SECRET, algorithm=JWT_ALG)
        return {"token": new}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"code": "TOKEN_REFRESH_ERROR", "message": str(e)})

DEPLOY_HISTORY_KEY = "deploy:history"

@app.get("/metrics/deployments")
async def deployment_metrics() -> Dict[str, Any]:
    history: List[Dict[str, Any]] = []
    r = None
    try:
        r = redis.Redis.from_url(os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0"))
        raw = r.get(DEPLOY_HISTORY_KEY)
        history = json.loads(raw.decode()) if raw else []
    except Exception:
        history = []
    total = len(history)
    successes = sum(1 for h in history if h.get("success"))
    failures = total - successes
    avg_ms = int(sum(h.get("duration_ms", 0) for h in history) / total) if total else 0
    reasons: Dict[str, int] = {}
    for h in history:
        if not h.get("success"):
            reasons[h.get("reason", "unknown")] = reasons.get(h.get("reason", "unknown"), 0) + 1
    return {"total": total, "success_rate": (successes / total) if total else 0.0, "avg_duration_ms": avg_ms, "failure_reasons": reasons}

@app.post("/metrics/deployments/push")
async def deployment_metrics_push(body: Dict[str, Any]) -> Dict[str, Any]:
    item = {
        "ts": int(time.time()*1000),
        "duration_ms": int(body.get("duration_ms", 0)),
        "success": bool(body.get("success", False)),
        "reason": body.get("reason", "")
    }
    try:
        r = redis.Redis.from_url(os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0"))
        raw = r.get(DEPLOY_HISTORY_KEY)
        history = json.loads(raw.decode()) if raw else []
        history.append(item)
        r.set(DEPLOY_HISTORY_KEY, json.dumps(history[-500:]))
    except Exception:
        pass
    return {"accepted": True}

def z_scores(values: List[float]) -> List[float]:
    n = len(values)
    if n == 0:
        return []
    mean = sum(values) / n
    var = sum((v - mean) ** 2 for v in values) / max(n - 1, 1)
    std = var ** 0.5
    return [(v - mean) / std if std > 0 else 0.0 for v in values]

def alert(message: str) -> None:
    url = os.getenv("SLACK_WEBHOOK_URL", "")
    if not url:
        return
    try:
        import requests
        requests.post(url, json={"text": message}, timeout=5)
    except Exception:
        pass

@app.get("/metrics/anomalies")
async def metrics_anomalies() -> Dict[str, Any]:
    durations: List[int] = []
    try:
        r = redis.Redis.from_url(os.getenv("HYPERCODE_REDIS_URL", "redis://localhost:6379/0"))
        raw = r.get(DEPLOY_HISTORY_KEY)
        history = json.loads(raw.decode()) if raw else []
        durations = [int(h.get("duration_ms", 0)) for h in history][-50:]
    except Exception:
        durations = []
    zs = z_scores([float(x) for x in durations])
    threshold = float(os.getenv("ANOMALY_Z", "2.5"))
    anomalies = [i for i, z in enumerate(zs) if abs(z) >= threshold]
    if anomalies:
        alert(f"Deployment duration anomaly z>= {threshold}: indices {anomalies}")
    return {"count": len(anomalies), "indices": anomalies, "last_z": zs[-1] if zs else 0.0}

@app.get("/dashboard")
async def dashboard() -> Any:
    html = """
    <!doctype html><html><head><meta charset=\"utf-8\"><title>HyperCode Metrics</title>
    <style>body{font-family:sans-serif;padding:16px}table{border-collapse:collapse}td,th{border:1px solid #ccc;padding:6px}</style>
    </head><body>
    <h1>Metrics Dashboard</h1>
    <div id=ready></div>
    <h2>Deployments</h2>
    <pre id=deploy></pre>
    <h2>Cache</h2>
    <pre id=cache></pre>
    <script>
    async function load(){
      const r = await fetch('/ready'); document.getElementById('ready').textContent = await r.text();
      const d = await fetch('/metrics/deployments'); document.getElementById('deploy').textContent = await d.text();
      const c = await fetch('/cache/metrics'); document.getElementById('cache').textContent = await c.text();
    }
    load(); setInterval(load, 5000);
    </script>
    </body></html>
    """
    from fastapi import Response
    return Response(content=html, media_type="text/html")

@app.websocket("/ws/debug")
async def websocket_debug_endpoint(websocket: WebSocket) -> None:
    """
    Flow State Guardian (Live Debugger) Endpoint.
    Streams execution events to the frontend.
    """
    await websocket.accept()
    try:
        while True:
            # Wait for flow data from client
            data = await websocket.receive_text()
            flow_data = json.loads(data)
            
            # Run the generator simulation
            # We iterate over the generator and send events
            for event in simulate_flow_generator(flow_data):
                await websocket.send_json(event)
                # Artificial delay for visual effect (ADHD dopamine pacing)
                await asyncio.sleep(0.5) 
            
            # Send completion message
            await websocket.send_json({"type": "execution_complete"})
            
    except WebSocketDisconnect:
        print("Client disconnected from Debugger")
    except (ValueError, RuntimeError) as e:
        print(f"Debugger Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except WebSocketDisconnect:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
else:
    try:
        db_url = os.getenv("HYPERCODE_DB_URL")
        if db_url:
            engine = create_engine(db_url)
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            cfg = AlembicConfig(os.path.join(os.path.dirname(__file__), "..", "alembic.ini"))
            alembic_command.upgrade(cfg, "head")
    except Exception:
        pass
