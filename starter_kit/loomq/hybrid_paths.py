"""Exact bounded mid-circuit measurement certificates for Hybrid-QASM."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import Any, Dict, List

try:
    from .hybrid import parse_hybrid
    from .hybrid_trace import trace_hybrid
    from .qasm import Circuit, Gate, Measurement
    from .simulator import (
        MAX_SIMULATOR_QUBITS,
        _apply_gate,
        _initial_state,
        _split_measurement_branches,
    )
except ImportError:
    from loomq.hybrid import parse_hybrid
    from loomq.hybrid_trace import trace_hybrid
    from loomq.qasm import Circuit, Gate, Measurement
    from loomq.simulator import (
        MAX_SIMULATOR_QUBITS,
        _apply_gate,
        _initial_state,
        _split_measurement_branches,
    )


HYBRID_PATH_CERTIFICATE_SCHEMA = "loomq-hybrid-path-certificate-v1"
DEFAULT_MAX_BRANCHES = 256
_NUMERICAL_DUST = 1e-15


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _require_positive_bound(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _classical_key(bits: List[int]) -> str:
    return "".join(str(bits[index]) for index in reversed(range(len(bits))))


def _outcome_bits(key: str) -> List[int]:
    return [int(bit) for bit in reversed(key)]


def _source_visible_registers(registers: Mapping[str, int]) -> Dict[str, int]:
    visible: Dict[str, int] = {}
    for name, value in registers.items():
        if not name.startswith("x"):
            continue
        index = int(name[1:])
        if 1 <= index <= 9:
            visible[name] = value
    return dict(sorted(visible.items()))


def measurement_branch_probabilities(
    circuit: Circuit, *, max_branches: int = DEFAULT_MAX_BRANCHES
) -> dict[str, float]:
    max_live_histories = _require_positive_bound("max_branches", max_branches)
    if circuit.num_qubits > MAX_SIMULATOR_QUBITS:
        raise ValueError(
            f"local statevector simulation supports at most {MAX_SIMULATOR_QUBITS} qubits"
        )

    if not any(isinstance(operation, Measurement) for operation in circuit.operations):
        raise ValueError("circuit must contain at least one measurement")

    histories: List[Dict[str, Any]] = [
        {
            "probability": 1.0,
            "state": _initial_state(circuit.num_qubits),
            "classical_bits": [0] * circuit.num_clbits,
        }
    ]

    for operation in circuit.operations:
        if isinstance(operation, Gate):
            for history in histories:
                _apply_gate(history["state"], operation)
            continue

        next_histories: List[Dict[str, Any]] = []
        for history in histories:
            for bit, branch_probability, collapsed_state in _split_measurement_branches(
                history["state"], operation.qubit
            ):
                classical_bits = list(history["classical_bits"])
                classical_bits[operation.clbit] = bit
                next_histories.append(
                    {
                        "probability": history["probability"] * branch_probability,
                        "state": collapsed_state,
                        "classical_bits": classical_bits,
                    }
                )
        histories = next_histories
        if len(histories) > max_live_histories:
            raise ValueError(
                f"max_branches={max_live_histories} is too small for exact live-history branching"
            )

    distribution: Dict[str, float] = {}
    for history in histories:
        if history["probability"] < _NUMERICAL_DUST:
            continue
        key = _classical_key(history["classical_bits"])
        distribution[key] = distribution.get(key, 0.0) + history["probability"]

    total = sum(distribution.values())
    if total <= 0:
        raise ValueError("simulation produced no measurable probability")
    normalized = {
        key: value / total
        for key, value in sorted(distribution.items())
        if value / total >= _NUMERICAL_DUST
    }
    normalized_total = sum(normalized.values())
    if normalized_total <= 0:
        raise ValueError("simulation produced no measurable probability")
    return {
        key: value / normalized_total
        for key, value in sorted(normalized.items())
    }


def certify_hybrid_paths(source: str, *, max_outcomes: int = 256) -> dict[str, Any]:
    max_paths = _require_positive_bound("max_outcomes", max_outcomes)
    circuit, _statements = parse_hybrid(source)
    outcome_count = 1 << circuit.num_clbits
    if outcome_count > max_paths:
        raise ValueError(
            f"exact hybrid path certification requires 2**num_clbits <= max_outcomes ({outcome_count} > {max_paths})"
        )

    probabilities = measurement_branch_probabilities(
        circuit, max_branches=max(DEFAULT_MAX_BRANCHES, max_paths)
    )
    outcomes: List[Dict[str, Any]] = []
    grouped: Dict[str, Dict[str, Any]] = {}
    for value in range(outcome_count):
        outcome = format(value, f"0{circuit.num_clbits}b")
        measurement_bits = _outcome_bits(outcome)
        replay = trace_hybrid(source, measurement_bits)
        probability = probabilities.get(outcome, 0.0)
        reachable = probability > 0.0
        branch_path = replay["branch_path"] or "root"
        final_registers = _source_visible_registers(replay["final_registers"])
        final_register_sha256 = _sha256_json(final_registers)
        outcome_entry = {
            "outcome": outcome,
            "probability": probability,
            "reachable": reachable,
            "path_id": branch_path,
            "branch_path": branch_path,
            "branch_events": replay["branch_events"],
            "final_registers": final_registers,
            "final_register_sha256": final_register_sha256,
        }
        outcomes.append(outcome_entry)

        group = grouped.setdefault(
            branch_path,
            {
                "path_id": branch_path,
                "total_probability": 0.0,
                "outcomes": [],
                "reachable_outcomes": [],
                "final_register_sha256s": set(),
            },
        )
        group["total_probability"] += probability
        group["outcomes"].append(outcome)
        if reachable:
            group["reachable_outcomes"].append(outcome)
        group["final_register_sha256s"].add(final_register_sha256)

    path_groups = []
    for path_id in sorted(grouped):
        group = grouped[path_id]
        path_groups.append(
            {
                "path_id": path_id,
                "total_probability": group["total_probability"],
                "outcomes": sorted(group["outcomes"]),
                "reachable_outcomes": sorted(group["reachable_outcomes"]),
                "final_register_sha256s": sorted(group["final_register_sha256s"]),
            }
        )

    body = {
        "schema_version": HYBRID_PATH_CERTIFICATE_SCHEMA,
        "source_sha256": _sha256_text(source),
        "scope": {
            "num_qubits": circuit.num_qubits,
            "num_clbits": circuit.num_clbits,
        },
        "limits": {
            "max_outcomes": max_paths,
        },
        "bit_order": "Outcome keys are ordered c[n-1]...c[0].",
        "outcomes": sorted(outcomes, key=lambda item: item["outcome"]),
        "path_groups": path_groups,
        "unreachable_outcomes": [
            item["outcome"] for item in outcomes if not item["reachable"]
        ],
        "dead_path_ids": [
            item["path_id"]
            for item in path_groups
            if not item["reachable_outcomes"]
        ],
    }
    certificate = dict(body)
    certificate["integrity"] = {"body_sha256": _sha256_json(body)}
    return certificate


def verify_hybrid_path_certificate(
    source: str, certificate: Mapping[str, Any]
) -> dict[str, Any]:
    if not isinstance(certificate, Mapping):
        return {
            "valid": False,
            "reason": "invalid schema: certificate must be a mapping",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    if certificate.get("schema_version") != HYBRID_PATH_CERTIFICATE_SCHEMA:
        return {
            "valid": False,
            "reason": "invalid schema: unsupported schema_version",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    if certificate.get("source_sha256") != _sha256_text(source):
        return {
            "valid": False,
            "reason": "source mismatch: certificate was not issued for this source",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    limits = certificate.get("limits")
    if not isinstance(limits, Mapping):
        return {
            "valid": False,
            "reason": "invalid schema: limits must be a mapping",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    try:
        stored_bound = _require_positive_bound("max_outcomes", limits["max_outcomes"])
    except (KeyError, ValueError, TypeError) as exc:
        return {
            "valid": False,
            "reason": f"invalid schema: {exc}",
            "certificate_sha256": "",
            "recomputed_sha256": "",
        }

    supplied_body = {key: value for key, value in certificate.items() if key != "integrity"}
    certificate_sha256 = _sha256_json(supplied_body)
    try:
        recomputed = certify_hybrid_paths(source, max_outcomes=stored_bound)
    except Exception as exc:  # Verification must fail closed for malformed claims.
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
