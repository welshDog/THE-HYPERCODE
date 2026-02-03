from fastapi import APIRouter
from app.core.db import db
from pydantic import BaseModel

router = APIRouter()

class CostSummary(BaseModel):
    total_cost: float
    total_tokens: int
    by_model: dict

@router.get("/costs", response_model=CostSummary)
async def get_costs():
    usages = await db.tokenusage.find_many()
    
    total_cost = sum(u.cost for u in usages)
    total_tokens = sum(u.totalTokens for u in usages)
    
    by_model = {}
    for u in usages:
        if u.model not in by_model:
            by_model[u.model] = 0.0
        by_model[u.model] += u.cost
        
    return {
        "total_cost": round(total_cost, 6),
        "total_tokens": total_tokens,
        "by_model": {k: round(v, 6) for k, v in by_model.items()}
    }
