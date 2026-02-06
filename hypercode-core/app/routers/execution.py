from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from app.schemas.execution import ExecutionRequest, ExecutionResult, Language
from app.services.execution_service import ExecutionService, LAST_RESULT

router = APIRouter()

@router.post("/execute", response_model=ExecutionResult, status_code=status.HTTP_200_OK)
async def execute_task(request: ExecutionRequest):
    """
    Execute a code snippet in the specified language.
    WARNING: This executes code in the container environment. 
    It is intended for development and controlled agent use only.
    """
    return await ExecutionService.execute_code(request)

@router.get("/health")
async def health_check():
    return {"status": "Execution Engine Operational"}

class HCRequest(BaseModel):
    source: str
    target: str | None = None

@router.post("/execute-hc", response_model=ExecutionResult, status_code=status.HTTP_200_OK)
async def execute_hypercode(req: HCRequest):
    r = ExecutionRequest(code=req.source, language=Language.HYPERCODE, target=req.target)
    return await ExecutionService.execute_code(r)

class HCFileRequest(BaseModel):
    path: str

@router.post("/execute-hc-file", response_model=ExecutionResult, status_code=status.HTTP_200_OK)
async def execute_hypercode_file(req: HCFileRequest):
    try:
        import os
        # SEC-01: Fix Path Traversal
        # Ensure path is within the allowed workspace (current working directory for now)
        base_dir = os.path.abspath(os.getcwd())
        requested_path = os.path.abspath(req.path)
        
        if not requested_path.startswith(base_dir):
             raise ValueError("Access denied: Path is outside the allowed directory.")

        with open(requested_path, "r", encoding="utf-8") as f:
            src = f.read()
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    r = ExecutionRequest(code=src, language=Language.HYPERCODE)
    return await ExecutionService.execute_code(r)

@router.get("/last", response_model=ExecutionResult)
async def last_execution():
    if LAST_RESULT is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No execution yet")
    return LAST_RESULT
