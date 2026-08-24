"""Exact bounded whole-circuit semantic equivalence certificates."""

from __future__ import annotations

import cmath
import hashlib
import json
import math
from typing import Any, Mapping, Sequence

from .qasm import Circuit, Gate, Measurement
from .simulator import _apply_gate


SCHEMA_VERSION = "loomq-semantic-equivalence-v1"
METHOD = "complete-unitary-column-comparison-v1"
_MAX_SUPPORTED_QUBITS = 8


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _normalized_float(value: float, *, tolerance: float = 1e-15) -> float:
    if abs(value) <= tolerance:
        return 0.0
    return float(value)


def _phase_payload(phase: complex) -> dict[str, float]:
    return {
        "real": _normalized_float(phase.real),
        "imag": _normalized_float(phase.imag),
    }


def _measurement_map(circuit: Circuit) -> list[dict[str, int]]:
    return [
        {"qubit": operation.qubit, "clbit": operation.clbit}
        for operation in circuit.operations
        if isinstance(operation, Measurement)
    ]


def _gate_sequence(circuit: Circuit) -> list[Gate]:
    gates: list[Gate] = []
    measurement_seen = False
    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            measurement_seen = True
            continue
        if measurement_seen:
            raise ValueError("mid-circuit measurement is outside the LoomQ L1 contract")
        gates.append(operation)
    return gates


def _validate_bounds(max_qubits: int, tolerance: float) -> None:
    if not isinstance(max_qubits, int) or isinstance(max_qubits, bool) or max_qubits <= 0:
        raise ValueError("max_qubits must be a positive integer")
    if max_qubits > _MAX_SUPPORTED_QUBITS:
        raise ValueError(
            f"whole-circuit semantic equivalence supports at most {_MAX_SUPPORTED_QUBITS} qubits"
        )
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        raise ValueError("tolerance must be a positive finite number")
    if not math.isfinite(float(tolerance)) or float(tolerance) <= 0.0:
        raise ValueError("tolerance must be a positive finite number")


def _validate_circuit_pair(reference: Circuit, candidate: Circuit, max_qubits: int) -> None:
    _gate_sequence(reference)
    _gate_sequence(candidate)
    if reference.num_qubits > max_qubits or candidate.num_qubits > max_qubits:
        raise ValueError(f"whole-circuit semantic equivalence supports at most {max_qubits} qubits")


def _simulate_column(num_qubits: int, gates: Sequence[Gate], basis_index: int) -> list[complex]:
    state = [0j] * (1 << num_qubits)
    state[basis_index] = 1 + 0j
    for gate in gates:
        _apply_gate(state, gate)
    return state


def _matrix_columns(circuit: Circuit) -> list[list[complex]]:
    gates = _gate_sequence(circuit)
    return [
        _simulate_column(circuit.num_qubits, gates, basis_index)
        for basis_index in range(1 << circuit.num_qubits)
    ]


def _largest_anchor(reference_columns: Sequence[Sequence[complex]]) -> tuple[int, int, complex]:
    anchor_column = 0
    anchor_row = 0
    anchor = 0j
    anchor_abs = -1.0
    for column_index, column in enumerate(reference_columns):
        for row_index, amplitude in enumerate(column):
            magnitude = abs(amplitude)
            if magnitude > anchor_abs:
                anchor_abs = magnitude
                anchor = amplitude
                anchor_row = row_index
                anchor_column = column_index
    return anchor_row, anchor_column, anchor


def _safe_phase(reference_anchor: complex, candidate_anchor: complex) -> complex:
    if abs(reference_anchor) == 0.0:
        return 1 + 0j
    phase = candidate_anchor / reference_anchor
    magnitude = abs(phase)
    if magnitude == 0.0:
        return 1 + 0j
    return phase / magnitude


def _align_state(reference_state: Sequence[complex], candidate_state: Sequence[complex]) -> tuple[complex, list[complex]]:
    anchor_index = next((index for index, amplitude in enumerate(reference_state) if abs(amplitude) > 1e-15), None)
    if anchor_index is None:
        return 1 + 0j, [complex(amplitude) for amplitude in candidate_state]
    phase = _safe_phase(reference_state[anchor_index], candidate_state[anchor_index])
    aligned = [amplitude / phase for amplitude in candidate_state]
    return phase, aligned


