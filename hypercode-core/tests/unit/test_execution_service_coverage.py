import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from app.services.execution_service import ExecutionService
from app.schemas.execution import ExecutionRequest, ExecutionResult, Language

@pytest.fixture
def mock_subprocess():
    with patch("asyncio.create_subprocess_exec") as mock:
        process_mock = AsyncMock()
        process_mock.communicate.return_value = (b"output", b"errors")
        process_mock.returncode = 0
        mock.return_value = process_mock
        yield mock

@pytest.mark.asyncio
async def test_execute_python_success(mock_subprocess):
    request = ExecutionRequest(
        language=Language.PYTHON,
        code="print('hello')",
        timeout=5.0
    )
    result = await ExecutionService.execute_code(request)
    
    assert result.status == "success"
    assert result.stdout == "output"
    assert result.stderr == "errors"
    assert result.exit_code == 0
    
    mock_subprocess.assert_called_once()
    args = mock_subprocess.call_args[0]
    assert args[0] == "python"
    assert args[1] == "-c"
    assert args[2] == "print('hello')"

@pytest.mark.asyncio
async def test_execute_python_timeout(mock_subprocess):
    # Setup timeout simulation
    process_mock = mock_subprocess.return_value
    process_mock.communicate.side_effect = asyncio.TimeoutError()
    
    request = ExecutionRequest(
        language=Language.PYTHON,
        code="while True: pass",
        timeout=1.0
    )
    result = await ExecutionService.execute_code(request)
    
    assert result.status == "timeout"
    assert "timed out" in result.stderr
    assert result.exit_code == -1
    process_mock.kill.assert_called_once()

@pytest.mark.asyncio
async def test_execute_bash_simple(mock_subprocess):
    request = ExecutionRequest(
        language=Language.BASH,
        code="ls -la",
        timeout=5.0
    )
    await ExecutionService.execute_code(request)
    
    args = mock_subprocess.call_args[0]
    assert args[0] == "bash"
    assert args[1] == "-c"
    assert args[2] == "ls -la"

@pytest.mark.asyncio
async def test_execute_bash_python_unwrap(mock_subprocess):
    # Test the unwrapping logic for "python -c" inside bash
    request = ExecutionRequest(
        language=Language.BASH,
        code="python -c 'print(1)'",
        timeout=5.0
    )
    await ExecutionService.execute_code(request)
    
    args = mock_subprocess.call_args[0]
    assert args[0] == "python"
    assert args[1] == "-c"
    assert args[2] == "print(1)"

@pytest.mark.asyncio
async def test_execute_hypercode_with_target(mock_subprocess):
    request = ExecutionRequest(
        language=Language.HYPERCODE,
        code="task1",
        target="file.hc",
        timeout=5.0
    )
    await ExecutionService.execute_code(request)
    
    args = mock_subprocess.call_args[0]
    # Should use CLI
    assert args[0] == "python"
    assert "-m" in args
    assert "app.engine.cli" in args
    assert "-t" in args
    assert "file.hc" in args

@pytest.mark.asyncio
async def test_execute_hypercode_direct():
    # Mock the adapter run_hypercode
    with patch("app.services.execution_service.run_hypercode", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = ("hc_out", "hc_err", 0, None)
        
        request = ExecutionRequest(
            language=Language.HYPERCODE,
            code="run task",
            timeout=5.0
        )
        result = await ExecutionService.execute_code(request)
        
        assert result.status == "success"
        assert result.stdout == "hc_out"
        mock_run.assert_called_once()

@pytest.mark.asyncio
async def test_execution_exception():
    with patch("asyncio.create_subprocess_exec", side_effect=Exception("System failure")):
        request = ExecutionRequest(
            language=Language.PYTHON,
            code="pass"
        )
        result = await ExecutionService.execute_code(request)
        
        assert result.status == "error"
        assert "System failure" in result.stderr

    pass
