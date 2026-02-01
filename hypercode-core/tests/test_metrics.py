from fastapi.testclient import TestClient
from hypercode.server import app

client = TestClient(app)

def test_metrics_endpoint():
    r = client.get('/metrics')
    assert r.status_code == 200
    assert 'text/plain' in r.headers['content-type']
