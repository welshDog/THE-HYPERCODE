import pytest
import os
import shutil
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from hypercode_engine import run_code


def _tool_available(name: str) -> bool:
    return shutil.which(name) is not None


@pytest.mark.skipif(not _tool_available("node"), reason="node not available")
def test_compile_javascript_runtime_output(monkeypatch):
    monkeypatch.setenv("HYPERCODE_COMPILE", "1")
    res = run_code('print "Hello"', target="javascript")
    assert res.exit_code == 0
    assert res.stdout == "Hello"


@pytest.mark.skipif(not _tool_available("g++"), reason="g++ not available")
def test_compile_cpp_runtime_output(monkeypatch):
    monkeypatch.setenv("HYPERCODE_COMPILE", "1")
    res = run_code('print "Hello"', target="cpp")
    assert res.exit_code == 0
    assert res.stdout == "Hello"


@pytest.mark.skipif(not _tool_available("javac") or not _tool_available("java"), reason="javac/java not available")
def test_compile_java_runtime_output(monkeypatch):
    monkeypatch.setenv("HYPERCODE_COMPILE", "1")
    res = run_code('print "Hello"', target="java")
    assert res.exit_code == 0
    assert res.stdout == "Hello"
