"""Parser for the bounded OpenQASM 2.0 subset used by LoomQ."""

from __future__ import annotations

import ast
import math
import operator
import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Sequence, Tuple, Union


GATE_ARITY = {
    "h": 1,
    "x": 1,
    "s": 1,
    "sdg": 1,
    "t": 1,
    "tdg": 1,
    "rz": 1,
    "ry": 1,
    "cx": 2,
    "cu1": 2,
    "swap": 2,
    "ccx": 3,
}
PARAMETER_GATES = {"rz", "ry", "cu1"}


class QASMError(ValueError):
    """Raised when source falls outside the published LoomQ contract."""


@dataclass(frozen=True)
class Gate:
    name: str
    qubits: Tuple[int, ...]
    parameter: float | None = None


@dataclass(frozen=True)
class Measurement:
    qubit: int
    clbit: int


Operation = Union[Gate, Measurement]


@dataclass
class Circuit:
    num_qubits: int
    num_clbits: int
    operations: List[Operation]

    def to_qasm2(self) -> str:
        lines = [
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            f"qreg q[{self.num_qubits}];",
            f"creg c[{self.num_clbits}];",
        ]
        for operation in self.operations:
            if isinstance(operation, Measurement):
                lines.append(f"measure q[{operation.qubit}] -> c[{operation.clbit}];")
                continue
            parameter = ""
            if operation.parameter is not None:
                parameter = f"({operation.parameter!r})"
            operands = ",".join(f"q[{index}]" for index in operation.qubits)
            lines.append(f"{operation.name}{parameter} {operands};")
        return "\n".join(lines) + "\n"


@dataclass(frozen=True)
class _Register:
    offset: int
    size: int


@dataclass(frozen=True)
class _Operand:
    indices: List[int]
    scalar: bool


_DECLARATION = re.compile(r"^(qreg|creg)\s+([A-Za-z_]\w*)\s*\[\s*(\d+)\s*\]$")
_MEASURE = re.compile(r"^measure\s+(.+?)\s*->\s*(.+)$", re.IGNORECASE)
_GATE = re.compile(
    r"^([A-Za-z_]\w*)\s*(?:\((.+)\))?\s+(.+)$", re.DOTALL
)
_REFERENCE = re.compile(r"^([A-Za-z_]\w*)(?:\s*\[\s*(\d+)\s*\])?$")


