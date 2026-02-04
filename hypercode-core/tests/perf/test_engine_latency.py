import time
from statistics import mean, median
from fastapi.testclient import TestClient
from main import app

def test_engine_run_latency_distribution():
    client = TestClient(app)
    samples = []
    for _ in range(10):
        t0 = time.perf_counter()
        resp = client.post("/engine/run", json={"source": "print \"ok\""})
        dt = (time.perf_counter() - t0) * 1000.0
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "success"
        assert data["stdout"] == "ok"
        samples.append(dt)
    assert len(samples) == 10
    _mean = mean(samples)
    _median = median(samples)
    assert _mean > 0
    assert _median > 0
