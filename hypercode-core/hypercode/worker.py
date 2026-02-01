import os
import time
import threading
import json
import uuid
from celery import Celery
from celery.signals import task_postrun, task_success, task_failure, task_retry
import redis
from .audit import insert_audit_sync

broker = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
app = Celery("hypercode", broker=broker, backend=backend)

r = redis.Redis.from_url(os.getenv("HYPERCODE_REDIS_URL", broker))

@app.task(name="hypercode.ping")
def ping(x: int = 1) -> int:
    r.incr("hypercode:metrics:processed")
    return x

@app.task(name="hypercode.heartbeat")
def heartbeat() -> str:
    r.set("hypercode:metrics:last_heartbeat", int(__import__("time").time()))
    return "ok"

def queue_depth(queue: str = "celery") -> int:
    try:
        return r.llen(f"{queue}")
    except Exception:
        return -1

def _inc(key: str):
    try:
        r.incr(key)
        r.expire(key, 7 * 24 * 3600)
    except Exception:
        pass

def _set_ts(worker: str):
    try:
        r.set(f"celery:worker:{worker}:last_task_ts", int(time.time()))
        r.expire(f"celery:worker:{worker}:last_task_ts", 7 * 24 * 3600)
    except Exception:
        pass

@task_success.connect
def on_task_success(sender=None, result=None, **kwargs):
    try:
        worker = getattr(sender.request, "hostname", "unknown")
        _inc(f"celery:worker:{worker}:success")
        _set_ts(worker)
    except Exception:
        pass

@task_failure.connect
def on_task_failure(sender=None, exception=None, **kwargs):
    try:
        worker = getattr(sender.request, "hostname", "unknown")
        _inc(f"celery:worker:{worker}:failure")
        _set_ts(worker)
    except Exception:
        pass

@task_retry.connect
def on_task_retry(sender=None, **kwargs):
    try:
        worker = getattr(sender.request, "hostname", "unknown")
        _inc(f"celery:worker:{worker}:retries")
        _set_ts(worker)
    except Exception:
        pass

@task_postrun.connect
def on_task_postrun(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kw):
    try:
        worker = getattr(task.request, "hostname", "unknown")
        start = getattr(task.request, "time_start", None)
        runtime_ms = int((time.time() - start) * 1000) if start else 0
        payload = {
            "id": uuid.uuid4().hex,
            "task_id": task_id or "",
            "name": getattr(task, "name", ""),
            "status": (state or "SUCCESS").lower(),
            "runtime_ms": runtime_ms,
            "args": json.dumps(args or []),
            "kwargs": json.dumps(kwargs or {}),
            "result": json.dumps(retval),
            "traceback": kw.get("traceback"),
            "worker_name": worker,
        }
        insert_audit_sync(payload)
        _set_ts(worker)
    except Exception:
        pass

def _aggregate_cluster():
    try:
        keys = r.keys("celery:worker:*:success")
        total_s = 0
        total_f = 0
        total_r = 0
        for k in keys:
            name = k.decode().split(":")[2]
            total_s += int(r.get(k) or 0)
            total_f += int(r.get(f"celery:worker:{name}:failure") or 0)
            total_r += int(r.get(f"celery:worker:{name}:retries") or 0)
        r.set("celery:cluster_total:success", total_s, ex=7 * 24 * 3600)
        r.set("celery:cluster_total:failure", total_f, ex=7 * 24 * 3600)
        r.set("celery:cluster_total:retries", total_r, ex=7 * 24 * 3600)
    except Exception:
        pass

def _start_aggregator():
    def loop():
        while True:
            _aggregate_cluster()
            time.sleep(15)
    t = threading.Thread(target=loop, daemon=True)
    t.start()

_start_aggregator()
