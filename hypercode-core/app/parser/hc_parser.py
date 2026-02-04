from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional
import ast


@dataclass
class HCNode:
    kind: str
    value: Any = None
    children: List["HCNode"] | None = None
    lineno: Optional[int] = None
    col_offset: Optional[int] = None

    def __post_init__(self):
        if self.children is None:
            self.children = []


@dataclass
class HCProgram:
    body: List[HCNode]


def parse(code: str) -> HCProgram:
    py_ast = ast.parse(code)
    body = [_convert_node(n) for n in py_ast.body]
    return HCProgram(body=body)


def _convert_node(node: ast.AST) -> HCNode:
    if isinstance(node, ast.Expr):
        return HCNode(kind="expr", value=_convert_expr(node.value), lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.Assign):
        targets = [
            {"var": t.id} if isinstance(t, ast.Name) else {"target": _simple_value(t)}
            for t in node.targets
        ]
        val = _simple_value(node.value)
        return HCNode(kind="assign", value={"targets": targets, "value": val}, lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.FunctionDef):
        args = [a.arg for a in node.args.args]
        children = [_convert_node(n) for n in node.body]
        return HCNode(kind="function_def", value={"name": node.name, "args": args}, children=children, lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.Return):
        return HCNode(kind="return", value=_simple_value(node.value), lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.If):
        test = _simple_value(node.test)
        body = [_convert_node(n) for n in node.body]
        orelse = [_convert_node(n) for n in node.orelse]
        return HCNode(kind="if", value={"test": test}, children=[HCNode(kind="body", children=body), HCNode(kind="orelse", children=orelse)], lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.While):
        test = _simple_value(node.test)
        body = [_convert_node(n) for n in node.body]
        orelse = [_convert_node(n) for n in node.orelse]
        return HCNode(kind="while", value={"test": test}, children=[HCNode(kind="body", children=body), HCNode(kind="orelse", children=orelse)], lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.For):
        target = _simple_value(node.target)
        iter_v = _simple_value(node.iter)
        body = [_convert_node(n) for n in node.body]
        orelse = [_convert_node(n) for n in node.orelse]
        return HCNode(kind="for", value={"target": target, "iter": iter_v}, children=[HCNode(kind="body", children=body), HCNode(kind="orelse", children=orelse)], lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.Break):
        return HCNode(kind="break", lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if isinstance(node, ast.Continue):
        return HCNode(kind="continue", lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    if hasattr(ast, "Match") and isinstance(node, getattr(ast, "Match")):
        subject = _simple_value(node.subject)
        cases = []
        for c in node.cases:
            patt = _simple_value(c.pattern)
            body = [_convert_node(n) for n in c.body]
            cases.append({"pattern": patt, "body": body})
        return HCNode(kind="match", value={"subject": subject, "cases": cases}, lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))
    return HCNode(kind=type(node).__name__.lower(), value=None, lineno=getattr(node, "lineno", None), col_offset=getattr(node, "col_offset", None))


def _convert_expr(node: ast.AST) -> Any:
    if isinstance(node, ast.Call):
        func = _name_or_attr(node.func)
        args = [_simple_value(a) for a in node.args]
        return {"call": {"func": func, "args": args}}
    return _simple_value(node)


def _name_or_attr(node: ast.AST) -> Any:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return {"attr": {"value": _name_or_attr(node.value), "name": node.attr}}
    return ast.dump(node)


def _simple_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        return {"var": node.id}
    if isinstance(node, ast.Str):
        return node.s
    if isinstance(node, ast.Num):
        return node.n
    if isinstance(node, ast.List):
        return [_simple_value(e) for e in node.elts]
    if isinstance(node, ast.Tuple):
        return tuple(_simple_value(e) for e in node.elts)
    if isinstance(node, ast.Call):
        func = _name_or_attr(node.func)
        args = [_simple_value(a) for a in node.args]
        return {"call": {"func": func, "args": args}}
    if isinstance(node, ast.BinOp):
        op = node.op
        left = _simple_value(node.left)
        right = _simple_value(node.right)
        op_name = type(op).__name__.lower()
        return {"binop": {"op": op_name, "left": left, "right": right}}
    if isinstance(node, ast.BoolOp):
        op_name = type(node.op).__name__.lower()
        vals = [_simple_value(v) for v in node.values]
        return {"boolop": {"op": op_name, "values": vals}}
    if isinstance(node, ast.UnaryOp):
        op_name = type(node.op).__name__.lower()
        operand = _simple_value(node.operand)
        return {"unary": {"op": op_name, "operand": operand}}
    if isinstance(node, ast.Compare):
        left = _simple_value(node.left)
        ops = [type(o).__name__.lower() for o in node.ops]
        comps = [_simple_value(c) for c in node.comparators]
        return {"compare": {"left": left, "ops": ops, "comparators": comps}}
    return ast.dump(node)
