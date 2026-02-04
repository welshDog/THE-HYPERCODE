from __future__ import annotations
from dataclasses import dataclass
from typing import Any, List, Optional
import ast
import re
import time
from app.services.metrics_registry import metrics


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


@dataclass
class Token:
    type: str
    value: str
    lineno: int
    col: int


class Lexer:
    def __init__(self, src: str):
        self.src = src
        self.pos = 0
        self.lineno = 1
        self.col = 1

    def _peek(self) -> str:
        if self.pos >= len(self.src):
            return ""
        return self.src[self.pos]

    def _advance(self) -> str:
        ch = self._peek()
        self.pos += 1
        if ch == "\n":
            self.lineno += 1
            self.col = 1
        else:
            self.col += 1
        return ch

    def _skip_ws_and_comments(self):
        while True:
            while self._peek() and self._peek().isspace():
                self._advance()
            if self._peek() == "/" and self.pos + 1 < len(self.src) and self.src[self.pos + 1] == "/":
                while self._peek() and self._peek() != "\n":
                    self._advance()
                continue
            break

    def tokens(self) -> List[Token]:
        out: List[Token] = []
        self._skip_ws_and_comments()
        while self._peek():
            ch = self._peek()
            if ch.isalpha() or ch == "_":
                start_col = self.col
                start_line = self.lineno
                ident = self._read_ident()
                out.append(Token(self._kw_or("IDENT", ident), ident, start_line, start_col))
            elif ch.isdigit():
                start_col = self.col
                start_line = self.lineno
                num = self._read_number()
                out.append(Token("NUMBER", num, start_line, start_col))
            elif ch == '"':
                start_col = self.col
                start_line = self.lineno
                s = self._read_string()
                out.append(Token("STRING", s, start_line, start_col))
            else:
                start_line = self.lineno
                start_col = self.col
                if ch in "{}().,;=":
                    out.append(Token(ch, ch, start_line, start_col))
                    self._advance()
                else:
                    out.append(Token("CHAR", ch, start_line, start_col))
                    self._advance()
            self._skip_ws_and_comments()
        return out

    def _read_ident(self) -> str:
        s = []
        while self._peek() and (self._peek().isalnum() or self._peek() == "_"):
            s.append(self._advance())
        return "".join(s)

    def _read_number(self) -> str:
        s = []
        while self._peek() and self._peek().isdigit():
            s.append(self._advance())
        return "".join(s)

    def _read_string(self) -> str:
        self._advance()
        s = []
        while self._peek() and self._peek() != '"':
            s.append(self._advance())
        if self._peek() == '"':
            self._advance()
        return "".join(s)

    def _kw_or(self, default: str, ident: str) -> str:
        kws = {"mission", "agent", "do", "set", "remember", "call"}
        if ident in kws:
            return ident.upper()
        return default


class Parser:
    def __init__(self, tokens: List[Token]):
        self.tokens = tokens
        self.i = 0

    def _peek(self) -> Optional[Token]:
        if self.i >= len(self.tokens):
            return None
        return self.tokens[self.i]

    def _advance(self) -> Optional[Token]:
        t = self._peek()
        if t:
            self.i += 1
        return t

    def _expect(self, ttype: str) -> Token:
        t = self._peek()
        if not t or t.type != ttype:
            raise ValueError(f"expected {ttype}")
        self._advance()
        return t

    def parse(self) -> HCProgram:
        body: List[HCNode] = []
        while self._peek():
            n = self._statement()
            if n:
                body.append(n)
        return HCProgram(body=body)

    def _statement(self) -> Optional[HCNode]:
        t = self._peek()
        if not t:
            return None
        if t.type == "MISSION":
            return self._mission()
        if t.type == "AGENT":
            return self._agent()
        if t.type == "SET":
            return self._set()
        if t.type == "REMEMBER":
            return self._remember()
        if t.type == "CALL":
            return self._call()
        self._advance()
        return None

    def _mission(self) -> HCNode:
        kw = self._expect("MISSION")
        ident = self._expect("IDENT")
        self._expect("{")
        children: List[HCNode] = []
        while self._peek() and self._peek().type != "}":
            s = self._statement()
            if s:
                children.append(s)
        self._expect("}")
        return HCNode(kind="mission", value={"id": ident.value}, children=children, lineno=kw.lineno, col_offset=kw.col)

    def _agent(self) -> HCNode:
        kw = self._expect("AGENT")
        name = self._expect("IDENT")
        self._expect("DO")
        action = self._expect("IDENT")
        self._expect("(")
        args = self._args()
        self._expect(")")
        self._expect(";")
        return HCNode(kind="agent_action", value={"agent": name.value, "action": action.value, "args": args}, lineno=kw.lineno, col_offset=kw.col)

    def _set(self) -> HCNode:
        kw = self._expect("SET")
        key = self._expect("IDENT")
        self._expect("=")
        val = self._value()
        self._expect(";")
        return HCNode(kind="set", value={"key": key.value, "value": val}, lineno=kw.lineno, col_offset=kw.col)

    def _remember(self) -> HCNode:
        kw = self._expect("REMEMBER")
        key = self._expect("IDENT")
        s = self._expect("STRING")
        self._expect(";")
        return HCNode(kind="remember", value={"key": key.value, "text": s.value}, lineno=kw.lineno, col_offset=kw.col)

    def _call(self) -> HCNode:
        kw = self._expect("CALL")
        ns = self._expect("IDENT")
        self._expect(".")
        fn = self._expect("IDENT")
        self._expect("(")
        args = self._args()
        self._expect(")")
        self._expect(";")
        return HCNode(kind="call", value={"ns": ns.value, "fn": fn.value, "args": args}, lineno=kw.lineno, col_offset=kw.col)

    def _args(self) -> List[Any]:
        vals: List[Any] = []
        if self._peek() and self._peek().type in {"STRING", "NUMBER", "IDENT"}:
            vals.append(self._value())
            while self._peek() and self._peek().type == ",":
                self._advance()
                vals.append(self._value())
        return vals

    def _value(self) -> Any:
        t = self._peek()
        if not t:
            raise ValueError("expected value")
        if t.type in {"STRING", "NUMBER", "IDENT"}:
            self._advance()
            if t.type == "NUMBER":
                return int(t.value)
            return t.value
        raise ValueError("expected value")


def parse_hc(code: str) -> HCProgram:
    start = time.perf_counter()
    lex = Lexer(code)
    toks = lex.tokens()
    p = Parser(toks)
    prog = p.parse()
    dur = (time.perf_counter() - start) * 1000.0
    metrics.inc("parser_calls", 1)
    metrics.observe("parser_duration_ms", dur)
    return prog


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
