from __future__ import annotations
from typing import Any, List, Dict, Optional
import time
from prometheus_client import Counter, Histogram
from dataclasses import dataclass
from app.errors.nd_errors import (
    create_undefined_name_error,
    create_unsupported_error,
    wrap_interpreter_error,
)


# Prometheus metrics
INTERPRETER_EXECUTIONS = Counter(
    "interpreter_executions_total",
    "Interpreter executions",
    ("status",),
)
INTERPRETER_ERRORS = Counter(
    "interpreter_errors_total",
    "Interpreter errors",
    ("error_type",),
)
INTERPRETER_EXECUTE_DURATION = Histogram(
    "interpreter_execute_duration_seconds",
    "Interpreter execution duration (seconds)",
    ("status",),
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 2.0)
)

@dataclass
class ExecResult:
    stdout: str
    stderr: str
    exit_code: int


class InterpreterError(Exception):
    pass


class _ReturnSignal(Exception):
    def __init__(self, value: Any):
        self.value = value


class _BreakSignal(Exception):
    pass


class _ContinueSignal(Exception):
    pass


class Interpreter:
    def __init__(self):
        self._stdout: List[str] = []
        self.globals: Dict[str, Any] = {}
        self.stack: List[Dict[str, Any]] = [self.globals]
        self.functions: Dict[str, Dict[str, Any]] = {}
        self.builtins: Dict[str, Any] = {
            "print": lambda *args: self._stdout.append(" ".join(str(a) for a in args))
        }

    def _env_get(self, name: str) -> Any:
        for env in reversed(self.stack):
            if name in env:
                return env[name]
        if name in self.builtins:
            return self.builtins[name]
        nd = create_undefined_name_error(name, 0, list(self.stack[-1].keys()))
        raise NameError(nd.message)

    def _env_set(self, name: str, value: Any) -> None:
        if isinstance(name, tuple):
            for i, n in enumerate(name):
                self.stack[-1][n] = value[i]
        else:
            self.stack[-1][name] = value

    def _push(self):
        self.stack.append({})

    def _pop(self):
        self.stack.pop()

    def execute(self, program) -> ExecResult:
        t0 = time.perf_counter()
        try:
            for node in program.body:
                self._exec_node(node)
            INTERPRETER_EXECUTIONS.labels("success").inc()
            INTERPRETER_EXECUTE_DURATION.labels("success").observe(time.perf_counter() - t0)
            return ExecResult(stdout="\n".join(s for s in self._stdout), stderr="", exit_code=0)
        except Exception as e:
            env_names = list(self.stack[-1].keys()) if self.stack else []
            nd = wrap_interpreter_error(e, "", env_names)
            INTERPRETER_EXECUTIONS.labels("error").inc()
            INTERPRETER_ERRORS.labels(type(e).__name__).inc()
            INTERPRETER_EXECUTE_DURATION.labels("error").observe(time.perf_counter() - t0)
            return ExecResult(stdout="\n".join(s for s in self._stdout), stderr=nd.format(), exit_code=1)

    def _exec_node(self, node):
        k = node.kind
        if k == "assign":
            val = self._eval_value(node.value["value"]) if isinstance(node.value, dict) else node.value
            for t in node.value["targets"]:
                name = t.get("var") or t.get("target")
                if isinstance(name, str):
                    self._env_set(name, val)
        elif k == "expr":
            self._eval_value(node.value)
        elif k == "function_def":
            self.functions[node.value["name"]] = {"args": node.value["args"], "body": node.children}
        elif k == "return":
            val = self._eval_value(node.value)
            raise _ReturnSignal(val)
        elif k == "if":
            cond = self._eval_value(node.value["test"])
            if cond:
                for bn in (node.children[0].children or []):
                    self._exec_node(bn)
            else:
                for en in (node.children[1].children or []):
                    self._exec_node(en)
        elif k == "while":
            while self._eval_value(node.value["test"]):
                try:
                    for bn in (node.children[0].children or []):
                        self._exec_node(bn)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    continue
            for en in (node.children[1].children or []):
                self._exec_node(en)
        elif k == "for":
            iterable = self._eval_value(node.value["iter"])
            target = node.value["target"]
            for item in iterable:
                if isinstance(target, str):
                    self._env_set(target, item)
                elif isinstance(target, dict) and "var" in target:
                    self._env_set(target["var"], item)
                try:
                    for bn in (node.children[0].children or []):
                        self._exec_node(bn)
                except _BreakSignal:
                    break
                except _ContinueSignal:
                    continue
            for en in (node.children[1].children or []):
                self._exec_node(en)
        elif k == "break":
            raise _BreakSignal()
        elif k == "continue":
            raise _ContinueSignal()
        elif k == "match":
            subj = self._eval_value(node.value["subject"])
            done = False
            for case in node.value["cases"]:
                patt = case["pattern"]
                if subj == patt:
                    for bn in case["body"]:
                        self._exec_node(bn)
                    done = True
                    break
            if not done:
                pass
        else:
            nd = create_unsupported_error(k, getattr(node, "lineno", 0) or 0)
            raise RuntimeError(nd.format())

    def _call(self, name: str, args: List[Any]) -> Any:
        if name in self.builtins:
            return self.builtins[name](*args)
        fn = self.functions.get(name)
        if not fn:
            raise InterpreterError(f"undefined function: {name}")
        self._push()
        for p, a in zip(fn["args"], args):
            self._env_set(p, a)
        try:
            for n in fn["body"]:
                self._exec_node(n)
        except _ReturnSignal as r:
            self._pop()
            return r.value
        self._pop()
        return None

    def _eval_value(self, v: Any) -> Any:
        if isinstance(v, dict) and "call" in v:
            func = v["call"]["func"]
            if isinstance(func, dict) and "attr" in func:
                func = func["attr"]["name"]
            args = [self._eval_value(a) for a in v["call"]["args"]]
            return self._call(func, args)
        if isinstance(v, dict) and "binop" in v:
            op = v["binop"]["op"]
            left = self._eval_value(v["binop"]["left"]) 
            right = self._eval_value(v["binop"]["right"]) 
            return self._apply_binop(op, left, right)
        if isinstance(v, dict) and "boolop" in v:
            op = v["boolop"]["op"]
            vals = [self._eval_value(x) for x in v["boolop"]["values"]]
            if op == "and":
                out = True
                for x in vals:
                    out = out and bool(x)
                return out
            if op == "or":
                out = False
                for x in vals:
                    out = out or bool(x)
                return out
            raise InterpreterError(f"unsupported boolop: {op}")
        if isinstance(v, dict) and "unary" in v:
            op = v["unary"]["op"]
            operand = self._eval_value(v["unary"]["operand"])
            if op == "usub":
                return -operand
            if op == "not":
                return not operand
            if op == "uadd":
                return +operand
            raise InterpreterError(f"unsupported unary: {op}")
        if isinstance(v, dict) and "compare" in v:
            left = self._eval_value(v["compare"]["left"]) 
            ops = v["compare"]["ops"]
            comps = [self._eval_value(c) for c in v["compare"]["comparators"]]
            cur = left
            ok = True
            for op, comp in zip(ops, comps):
                if op == "eq":
                    ok = ok and (cur == comp)
                elif op == "noteq":
                    ok = ok and (cur != comp)
                elif op == "lt":
                    ok = ok and (cur < comp)
                elif op == "lte":
                    ok = ok and (cur <= comp)
                elif op == "gt":
                    ok = ok and (cur > comp)
                elif op == "gte":
                    ok = ok and (cur >= comp)
                else:
                    ok = False
                cur = comp
            return ok
        if isinstance(v, dict) and "var" in v:
            return self._env_get(v["var"])
        if isinstance(v, list):
            return [self._eval_value(e) for e in v]
        if isinstance(v, tuple):
            return tuple(self._eval_value(e) for e in v)
        if isinstance(v, str):
            return v
        return v

    def _apply_binop(self, op: str, left: Any, right: Any) -> Any:
        if op == "add":
            return left + right
        if op == "sub":
            return left - right
        if op == "mult":
            return left * right
        if op == "div":
            return left / right
        if op == "mod":
            return left % right
        if op == "pow":
            return left ** right
        return None

def execute_program(program) -> ExecResult:
    intr = Interpreter()
    return intr.execute(program)
