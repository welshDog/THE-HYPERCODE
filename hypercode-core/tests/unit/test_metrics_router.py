import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_db():
    mock = AsyncMock()
    return mock

@pytest.fixture
def mock_metrics():
    mock = MagicMock()
    return mock

def test_get_costs(client, mock_db):
    # Mock db.tokenusage.find_many
    usage1 = MagicMock()
    usage1.cost = 0.1
    usage1.totalTokens = 100
    usage1.model = "gpt-4"
    
    usage2 = MagicMock()
    usage2.cost = 0.05
    usage2.totalTokens = 50
    usage2.model = "gpt-3.5"
    
    mock_db.tokenusage.find_many.return_value = [usage1, usage2]
    
    with patch("app.routers.metrics.db", mock_db):
        response = client.get("/metrics/costs")
        assert response.status_code == 200
        data = response.json()
        assert data["total_cost"] == 0.15
        assert data["total_tokens"] == 150
        assert data["by_model"]["gpt-4"] == 0.1
        assert data["by_model"]["gpt-3.5"] == 0.05

def test_performance_metrics(client, mock_metrics):
    mock_metrics.snapshot.return_value = {"counters": {"c1": 1}}
    
    with patch("app.routers.metrics.metrics", mock_metrics):
        response = client.get("/metrics/performance")
        assert response.status_code == 200
        assert response.json()["counters"]["c1"] == 1

def test_error_metrics(client, mock_metrics):
    mock_metrics.snapshot.return_value = {"errors": {"e1": 1}}
    
    with patch("app.routers.metrics.metrics", mock_metrics):
        response = client.get("/metrics/errors")
        assert response.status_code == 200
        assert response.json()["errors"]["e1"] == 1

def test_execution_metrics(client, mock_metrics):
    mock_metrics.snapshot.return_value = {
        "timers": {
            "parser_duration_ms": [10.0, 20.0, 30.0]
        }
    }
    
    with patch("app.routers.metrics.metrics", mock_metrics):
        response = client.get("/metrics/execution")
        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 3
        assert data["avg_ms"] == 20.0
        assert data["p50_ms"] == 20.0 # Median of 10, 20, 30

def test_execution_metrics_empty(client, mock_metrics):
    mock_metrics.snapshot.return_value = {"timers": {}}
    
    with patch("app.routers.metrics.metrics", mock_metrics):
        response = client.get("/metrics/execution")
        assert response.status_code == 200
        assert response.json()["count"] == 0

def test_resource_metrics(client, mock_metrics):
    mock_metrics.snapshot.return_value = {
        "uptime_sec": 100,
        "memory_bytes": {"rss": 1000},
        "threads": 5,
        "process_cpu_sec": 1.5
    }
    
    with patch("app.routers.metrics.metrics", mock_metrics):
        response = client.get("/metrics/resources")
        assert response.status_code == 200
        assert response.json()["uptime_sec"] == 100

@pytest.mark.asyncio
async def test_agent_stream_summary(client):
    # Mock httpx.AsyncClient
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        # Mock responses for p50, p95, p99
        # format: j["data"]["result"][0]["value"][1]
        def mock_get(url, params=None):
            resp = MagicMock()
            if "p50" in params["query"]:
                val = "50.0"
            elif "p95" in params["query"]:
                val = "95.0"
            elif "p99" in params["query"]:
                val = "99.0"
            else:
                val = "0.0"
                
            resp.json.return_value = {
                "data": {
                    "result": [
                        {"value": [0, val]}
                    ]
                }
            }
            return resp
            
        mock_client.get.side_effect = mock_get
        
        response = client.get("/metrics/agent_stream_summary")
        assert response.status_code == 200
        data = response.json()
        assert data["p50_ms"] == 50.0
        assert data["p95_ms"] == 95.0
        assert data["p99_ms"] == 99.0

@pytest.mark.asyncio
async def test_agent_stream_summary_error(client):
    with patch("httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        
        mock_client.get.side_effect = Exception("Prometheus Down")
        
        response = client.get("/metrics/agent_stream_summary")
        assert response.status_code == 200
        data = response.json()
        assert data["p50_ms"] == 0.0
