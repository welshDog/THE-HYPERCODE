from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from typing import Optional, Dict
from app.schemas.execution import ExecutionRequest, ExecutionResult, Language
from app.engine import adapter as hc_adapter
from app.services.execution_service import ExecutionService

router = APIRouter()

class RunRequest(BaseModel):
    source: str = Field(...)
    timeout: int = Field(default=30, ge=1, le=300)
    env_vars: Optional[Dict[str, str]] = None
    target: Optional[str] = None

@router.post("/run", response_model=ExecutionResult, status_code=status.HTTP_200_OK)
async def run(req: RunRequest):
    import sys
    mod = sys.modules.get("hypercode_engine")
    if mod and hasattr(mod, "run_code"):
        res = mod.run_code(req.source, target=req.target)
        return ExecutionResult(
            stdout=getattr(res, "stdout", ""),
            stderr=getattr(res, "stderr", ""),
            exit_code=getattr(res, "exit_code", 0),
            status="success" if getattr(res, "exit_code", 0) == 0 else "error",
            duration=0.0,
            language=Language.HYPERCODE,
        )
    token = hc_adapter.set_internal_call(True)
    try:
        r = ExecutionRequest(code=req.source, language=Language.HYPERCODE, timeout=req.timeout, env_vars=req.env_vars, target=req.target)
        return await ExecutionService.execute_code(r)
    finally:
        hc_adapter.reset_internal_call(token)
