"""Deterministic certificates for exact Hybrid-QASM branch-path replay."""

from __future__ import annotations

import hashlib
import json
from itertools import product
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from .hybrid import _statement_measurements, parse_hybrid
from .hybrid_trace import trace_hybrid
from .simulator import probabilities


HYBRID_PATH_CERTIFICATE_SCHEMA = "loomq-hybrid-path-certificate-v1"
MAX_PROJECTED_MEASUREMENT_BITS = 12


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _audit_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _with_integrity(payload: dict[str, Any]) -> dict[str, Any]:
    body = dict(payload)
    body["integrity"] = {
        "algorithm": "sha256",
        "scope": "content-addressed-canonical-json-without-integrity-or-verification",
        "audit_sha256": _audit_sha256(payload),
        "is_signature": False,
        "note": "This digest is an integrity checksum only; it does not authenticate authorship.",
    }
    return body


def _referenced_measurement_bits(statements: Sequence[object]) -> list[int]:
    registers: set[int] = set()
    for statement in statements:
        for register in _statement_measurements(statement):
            if register < 10:
                continue
            registers.add(register - 10)
    return sorted(registers)


def _projected_assignment_key(assignment: Sequence[int]) -> tuple[int, ...]:
    return tuple(int(bit) for bit in assignment)


def _full_measurement_bits(
    projection: Sequence[int], projected_bits: Sequence[int], width: int
) -> list[int]:
    bits = [0] * width
    for index, value in zip(projected_bits, projection, strict=True):
        bits[index] = value
    return bits


def _project_distribution(
    distribution: Dict[str, float], width: int, projected_bits: Sequence[int]
) -> Dict[tuple[int, ...], float]:
    projected: Dict[tuple[int, ...], float] = {}
    for key, probability in distribution.items():
        bits = [int(key[width - 1 - index]) for index in range(width)]
        projection = tuple(bits[index] for index in projected_bits)
        projected[projection] = projected.get(projection, 0.0) + probability
    return projected


def _terminal_registers(registers: Dict[str, Any]) -> dict[str, Any]:
    return {key: registers[key] for key in sorted(registers)}


def build_hybrid_path_certificate(hybrid_qasm_str: str) -> dict[str, Any]:
    circuit, statements = parse_hybrid(hybrid_qasm_str)
    projected_bits = _referenced_measurement_bits(statements)
    if len(projected_bits) > MAX_PROJECTED_MEASUREMENT_BITS:
        raise ValueError(
            f"hybrid path certificates are limited to {MAX_PROJECTED_MEASUREMENT_BITS} referenced measurement bits"
        )

    distribution = probabilities(circuit)
    projected_distribution = _project_distribution(
        distribution, circuit.num_clbits, projected_bits
    )

    path_buckets: Dict[str, Dict[str, Any]] = {}
    unreachable_outcomes: list[dict[str, Any]] = []

    for assignment in product((0, 1), repeat=len(projected_bits)):
        full_bits = _full_measurement_bits(assignment, projected_bits, circuit.num_clbits)
        trace = trace_hybrid(hybrid_qasm_str, full_bits)
        branch_path = trace["branch_path"]
        probability = projected_distribution.get(_projected_assignment_key(assignment), 0.0)
        bucket = path_buckets.setdefault(
            branch_path,
            {
                "probability": 0.0,
                "measurement_outcomes": [],
                "terminal_registers": {},
                "branch_events": trace["branch_events"],
                "representative_final_registers": trace["final_registers"],
            },
        )
        bucket["probability"] += probability
        bucket["measurement_outcomes"].append(
            {
                "measurement_bits": list(assignment),
                "probability": probability,
            }
        )
        registers_key = _canonical_json(_terminal_registers(trace["final_registers"]))
        bucket["terminal_registers"][registers_key] = bucket["terminal_registers"].get(
            registers_key, 0.0
        ) + probability
        if probability == 0.0:
            unreachable_outcomes.append(
                {
                    "measurement_bits": list(assignment),
                    "branch_path": branch_path,
                    "probability": 0.0,
                }
            )

    path_probabilities = []
    for branch_path in sorted(path_buckets):
        bucket = path_buckets[branch_path]
        if bucket["probability"] <= 0.0:
            continue
        path_probabilities.append(
            {
                "branch_path": branch_path,
                "probability": round(bucket["probability"], 15),
                "measurement_outcomes": sorted(
                    bucket["measurement_outcomes"],
                    key=lambda item: (item["measurement_bits"], item["probability"]),
                ),
                "terminal_registers": [
                    {
                        "registers": json.loads(registers_key),
                        "probability": round(probability, 15),
                    }
                    for registers_key, probability in sorted(
                        bucket["terminal_registers"].items(), key=lambda item: item[0]
                    )
                ],
                "branch_events": bucket["branch_events"],
                "representative_final_registers": bucket["representative_final_registers"],
            }
        )

    payload = {
        "schema_version": HYBRID_PATH_CERTIFICATE_SCHEMA,
        "source_sha256": _sha256(hybrid_qasm_str),
        "inputs": {"hybrid_source": hybrid_qasm_str},
        "projected_measurement_bits": projected_bits,
        "projection": {
            "projected_measurement_bits": projected_bits,
            "enumeration_limit": MAX_PROJECTED_MEASUREMENT_BITS,
            "projected_outcomes": 1 << len(projected_bits),
            "exact_distribution_support": len(distribution),
        },
        "path_probabilities": path_probabilities,
        "unreachable_outcomes": sorted(
            unreachable_outcomes,
            key=lambda item: (item["measurement_bits"], item["branch_path"]),
        ),
    }
    return _with_integrity(payload)


def verify_hybrid_path_certificate(certificate: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(certificate, dict):
        return {"valid": False, "reason": "certificate must be a dictionary"}
    if certificate.get("schema_version") != HYBRID_PATH_CERTIFICATE_SCHEMA:
        return {"valid": False, "reason": "schema_version mismatch"}
    integrity = certificate.get("integrity")
    if not isinstance(integrity, dict):
        return {"valid": False, "reason": "missing integrity block"}
    declared_sha = integrity.get("audit_sha256")
    if not isinstance(declared_sha, str):
        return {"valid": False, "reason": "missing integrity.audit_sha256"}

    payload = {
        key: value for key, value in certificate.items() if key not in {"integrity", "verification"}
    }
    computed_sha = _audit_sha256(payload)
    if computed_sha != declared_sha:
        return {
            "valid": False,
            "reason": "integrity checksum mismatch",
            "expected_audit_sha256": computed_sha,
            "observed_audit_sha256": declared_sha,
        }

    try:
        rebuilt = build_hybrid_path_certificate(certificate["inputs"]["hybrid_source"])
    except Exception as exc:  # pragma: no cover - defensive verifier path
        return {"valid": False, "reason": f"rebuild failed: {exc}"}

    normalized = {key: value for key, value in certificate.items() if key != "verification"}
    if rebuilt != normalized:
        return {
            "valid": False,
            "reason": "recomputed certificate mismatch",
            "expected_audit_sha256": rebuilt["integrity"]["audit_sha256"],
            "observed_audit_sha256": declared_sha,
        }
    return {"valid": True, "audit_sha256": declared_sha}