def _strip_comments(source: str) -> str:
    source = re.sub(r"/\*.*?\*/", "", source, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", "", source)


def _statements(source: str) -> Iterable[str]:
    for item in _strip_comments(source).split(";"):
        statement = item.strip()
        if statement:
            yield statement


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _evaluate_parameter(expression: str) -> float:
    try:
        tree = ast.parse(expression.replace("^", "**"), mode="eval")
    except SyntaxError as exc:
        raise QASMError(f"invalid gate parameter: {expression}") from exc

    def evaluate(node: ast.AST) -> float:
        if isinstance(node, ast.Expression):
            return evaluate(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.Name) and node.id == "pi":
            return math.pi
        if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
            return _BINARY_OPERATORS[type(node.op)](evaluate(node.left), evaluate(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
            return _UNARY_OPERATORS[type(node.op)](evaluate(node.operand))
        raise QASMError(f"invalid gate parameter: {expression}")

    value = evaluate(tree)
    if not math.isfinite(value):
        raise QASMError(f"non-finite gate parameter: {expression}")
    return value


def _resolve_reference(
    text: str, registers: Dict[str, _Register], register_kind: str
) -> _Operand:
    match = _REFERENCE.fullmatch(text.strip())
    if not match:
        raise QASMError(f"invalid {register_kind} operand: {text}")
    name, raw_index = match.groups()
    if name not in registers:
        raise QASMError(f"unknown {register_kind} register: {name}")
    register = registers[name]
    if raw_index is None:
        return _Operand(list(range(register.offset, register.offset + register.size)), False)
    index = int(raw_index)
    if index >= register.size:
        raise QASMError(f"{register_kind} index out of range: {text}")
    return _Operand([register.offset + index], True)


def _expand_operands(operands: Sequence[_Operand]) -> Iterable[Tuple[int, ...]]:
    widths = {len(operand.indices) for operand in operands if not operand.scalar}
    if len(widths) > 1:
        raise QASMError("gate register sizes must match")
    width = next(iter(widths), 1)
    if any(not operand.scalar and len(operand.indices) != width for operand in operands):
        raise QASMError("gate register sizes must match")
    for position in range(width):
        yield tuple(
            operand.indices[0] if operand.scalar else operand.indices[position]
            for operand in operands
        )


def parse_qasm(source: str) -> Circuit:
    """Parse and validate the contest's complete L1 input subset."""
    if not isinstance(source, str) or not source.strip():
        raise QASMError("QASM source must be a non-empty string")

    statements = list(_statements(source))
    if not statements or not re.fullmatch(
        r"OPENQASM\s+2\.0", " ".join(statements[0].split()), re.IGNORECASE
    ):
        raise QASMError("missing OPENQASM 2.0 declaration")

    qregs: Dict[str, _Register] = {}
    cregs: Dict[str, _Register] = {}
    qubit_count = 0
    clbit_count = 0
    operations: List[Operation] = []
    saw_version = False

    for statement in statements:
        normalized = " ".join(statement.split())
        if re.fullmatch(r"OPENQASM\s+2\.0", normalized, re.IGNORECASE):
            saw_version = True
            continue
        if re.fullmatch(r'include\s+["\']qelib1\.inc["\']', normalized, re.IGNORECASE):
            continue

        declaration = _DECLARATION.fullmatch(normalized)
        if declaration:
            kind, name, raw_size = declaration.groups()
            size = int(raw_size)
            if size <= 0:
                raise QASMError(f"{kind} size must be positive")
            registers = qregs if kind == "qreg" else cregs
            if name in qregs or name in cregs:
                raise QASMError(f"duplicate register: {name}")
            offset = qubit_count if kind == "qreg" else clbit_count
            registers[name] = _Register(offset, size)
            if kind == "qreg":
                qubit_count += size
            else:
                clbit_count += size
            continue

        measurement = _MEASURE.fullmatch(normalized)
        if measurement:
            qubits = _resolve_reference(measurement.group(1), qregs, "quantum").indices
            clbits = _resolve_reference(measurement.group(2), cregs, "classical").indices
            if len(qubits) != len(clbits):
                raise QASMError("measurement register sizes must match")
            operations.extend(Measurement(q, c) for q, c in zip(qubits, clbits))
            continue

        gate_match = _GATE.fullmatch(normalized)
        if not gate_match:
            raise QASMError(f"unsupported statement: {normalized}")
        raw_name, raw_parameter, raw_operands = gate_match.groups()
        name = raw_name.lower()
        if name not in GATE_ARITY:
            raise QASMError(f"unsupported gate: {raw_name}")
        if (name in PARAMETER_GATES) != (raw_parameter is not None):
            expectation = "requires" if name in PARAMETER_GATES else "does not accept"
            raise QASMError(f"gate {name} {expectation} a parameter")
        operand_parts = [part.strip() for part in raw_operands.split(",")]
        if len(operand_parts) != GATE_ARITY[name]:
            raise QASMError(f"gate {name} expects {GATE_ARITY[name]} operand(s)")
        resolved = [_resolve_reference(part, qregs, "quantum") for part in operand_parts]
        parameter = _evaluate_parameter(raw_parameter) if raw_parameter is not None else None
        for qubits in _expand_operands(resolved):
            if len(set(qubits)) != len(qubits):
                raise QASMError(f"gate {name} cannot reuse a qubit operand")
            operations.append(Gate(name, qubits, parameter))

    if not saw_version:
        raise QASMError("missing OPENQASM 2.0 declaration")
    if not qregs:
        raise QASMError("at least one qreg is required")
    if not cregs:
        raise QASMError("at least one creg is required")
    return Circuit(qubit_count, clbit_count, operations)
