from dataclasses import dataclass
from typing import Optional
import os
from .pipeline import Pipeline

@dataclass
class RunResult:
    stdout: str
    stderr: str
    exit_code: int

def _parse(src: str) -> dict:
    t = src.strip()
    if t.lower().startswith("print "):
        v = t[6:].strip().strip('"').strip("'")
        return {"op": "print", "value": v}
    if t.lower().startswith("print(") and t.endswith(")"):
        inner = t[6:-1].strip().strip('"').strip("'")
        return {"op": "print", "value": inner}
    return {"op": "expr", "value": t}

def _lower(ast: dict) -> dict:
    return ast

def _opt(ir: dict) -> dict:
    if ir.get("op") == "expr":
        v = ir.get("value", "")
        return {"op": "print", "value": v}
    return ir

def _gen_python(ir: dict) -> str:
    if ir.get("op") == "print":
        return f"print(\"{ir['value']}\")"
    return ""

def _gen_js(ir: dict) -> str:
    if ir.get("op") == "print":
        return f"console.log(\"{ir['value']}\");"
    return ""

def _gen_cpp(ir: dict) -> str:
    v = ir.get("value", "")
    return (
        "#include <iostream>\n"
        "int main(){\n"
        f"  std::cout << \"{v}\" << std::endl;\n"
        "  return 0;\n"
        "}"
    )

def _gen_java(ir: dict) -> str:
    v = ir.get("value", "")
    return (
        "public class Main {\n"
        "  public static void main(String[] args){\n"
        f"    System.out.println(\"{v}\");\n"
        "  }\n"
        "}"
    )

def run_code(source: str, target: Optional[str] = None) -> RunResult:
    ast = _parse(source)
    ir = _lower(ast)
    ir2 = _opt(ir)
    t = (target or "python").lower()
    mode = "compile" if os.getenv("HYPERCODE_COMPILE", "0").lower() in ("1", "true", "yes") else "stubs"
    pipe = Pipeline(t, mode)
    code = pipe.generate(ir2)
    out = pipe.compile_and_run(code)
    return RunResult(stdout=out, stderr="", exit_code=0)
