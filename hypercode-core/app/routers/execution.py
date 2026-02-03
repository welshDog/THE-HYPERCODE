from fastapi import APIRouter, HTTPException, status
from app.schemas.execution import ExecutionRequest, ExecutionResult
from app.services.execution_service import ExecutionService

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
