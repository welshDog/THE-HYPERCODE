from fastapi import APIRouter

router = APIRouter()

@router.get("/")
async def get_memory():
    return {"message": "Memory interface"}
