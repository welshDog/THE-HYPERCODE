from fastapi.testclient import TestClient
from main import app
import tempfile
import os

def test_execute_hc_file_run():
    client = TestClient(app)
    # Create temp file in current directory to pass path validation
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".hc", encoding="utf-8", dir=".") as tf:
        tf.write('print "From File"')
        temp_path = tf.name
    try:
        resp = client.post("/execution/execute-hc-file", json={"path": temp_path})
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "success"
        assert body["stdout"] == "From File"
        assert body["language"] == "hypercode"
    finally:
        os.unlink(temp_path)

