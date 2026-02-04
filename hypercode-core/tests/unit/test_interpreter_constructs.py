from app.parser.hc_parser import parse
from app.engine.interpreter import execute_program


def run(code: str):
    program = parse(code)
    result = execute_program(program)
    return result


def test_if_else():
    code = """
x = 1
if x == 1:
    print("A")
else:
    print("B")
"""
    r = run(code)
    assert r.exit_code == 0
    assert r.stdout.strip() == "A"


def test_while_loop_break():
    code = """
x = 0
while x < 3:
    print(x)
    x = x + 1
    if x == 2:
        break
"""
    r = run(code)
    assert r.exit_code == 0
    assert r.stdout.strip() == "0\n1"


def test_for_loop_continue():
    code = """
for i in [0,1,2,3]:
    if i == 2:
        continue
    print(i)
"""
    r = run(code)
    assert r.exit_code == 0
    assert r.stdout.strip() == "0\n1\n3"


def test_function_decl_and_call():
    code = """
def add(a, b):
    return a + b
print(add(2,3))
"""
    r = run(code)
    assert r.exit_code == 0
    assert r.stdout.strip() == "5"


def test_scoping_variables():
    code = """
x = 10
def f(a):
    y = a + x
    return y
print(f(2))
"""
    r = run(code)
    assert r.exit_code == 0
    assert r.stdout.strip() == "12"


def test_operators_and_expressions():
    code = """
a = 3
b = 4
print(a * b)
print(a + b == 7 and not (a == b))
"""
    r = run(code)
    assert r.exit_code == 0
    assert r.stdout.strip() == "12\nTrue"

