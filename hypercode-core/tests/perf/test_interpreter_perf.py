import time
from app.parser.hc_parser import parse
from app.engine.interpreter import execute_program


def test_perf_simple_loop_under_threshold():
    code = """
x = 0
while x < 1000:
    x = x + 1
"""
    t0 = time.time()
    p = parse(code)
    r = execute_program(p)
    dt = time.time() - t0
    assert r.exit_code == 0
    assert dt < 0.5

