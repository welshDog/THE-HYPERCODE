from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio
import time
import uuid
import hashlib

from hypercode.compiler import compile_flow
from hypercode.simulator import simulate_flow, simulate_flow_generator

app = FastAPI(title="HyperCode Backend API")

IDEMPOTENCY_STORE: Dict[str, Dict[str, Any]] = {}
RATE_LIMIT_WINDOW_SECONDS = 60
RATE_LIMIT_MAX_REQUESTS = 10
REQUEST_TIMES: Dict[str, List[float]] = {}
RUNS: Dict[str, Dict[str, Any]] = {}

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
async def root():
    return {"message": "HyperCode Backend Online", "status": "ready"}

@app.get("/health")
async def health_check():
    return {"status": "ok", "services": {"compiler": "ok", "simulator": "ok"}}

@app.get("/runs/{run_id}")
async def get_run(run_id: str):
    r = RUNS.get(run_id)
    if not r:
        raise HTTPException(status_code=404, detail={"code": "RUN_NOT_FOUND", "message": "Run not found"})
    return r

@app.post("/compile", response_model=CompileResponse)
async def compile_endpoint(flow: FlowRequest, request: Request):
    """
    Compiles a Visual Flow into HyperCode source text.
    """
    try:
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
        return resp
    except HTTPException:
        raise
    except Exception as e:
        req_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        raise HTTPException(status_code=500, detail={
            "code": "COMPILER_ERROR",
            "message": str(e),
            "requestId": req_id
        }) from e

@app.websocket("/ws/debug")
async def websocket_debug_endpoint(websocket: WebSocket):
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
    except Exception as e:
        print(f"Debugger Error: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
