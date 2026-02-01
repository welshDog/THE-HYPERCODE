import pytest
from fastapi.testclient import TestClient
from hypercode.server import app

client = TestClient(app)

def test_workflows_get():
    r = client.get('/workflows')
    assert r.status_code == 200
    assert 'items' in r.json()

def test_workflows_post():
    payload = { 'name': 'Test Flow', 'flow': { 'nodes': [], 'edges': [] } }
    r = client.post('/workflows', json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data['name'] == 'Test Flow'
    assert 'id' in data
