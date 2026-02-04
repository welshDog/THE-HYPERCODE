from app.parser.hc_parser import parse
from app.engine.interpreter import execute_program
from prometheus_client import generate_latest


def test_interpreter_metrics_success_exposed():
    code = """
print("hi")
"""
    program = parse(code)
    result = execute_program(program)
    assert result.exit_code == 0
    metrics = generate_latest().decode()
    assert "interpreter_executions_total" in metrics
    assert "interpreter_execute_duration_seconds_count" in metrics


def test_interpreter_metrics_error_exposed():
    code = """
print(foo)
"""
    program = parse(code)
    result = execute_program(program)
    assert result.exit_code != 0
    metrics = generate_latest().decode()
    assert "interpreter_errors_total" in metrics
    assert "NameError" in metrics

