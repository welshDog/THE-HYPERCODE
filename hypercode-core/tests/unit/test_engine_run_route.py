from fastapi.testclient import TestClient
from main import app

def test_engine_run_route():
    client = TestClient(app)
    resp = client.post("/engine/run", json={"source": "print \"Hello Engine\""})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["stdout"] == "Hello Engine"
    assert body["language"] == "hypercode"

