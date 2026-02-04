from app.parser.hc_parser import parse, HCProgram, HCNode


def test_parse_hello_world():
    code = 'print("Hello, HyperCode! 🧠🚀")\n'
    program = parse(code)
    assert isinstance(program, HCProgram)
    assert len(program.body) == 1
    node = program.body[0]
    assert isinstance(node, HCNode)
    assert node.kind == "expr"
    assert "call" in str(node.value)


def test_parse_assignment():
    code = "x = 42\n"
    program = parse(code)
    assert len(program.body) == 1
    node = program.body[0]
    assert node.kind == "assign"
    assert node.value["targets"][0]["var"] == "x"
    assert node.value["value"] == 42


def test_parse_function_def():
    code = """
def add(a, b):
    return a + b
"""
    program = parse(code)
    node = program.body[0]
    assert node.kind == "function_def"
    assert node.value["name"] == "add"
    assert node.value["args"] == ["a", "b"]
    assert node.children

