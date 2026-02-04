import pytest
import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from hypercode_engine import run_code


@pytest.mark.parametrize(
    "target,expected_contains",
    [
        ("python", "print(\"Hello\")"),
        ("javascript", "console.log(\"Hello\");"),
        ("js", "console.log(\"Hello\");"),
        ("cpp", "std::cout"),
        ("c++", "std::cout"),
        ("java", "System.out.println(\"Hello\");"),
    ],
)
def test_run_code_generates_target_code(target, expected_contains):
    res = run_code('print "Hello"', target=target)
    assert res.exit_code == 0
    assert expected_contains in res.stdout
    assert res.stderr == ""


def test_functional_equivalence_semantics():
    py = run_code('print "Hello"', target="python").stdout
    js = run_code('print "Hello"', target="javascript").stdout
    cpp = run_code('print "Hello"', target="cpp").stdout
    java = run_code('print "Hello"', target="java").stdout
    assert "Hello" in py
    assert "Hello" in js
    assert "Hello" in cpp
    assert "Hello" in java