def _state_distance(reference_state: Sequence[complex], candidate_state: Sequence[complex]) -> tuple[complex, float]:
    phase, aligned = _align_state(reference_state, candidate_state)
    distance = math.sqrt(sum(abs(left - right) ** 2 for left, right in zip(reference_state, aligned)))
    return phase, _normalized_float(distance)


def _operational_counterexample(
    reference_columns: Sequence[Sequence[complex]],
    candidate_columns: Sequence[Sequence[complex]],
    tolerance: float,
) -> dict[str, Any] | None:
    dimension = len(reference_columns)
    for basis_index, (reference_state, candidate_state) in enumerate(
        zip(reference_columns, candidate_columns)
    ):
        phase, distance = _state_distance(reference_state, candidate_state)
        if distance > tolerance:
            return {
                "state_family": "basis",
                "basis_state": basis_index,
                "state_distance": distance,
                "phase": _phase_payload(phase),
            }

    inv_sqrt_two = 1 / math.sqrt(2)
    for left in range(dimension):
        for right in range(left + 1, dimension):
            combinations = (
                ("plus", 1 + 0j),
                ("plus_i", 1j),
            )
            for family, coefficient in combinations:
                reference_state = [
                    inv_sqrt_two
                    * (reference_columns[left][row] + coefficient * reference_columns[right][row])
                    for row in range(len(reference_columns[left]))
                ]
                candidate_state = [
                    inv_sqrt_two
                    * (candidate_columns[left][row] + coefficient * candidate_columns[right][row])
                    for row in range(len(candidate_columns[left]))
                ]
                phase, distance = _state_distance(reference_state, candidate_state)
                if distance > tolerance:
                    return {
                        "state_family": family,
                        "basis_pair": [left, right],
                        "state_distance": distance,
                        "phase": _phase_payload(phase),
                    }
    return None


def _base_report(
    reference: Circuit,
    candidate: Circuit,
    *,
    max_qubits: int,
    tolerance: float,
) -> dict[str, Any]:
    measurements = _measurement_map(reference)
    return {
        "schema_version": SCHEMA_VERSION,
        "verified": False,
        "method": METHOD,
        "scope": {
            "max_qubits": max_qubits,
            "tolerance": float(tolerance),
        },
        "dimensions": {
            "num_qubits": reference.num_qubits,
            "num_clbits": reference.num_clbits,
            "unitary_dimension": 1 << reference.num_qubits,
        },
        "identical_measurement_map": _measurement_map(reference) == _measurement_map(candidate),
        "reference_measurements": measurements,
        "candidate_measurements": _measurement_map(candidate),
        "one_global_phase": {
            "consistent": False,
            "real": 1.0,
            "imag": 0.0,
        },
        "basis_columns_checked": 0,
        "amplitudes_checked": 0,
        "maximum_absolute_error": 0.0,
        "failing_entry": None,
        "operational_counterexample": None,
    }


def _finalize_report(report: dict[str, Any]) -> dict[str, Any]:
    body = dict(report)
    body.pop("integrity", None)
    finalized = dict(body)
    finalized["integrity"] = {"body_sha256": _sha256_json(body)}
    return finalized


