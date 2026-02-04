import pytest
from fastapi.testclient import TestClient
from main import app


@pytest.mark.parametrize("initial_role,changed_role", [
    ("worker", "architect"),
    ("Worker", "architect"),
    ("worker", "Architect"),
])
def test_role_change_with_same_dedup_key_returns_422(initial_role, changed_role):
    client = TestClient(app)
    base = {
        "name": "RoleTest",
        "role": initial_role,
        "version": "0.1.0",
        "capabilities": [],
        "topics": [],
        "health_url": None,
        "dedup_key": "00000000-0000-0000-0000-00000000RR"
    }
    r1 = client.post("/agents/register", json=base)
    assert r1.status_code == 200

    bad = dict(base)
    bad["role"] = changed_role
    r2 = client.post("/agents/register", json=bad)
    assert r2.status_code == 422


def test_case_only_role_is_considered_same():
    client = TestClient(app)
    base = {
        "name": "RoleCase",
        "role": "Worker",
        "version": "0.1.0",
        "capabilities": [],
        "topics": [],
        "health_url": None,
        "dedup_key": "00000000-0000-0000-0000-00000000RC"
    }
    r1 = client.post("/agents/register", json=base)
    assert r1.status_code == 200

    upd = dict(base)
    upd["role"] = "worker"
    r2 = client.post("/agents/register", json=upd)
    assert r2.status_code == 200
