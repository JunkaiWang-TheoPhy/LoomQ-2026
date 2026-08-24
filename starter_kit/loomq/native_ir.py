"""Independent parsers and semantic round-trip checks for emitted target IR."""

from __future__ import annotations

import math
import re
from typing import Callable, Dict, List

from .qasm import (
    Circuit,
    GATE_ARITY,
    MAX_QASM_SOURCE_CHARS,
    MAX_REGISTER_BITS,
    PARAMETER_GATES,
    Gate,
    Measurement,
    parse_qasm,
)


def _size(match: re.Match[str] | None, label: str) -> int:
    if match is None:
        raise ValueError(f"missing or invalid {label} declaration")
    value = int(match.group(1))
    if not 1 <= value <= MAX_REGISTER_BITS:
        raise ValueError(f"{label} size must be 1..{MAX_REGISTER_BITS}")
    return value


def _parameter(raw: str | None, gate: str) -> float | None:
    if (gate in PARAMETER_GATES) != (raw is not None):
        expectation = "requires" if gate in PARAMETER_GATES else "does not accept"
        raise ValueError(f"native gate {gate} {expectation} a parameter")
    if raw is None:
        return None
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"invalid native gate parameter: {raw}") from exc
    if not math.isfinite(value):
        raise ValueError(f"non-finite native gate parameter: {raw}")
    return value


def _gate(name: str, raw_parameter: str | None, operands: str, qubits: int) -> Gate:
    if name not in GATE_ARITY:
        raise ValueError(f"unsupported native gate: {name}")
    raw_operands = [item.strip() for item in operands.split(",")]
    if len(raw_operands) != GATE_ARITY[name]:
        raise ValueError(f"native gate {name} expects {GATE_ARITY[name]} operands")
    indices: List[int] = []
    for operand in raw_operands:
        match = re.fullmatch(r"q\[(\d+)\]", operand)
        if match is None:
            raise ValueError(f"invalid native quantum operand: {operand}")
        index = int(match.group(1))
        if index >= qubits:
            raise ValueError(f"native quantum operand out of range: {operand}")
        indices.append(index)
    if len(set(indices)) != len(indices):
        raise ValueError(f"native gate {name} reuses a quantum operand")
    return Gate(name, tuple(indices), _parameter(raw_parameter, name))


def _measurement(qubit: int, clbit: int, qubits: int, clbits: int) -> Measurement:
    if qubit >= qubits or clbit >= clbits:
        raise ValueError("native measurement operand out of range")
    return Measurement(qubit, clbit)


def _parse_spinq(source: str) -> Circuit:
    return parse_qasm(source)


def _parse_braket(source: str) -> Circuit:
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if len(lines) < 4 or lines[0] != "OPENQASM 3.0;" or lines[1] != 'include "stdgates.inc";':
        raise ValueError("invalid Braket OpenQASM 3 header")
    qubits = _size(re.fullmatch(r"qubit\[(\d+)\]\s+q;", lines[2]), "Braket qubit")
    clbits = _size(re.fullmatch(r"bit\[(\d+)\]\s+c;", lines[3]), "Braket bit")
    operations: List[Gate | Measurement] = []
    aliases = {"cnot": "cx", "cp": "cu1"}
    for line in lines[4:]:
        measured = re.fullmatch(r"c\[(\d+)\]\s*=\s*measure\s+q\[(\d+)\];", line)
        if measured:
            operations.append(
                _measurement(int(measured.group(2)), int(measured.group(1)), qubits, clbits)
            )
            continue
        matched = re.fullmatch(r"([a-z][a-z0-9]*)(?:\(([^)]+)\))?\s+(.+);", line)
        if matched is None:
            raise ValueError(f"invalid Braket instruction: {line}")
        raw_name, raw_parameter, operands = matched.groups()
        operations.append(_gate(aliases.get(raw_name, raw_name), raw_parameter, operands, qubits))
    return Circuit(qubits, clbits, operations)


def _parse_originq(source: str) -> Circuit:
    lines = [line.strip() for line in source.splitlines() if line.strip()]
    if len(lines) < 2:
        raise ValueError("invalid OriginIR header")
    qubits = _size(re.fullmatch(r"QINIT\s+(\d+)", lines[0]), "OriginIR quantum")
    clbits = _size(re.fullmatch(r"CREG\s+(\d+)", lines[1]), "OriginIR classical")
    operations: List[Gate | Measurement] = []
    aliases = {
        "SDAG": "sdg",
        "TDAG": "tdg",
        "CNOT": "cx",
        "CR": "cu1",
        "CU1": "cu1",
        "TOFFOLI": "ccx",
        "CCX": "ccx",
    }
    for line in lines[2:]:
        measured = re.fullmatch(r"MEASURE\s+q\[(\d+)\],c\[(\d+)\]", line)
        if measured:
            operations.append(
                _measurement(int(measured.group(1)), int(measured.group(2)), qubits, clbits)
            )
            continue
        matched = re.fullmatch(r"([A-Z][A-Z0-9]*)\s+(.+)", line)
        if matched is None:
            raise ValueError(f"invalid OriginIR instruction: {line}")
        raw_name, body = matched.groups()
        parameter_match = re.search(r",\(([^)]+)\)$", body)
        raw_parameter = parameter_match.group(1) if parameter_match else None
        operands = body[: parameter_match.start()] if parameter_match else body
        name = aliases.get(raw_name, raw_name.lower())
        operations.append(_gate(name, raw_parameter, operands, qubits))
    return Circuit(qubits, clbits, operations)


_PARSERS: Dict[str, Callable[[str], Circuit]] = {
    "spinq": _parse_spinq,
    "originq": _parse_originq,
    "braket": _parse_braket,
}


def parse_native_ir(source: str, target: str) -> Circuit:
    if not isinstance(source, str) or not source.strip():
        raise ValueError("native IR must be a non-empty string")
    if len(source) > MAX_QASM_SOURCE_CHARS:
        raise ValueError(f"native IR is limited to {MAX_QASM_SOURCE_CHARS} characters")
    try:
        parser = _PARSERS[target]
    except KeyError as exc:
        raise ValueError(f"unsupported target: {target}") from exc
    return parser(source)


def verify_native_ir(expected: Circuit, source: str, target: str) -> None:
    observed = parse_native_ir(source, target)
    if observed != expected:
        raise ValueError(f"{target} native IR semantic mismatch after round-trip parsing")