def compare_circuit_semantics(
    reference: Circuit,
    candidate: Circuit,
    *,
    max_qubits: int = 8,
    tolerance: float = 1e-12,
) -> dict[str, Any]:
    _validate_bounds(max_qubits, tolerance)
    _validate_circuit_pair(reference, candidate, max_qubits)

    report = _base_report(reference, candidate, max_qubits=max_qubits, tolerance=tolerance)

    if (
        reference.num_qubits != candidate.num_qubits
        or reference.num_clbits != candidate.num_clbits
    ):
        report["reason"] = "register declarations differ"
        return _finalize_report(report)

    if not report["identical_measurement_map"]:
        report["reason"] = "measurement mappings differ"
        return _finalize_report(report)

    reference_columns = _matrix_columns(reference)
    candidate_columns = _matrix_columns(candidate)
    report["basis_columns_checked"] = len(reference_columns)
    report["amplitudes_checked"] = len(reference_columns) * len(reference_columns)
    anchor_row, anchor_column, reference_anchor = _largest_anchor(reference_columns)
    candidate_anchor = candidate_columns[anchor_column][anchor_row]
    phase = _safe_phase(reference_anchor, candidate_anchor)
    report["one_global_phase"] = {
        "consistent": True,
        **_phase_payload(phase),
    }

    maximum_error = 0.0
    failing_entry: dict[str, int] | None = None
    for column_index, (reference_column, candidate_column) in enumerate(
        zip(reference_columns, candidate_columns)
    ):
        for row_index, (reference_entry, candidate_entry) in enumerate(
            zip(reference_column, candidate_column)
        ):
            error = abs(reference_entry - candidate_entry / phase)
            if error > maximum_error:
                maximum_error = error
            if failing_entry is None and error > tolerance:
                failing_entry = {"row": row_index, "column": column_index}

    report["maximum_absolute_error"] = _normalized_float(maximum_error)
    report["failing_entry"] = failing_entry

    if failing_entry is None:
        report["verified"] = True
        return _finalize_report(report)

    report["verified"] = False
    report["one_global_phase"]["consistent"] = False
    report["reason"] = "no single global phase aligns every matrix entry"
    report["operational_counterexample"] = _operational_counterexample(
        reference_columns,
        candidate_columns,
        tolerance,
    )
    return _finalize_report(report)


def _require_positive_int(name: str, value: Any) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _require_positive_float(name: str, value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{name} must be a positive finite number")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise ValueError(f"{name} must be a positive finite number")
    return result


def verify_semantic_equivalence_certificate(
    reference: Circuit,
    candidate: Circuit,
    certificate: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(certificate, Mapping):
        return {
            "valid": False,
            "reason": "invalid schema: certificate must be a mapping",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    if certificate.get("schema_version") != SCHEMA_VERSION:
        return {
            "valid": False,
            "reason": "invalid schema: unsupported schema_version",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    scope = certificate.get("scope")
    if not isinstance(scope, Mapping):
        return {
            "valid": False,
            "reason": "invalid schema: scope must be a mapping",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    try:
        max_qubits = _require_positive_int("max_qubits", scope["max_qubits"])
        tolerance = _require_positive_float("tolerance", scope["tolerance"])
        _validate_bounds(max_qubits, tolerance)
    except (KeyError, TypeError, ValueError) as exc:
        return {
            "valid": False,
            "reason": f"invalid schema: {exc}",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    supplied_body = {key: value for key, value in certificate.items() if key != "integrity"}
    certificate_sha256 = _sha256_json(supplied_body)

    try:
        recomputed = compare_circuit_semantics(
            reference,
            candidate,
            max_qubits=max_qubits,
            tolerance=tolerance,
        )
    except Exception as exc:
        return {
            "valid": False,
            "reason": f"recomputation failed: {exc}",
            "certificate_sha256": certificate_sha256,
            "recomputed_sha256": "",
        }

    recomputed_body = {key: value for key, value in recomputed.items() if key != "integrity"}
    recomputed_sha256 = _sha256_json(recomputed_body)

    integrity = certificate.get("integrity")
    if not isinstance(integrity, Mapping):
        return {
            "valid": False,
            "reason": "invalid schema: integrity must be a mapping",
            "certificate_sha256": certificate_sha256,
            "recomputed_sha256": recomputed_sha256,
        }

    if integrity.get("body_sha256") != certificate_sha256:
        return {
            "valid": False,
            "reason": "semantic mismatch: certificate integrity does not match its body",
            "certificate_sha256": certificate_sha256,
            "recomputed_sha256": recomputed_sha256,
        }

    if supplied_body != recomputed_body:
        return {
            "valid": False,
            "reason": "semantic mismatch: certificate body does not match recomputed source semantics",
            "certificate_sha256": certificate_sha256,
            "recomputed_sha256": recomputed_sha256,
        }

    return {
        "valid": True,
        "reason": "ok",
        "certificate_sha256": certificate_sha256,
        "recomputed_sha256": recomputed_sha256,
    }
