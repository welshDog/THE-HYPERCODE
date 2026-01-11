from dataclasses import dataclass
from typing import List, Union, Optional, Any

@dataclass
class Node:
    pass

@dataclass
class Expr(Node):
    pass

@dataclass
class Literal(Expr):
    value: Any

@dataclass
class Variable(Expr):
    name: str

@dataclass
class BinaryOp(Expr):
    left: Expr
    op: str
    right: Expr

@dataclass
class Statement(Node):
    pass

@dataclass
class DataDecl(Statement):
    name: str
    value: Expr

@dataclass
class SetStmt(Statement):
    name: str
    value: Expr

@dataclass
class PrintStmt(Statement):
    expr: Expr

@dataclass
class Block(Node):
    statements: List[Statement]

@dataclass
class CheckStmt(Statement):
    condition: Expr
    true_block: Block
    false_block: Optional[Block] = None

# --- Quantum Ops ---

@dataclass
class QubitRef(Expr):
    register: str
    index: int

@dataclass
class QRegDecl(Statement):
    name: str
    size: int
    is_quantum: bool = True  # True for QReg, False for CReg

@dataclass
class QGate(Statement):  # Changed from Node to Statement
    name: str
    qubits: List[QubitRef]
    params: List[Expr]

@dataclass
class QMeasure(Statement):  # Changed from Node to Statement
    qubit: QubitRef
    target: QubitRef

QuantumOp = Union[QGate, QMeasure]

@dataclass
class Directive(Statement):
    kind: str  # 'domain' or 'backend'
    value: str

@dataclass
class QuantumCircuitDecl(Statement):
    name: str
    body: List[Statement]  # Can contain QRegDecl, QGate, QMeasure

@dataclass
class Program(Node):
    statements: List[Statement]
