from fastapi import APIRouter
from app.core.db import db
from pydantic import BaseModel
import os
import httpx

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

class AgentStreamSummary(BaseModel):
    p50_ms: float
    p95_ms: float
    p99_ms: float

@router.get("/agent_stream_summary", response_model=AgentStreamSummary)
async def agent_stream_summary():
    base = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
    async with httpx.AsyncClient(timeout=3.0) as client:
        async def q(expr: str) -> float:
            r = await client.get(f"{base}/api/v1/query", params={"query": expr})
            j = r.json()
            try:
                v = j["data"]["result"][0]["value"][1]
                return float(v)
            except Exception:
                return 0.0

        p50 = await q("job:agent_stream_latency_ms:hist_p50")
        p95 = await q("job:agent_stream_latency_ms:hist_p95")
        p99 = await q("job:agent_stream_latency_ms:hist_p99")
        return {"p50_ms": p50, "p95_ms": p95, "p99_ms": p99}
