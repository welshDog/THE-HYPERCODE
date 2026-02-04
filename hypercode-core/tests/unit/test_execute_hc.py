import pytest
from fastapi.testclient import TestClient
from main import app

def test_execute_hc_eval_print():
    client = TestClient(app)
    payload = {"source": "print \"Hello HC\""}
    resp = client.post("/execution/execute-hc", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert body["stdout"] == "Hello HC"
    assert body["language"] == "hypercode"
