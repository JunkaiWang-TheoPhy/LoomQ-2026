"""Official target-IR emitters for the LoomQ adapter contract."""

from __future__ import annotations

from typing import Callable, Dict, List

from .qasm import Circuit, Gate, Measurement


def _parameter(gate: Gate) -> str:
    if gate.parameter is None:
        raise ValueError(f"gate {gate.name} has no parameter")
    return repr(gate.parameter)


def emit_spinq(circuit: Circuit) -> str:
    return circuit.to_qasm2()


def emit_braket(circuit: Circuit) -> str:
    lines = [
        "OPENQASM 3.0;",
        'include "stdgates.inc";',
        f"qubit[{circuit.num_qubits}] q;",
        f"bit[{circuit.num_clbits}] c;",
    ]
    gate_names = {"cx": "cnot", "cu1": "cp"}
    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            lines.append(f"c[{operation.clbit}] = measure q[{operation.qubit}];")
            continue
        name = gate_names.get(operation.name, operation.name)
        parameter = f"({_parameter(operation)})" if operation.parameter is not None else ""
        operands = ",".join(f"q[{index}]" for index in operation.qubits)
        lines.append(f"{name}{parameter} {operands};")
    return "\n".join(lines) + "\n"


def emit_originq(circuit: Circuit) -> str:
    lines = [f"QINIT {circuit.num_qubits}", f"CREG {circuit.num_clbits}"]
    gate_names = {
        "sdg": "SDAG",
        "tdg": "TDAG",
        "cx": "CNOT",
        "cu1": "CR",
        "ccx": "TOFFOLI",
    }
    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            lines.append(f"MEASURE q[{operation.qubit}],c[{operation.clbit}]")
            continue
        name = gate_names.get(operation.name, operation.name.upper())
        operands = ",".join(f"q[{index}]" for index in operation.qubits)
        if operation.parameter is None:
            lines.append(f"{name} {operands}")
        else:
            lines.append(f"{name} {operands},({_parameter(operation)})")
    return "\n".join(lines) + "\n"


_EMITTERS: Dict[str, Callable[[Circuit], str]] = {
    "spinq": emit_spinq,
    "originq": emit_originq,
    "braket": emit_braket,
}


def emit(circuit: Circuit, target: str) -> str:
    try:
        emitter = _EMITTERS[target]
    except KeyError as exc:
        raise ValueError(f"unsupported target: {target}") from exc
    return emitter(circuit)
