from fastapi.testclient import TestClient
from main import app


def test_immutable_role_error_payload():
    client = TestClient(app)
    base = {
        "name": "Immut",
        "role": "worker",
        "version": "0.1.0",
        "capabilities": [],
        "topics": [],
        "health_url": None,
        "dedup_key": "00000000-0000-0000-0000-00000000IM"
    }
    r1 = client.post("/agents/register", json=base)
    assert r1.status_code == 200

    bad = dict(base)
    bad["role"] = "architect"
    r2 = client.post("/agents/register", json=bad)
    assert r2.status_code == 422
    body = r2.json()
    assert body["detail"]["error"] == "immutable_field"
    assert "dedup_key and role are immutable" in body["detail"]["message"]
