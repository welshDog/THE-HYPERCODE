from fastapi import APIRouter
from app.core.db import db
from pydantic import BaseModel
import os
import httpx
from app.services.metrics_registry import metrics

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
            try:
                r = await client.get(f"{base}/api/v1/query", params={"query": expr})
                j = r.json()
                v = j["data"]["result"][0]["value"][1]
                return float(v)
            except Exception:
                return 0.0

        p50 = await q("job:agent_stream_latency_ms:hist_p50")
        p95 = await q("job:agent_stream_latency_ms:hist_p95")
        p99 = await q("job:agent_stream_latency_ms:hist_p99")
        return {"p50_ms": p50, "p95_ms": p95, "p99_ms": p99}


class PerformanceMetrics(BaseModel):
    counters: dict


@router.get("/performance", response_model=PerformanceMetrics)
async def performance_metrics():
    snap = metrics.snapshot()
    return {"counters": snap["counters"]}


class ErrorMetrics(BaseModel):
    errors: dict


@router.get("/errors", response_model=ErrorMetrics)
async def error_metrics():
    snap = metrics.snapshot()
    return {"errors": snap["errors"]}


class ExecutionMetrics(BaseModel):
    count: int
    avg_ms: float
    p50_ms: float
    p95_ms: float
    p99_ms: float


@router.get("/execution", response_model=ExecutionMetrics)
async def execution_metrics():
    snap = metrics.snapshot()
    arr = snap["timers"].get("parser_duration_ms", [])
    if not arr:
        return {"count": 0, "avg_ms": 0.0, "p50_ms": 0.0, "p95_ms": 0.0, "p99_ms": 0.0}
    srt = sorted(arr)
    def pct(p: float) -> float:
        i = max(0, min(len(srt) - 1, int(round(p * (len(srt) - 1)))))
        return srt[i]
    avg = sum(srt) / len(srt)
    return {
        "count": len(srt),
        "avg_ms": avg,
        "p50_ms": pct(0.5),
        "p95_ms": pct(0.95),
        "p99_ms": pct(0.99),
    }


class ResourceMetrics(BaseModel):
    uptime_sec: float
    memory_bytes: dict
    threads: int
    process_cpu_sec: float


@router.get("/resources", response_model=ResourceMetrics)
async def resource_metrics():
    snap = metrics.snapshot()
    return {
        "uptime_sec": snap["uptime_sec"],
        "memory_bytes": snap["memory_bytes"],
        "threads": snap["threads"],
        "process_cpu_sec": snap["process_cpu_sec"],
    }
