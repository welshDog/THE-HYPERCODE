from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import json
import asyncio

from hypercode.compiler import compile_flow
from hypercode.simulator import simulate_flow, simulate_flow_generator

app = FastAPI(title="HyperCode Backend API")

# Enable CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],  # Vite default port
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FlowRequest(BaseModel):
    nodes: List[Dict[str, Any]]
    edges: List[Dict[str, Any]]
    viewport: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    return {"message": "HyperCode Backend Online", "status": "ready"}

@app.get("/health")
async def health_check():
    return {"status": "ok"}

@app.post("/compile")
async def compile_endpoint(flow: FlowRequest):
    """
    Compiles a Visual Flow into HyperCode source text.
    """
    try:
        # Convert Pydantic model to dict
        flow_data = flow.model_dump()
        
        # Generate Code
        source_code = compile_flow(flow_data)
        
        # Run Simulation
        simulation_results = simulate_flow(flow_data)
        
        return {
            "success": True,
            "code": source_code,
            "simulation": simulation_results,
            "message": "Compilation and Simulation successful"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

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
