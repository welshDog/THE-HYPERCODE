import asyncio
import json
import pytest
from fastapi.testclient import TestClient
from app.core.config import get_settings
from main import app

pytestmark = pytest.mark.experimental


@pytest.fixture
def client():
    return TestClient(app)


def test_voice_ws_text_flow_dev_auth_disabled(client):
    settings = get_settings()
    # ensure dev mode allows open access
    assert settings.API_KEY in (None, "",)
    with client.websocket_connect("/voice/ws") as ws:
        ws.send_text(json.dumps({"text": "print('hi')"}))
        data = ws.receive_json()
        assert data["stdout"].strip() == "hi"
        assert data["exit_code"] == 0


def test_voice_ws_rate_limit(client):
    # simulate many messages and expect success under limit
    with client.websocket_connect("/voice/ws") as ws:
        for _ in range(5):
            ws.send_text(json.dumps({"text": "print('x')"}))
            data = ws.receive_json()
            assert data["stdout"].strip() == "x"
