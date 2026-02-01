import os
import asyncio
from typing import Any, Dict
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

DB_URL = os.getenv("HYPERCODE_DB_URL", "postgresql+asyncpg://hyper:hyper@localhost:5432/hypercode")
ENGINE = create_async_engine(DB_URL, pool_size=10, max_overflow=20)

async def insert_audit(payload: Dict[str, Any]) -> None:
    async with ENGINE.begin() as conn:
        await conn.execute(text(
            """
            INSERT INTO celery_task_audit (
              id, task_id, name, status, runtime_ms, args, kwargs, result, traceback, timestamp, worker_name
            ) VALUES (
              :id, :task_id, :name, :status, :runtime_ms, :args, :kwargs, :result, :traceback, NOW(), :worker_name
            )
            """
        ), payload)

def insert_audit_sync(payload: Dict[str, Any]) -> None:
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    loop.run_until_complete(insert_audit(payload))
