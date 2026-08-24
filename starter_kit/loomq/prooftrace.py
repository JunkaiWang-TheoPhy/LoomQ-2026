"""Proof-carrying, semantics-preserving compilation for LoomQ circuits."""

from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Tuple

from .emitters import emit
from .native_ir import verify_native_ir
from .qasm import Circuit, Gate, Measurement, Operation, parse_qasm


PROOFTRACE_SCHEMA = "loomq-prooftrace-v1"
SUPPORTED_TARGETS = ("spinq", "originq", "braket")
_SELF_INVERSE = {"h", "x", "cx", "swap", "ccx"}
_INVERSES = {
    ("s", "sdg"),
    ("sdg", "s"),
    ("t", "tdg"),
    ("tdg", "t"),
}
_ROTATIONS = {"rz", "ry", "cu1"}


AnnotatedOperation = Tuple[Operation, List[int]]


def _operation_payload(operation: Operation) -> Dict[str, object]:
    if isinstance(operation, Measurement):
        return {
            "kind": "measurement",
            "qubit": operation.qubit,
            "clbit": operation.clbit,
        }
    return {
        "kind": "gate",
        "name": operation.name,
        "qubits": list(operation.qubits),
        "parameter": operation.parameter,
    }


def _rewrite(previous: Gate, current: Gate) -> Tuple[str, Gate | None] | None:
    if previous.qubits != current.qubits:
        return None
    if previous.name == current.name and previous.name in _SELF_INVERSE:
        return "cancel-self-inverse", None
    if (previous.name, current.name) in _INVERSES:
        return "cancel-inverse", None
    if previous.name == current.name and previous.name in _ROTATIONS:
        assert previous.parameter is not None and current.parameter is not None
        parameter = previous.parameter + current.parameter
        if not math.isfinite(parameter):
            return None
        if parameter == 0.0:
            return "cancel-zero-rotation", None
        return "merge-rotations", Gate(previous.name, previous.qubits, parameter)
    return None


def optimize_circuit(circuit: Circuit) -> Tuple[Circuit, List[Dict[str, object]], List[List[int]]]:
    """Apply only recorded adjacent identities and preserve source-operation lineage."""
    optimized: List[AnnotatedOperation] = []
    rewrites: List[Dict[str, object]] = []

    for source_index, operation in enumerate(circuit.operations):
        if isinstance(operation, Gate) and optimized and isinstance(optimized[-1][0], Gate):
            previous, previous_sources = optimized[-1]
            assert isinstance(previous, Gate)
            result = _rewrite(previous, operation)
            if result is not None:
                rule, replacement = result
                source_indices = [*previous_sources, source_index]
                optimized.pop()
                rewrites.append(
                    {
                        "rule": rule,
                        "source_operation_indices": source_indices,
                        "before": [
                            _operation_payload(previous),
                            _operation_payload(operation),
                        ],
                        "after": [] if replacement is None else [_operation_payload(replacement)],
                    }
                )
                if replacement is not None:
                    optimized.append((replacement, source_indices))
                continue
        optimized.append((operation, [source_index]))

    operations = [operation for operation, _sources in optimized]
    lineage = [sources for _operation, sources in optimized]
    return Circuit(circuit.num_qubits, circuit.num_clbits, operations), rewrites, lineage


def _metrics(circuit: Circuit) -> Dict[str, int]:
    gate_count = 0
    two_qubit_gate_count = 0
    multi_qubit_gate_count = 0
    qubit_depth = [0] * circuit.num_qubits
    for operation in circuit.operations:
        if not isinstance(operation, Gate):
            continue
        gate_count += 1
        if len(operation.qubits) == 2:
            two_qubit_gate_count += 1
        if len(operation.qubits) >= 2:
            multi_qubit_gate_count += 1
        layer = max(qubit_depth[index] for index in operation.qubits) + 1
        for index in operation.qubits:
            qubit_depth[index] = layer
    return {
        "gate_count": gate_count,
        "depth": max(qubit_depth, default=0),
        "two_qubit_gate_count": two_qubit_gate_count,
        "multi_qubit_gate_count": multi_qubit_gate_count,
        "measurement_count": sum(
            isinstance(operation, Measurement) for operation in circuit.operations
        ),
    }


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compile_target(qasm_str: str, target: str) -> str:
    """Preserve source operations and verify only the explicitly requested backend."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target: {target}")
    source = parse_qasm(qasm_str)
    native_ir = emit(source, target)
    verify_native_ir(source, native_ir, target)
    return native_ir


def compile_with_proof(qasm_str: str, target: str) -> Tuple[str, Dict[str, object]]:
    """Compile one target and return a deterministic cross-target proof certificate."""
    if target not in SUPPORTED_TARGETS:
        raise ValueError(f"unsupported target: {target}")
    source = parse_qasm(qasm_str)
    optimized, rewrites, lineage = optimize_circuit(source)
    optimized_qasm = optimized.to_qasm2()

    native_outputs: Dict[str, str] = {}
    portability: Dict[str, Dict[str, object]] = {}
    for candidate_target in SUPPORTED_TARGETS:
        native_ir = emit(optimized, candidate_target)
        verify_native_ir(optimized, native_ir, candidate_target)
        native_outputs[candidate_target] = native_ir
        portability[candidate_target] = {
            "roundtrip_verified": True,
            "native_ir_sha256": _sha256(native_ir),
        }

    certificate: Dict[str, object] = {
        "schema_version": PROOFTRACE_SCHEMA,
        "selected_target": target,
        "source_sha256": _sha256(qasm_str),
        "optimized_qasm_sha256": _sha256(optimized_qasm),
        "equivalence": {
            "verified": True,
            "method": "verified-local-rewrites-v1",
            "scope": "universal-unitary-identities-with-unchanged-measurement-map",
            "measurement_sequence_preserved": [
                operation
                for operation in source.operations
                if isinstance(operation, Measurement)
            ]
            == [
                operation
                for operation in optimized.operations
                if isinstance(operation, Measurement)
            ],
        },
        "metrics": {
            "source": _metrics(source),
            "optimized": _metrics(optimized),
        },
        "rewrites": rewrites,
        "lineage": [
            {
                "optimized_operation_index": index,
                "kind": "measurement" if isinstance(operation, Measurement) else "gate",
                "operation": _operation_payload(operation),
                "source_operation_indices": source_indices,
            }
            for index, (operation, source_indices) in enumerate(
                zip(optimized.operations, lineage)
            )
        ],
        "portability": portability,
    }
    return native_outputs[target], certificate
