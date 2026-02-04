# Parser-Driven Execution Engine

## Integration Points

- Parser: [hc_parser.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/app/parser/hc_parser.py)
- Interpreter: [interpreter.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/app/engine/interpreter.py)
- Engine Adapter: [adapter.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/app/engine/adapter.py)
- API Routes: [engine.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/app/routers/engine.py), [execution.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/app/routers/execution.py)

## Execution Flow

- Source code parses to `HCProgram` via `parse(code)`.
- Interpreter walks `HCNode` tree and evaluates constructs.
- Builtins include `print`, writing to an internal buffer joined by newlines.
- Adapter internal path uses interpreter as a fallback before CLI when engine package is unavailable.
- Results return `{stdout, stderr, exit_code}` with friendly errors for unsupported or undefined constructs.

## AST Structure

- Program: `HCProgram(body: List[HCNode])`
- Nodes: `kind`, `value`, `children` (optional), with location info.
- Expressions map to dictionaries: `{"call": {"func": name|attr, "args": [...]}}`.
- Names encode as `{"var": name}` to distinguish from string literals.
- Operators:
  - Binary: `{"binop": {"op": name, "left": v, "right": v}}`
  - Boolean: `{"boolop": {"op": "and"|"or", "values": [..]}}`
  - Unary: `{"unary": {"op": "usub"|"uadd"|"not", "operand": v}}`
  - Compare: `{"compare": {"left": v, "ops": [..], "comparators": [..]}}`
- Control flow:
  - `if` with children body/orelse.
  - `while`, `for` with body/orelse.
  - `break`, `continue`, `return` signals.
  - `match` cases for switch-like semantics.

## State Management

- Environments: stack of dicts with globals at base.
- Variable assignment writes into current scope.
- Function declarations store `{name, args, body}`; calls push a new scope and support `return`.

## Error Handling

- `InterpreterError("undefined name: X")` for missing variables.
- `InterpreterError("unsupported node: K")` for unimplemented constructs.
- Execution returns `exit_code=1` on errors with `stderr` populated.

## Test Suites

- Constructs: [test_interpreter_constructs.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/tests/unit/test_interpreter_constructs.py)
- Errors: [test_interpreter_errors.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/tests/unit/test_interpreter_errors.py)
- Performance: [test_interpreter_perf.py](file:///c:/Users/Lyndz/Downloads/HyperCode-V2.0/HyperCode-V2.0/THE%20HYPERCODE/hypercode-core/tests/perf/test_interpreter_perf.py)

## Architectural Decisions

- Python `ast` drives v0.1 to minimize complexity and keep tests fast.
- `{"var": name}` encoding separates identifiers from string constants.
- Interpreter integrates as adapter fallback to preserve existing CLI/test behaviors.
- Control flow and operators implemented incrementally with explicit mappings for clarity.

