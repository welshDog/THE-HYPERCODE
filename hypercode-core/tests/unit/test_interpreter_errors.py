from app.parser.hc_parser import parse
from app.engine.interpreter import execute_program


def test_undefined_name_error():
    code = """
print(foo)
"""
    p = parse(code)
    r = execute_program(p)
    assert r.exit_code != 0
    assert "NameError" in r.stderr
    assert "I can't find" in r.stderr


def test_unsupported_node_error():
    code = """
class X:
    pass
"""
    p = parse(code)
    r = execute_program(p)
    assert r.exit_code != 0
    assert "isn't supported" in r.stderr
