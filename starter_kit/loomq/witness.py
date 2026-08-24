"""Deterministic causal witness chains for LoomQ proofs, mutations, and hybrid replay."""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .assertions import diagnose_mutation, evaluate_assertions
from .hybrid import parse_hybrid
from .hybrid_trace import trace_hybrid
from .prooftrace import compile_with_proof
from .qasm import Circuit, Gate, Measurement, Operation, parse_qasm


WITNESS_SCHEMA = "loomq-witness-chain-v1"


def _operation_payload(operation: Operation) -> dict[str, Any]:
    if isinstance(operation, Measurement):
        return {"kind": "measurement", "qubit": operation.qubit, "clbit": operation.clbit}
    return {
        "kind": "gate",
        "name": operation.name,
        "qubits": list(operation.qubits),
        "parameter": operation.parameter,
    }


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _audit_sha256(payload: dict[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _ordered_unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


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


def _split_witness_ids(reference: Circuit) -> tuple[list[str], list[str], list[dict[str, Any]], dict[int, str]]:
    gate_count = 0
    measurement_count = 0
    gate_ids: list[str] = []
    measurement_ids: list[str] = []
    index_rows: list[dict[str, Any]] = []
    clbit_to_measurement_id: dict[int, str] = {}
    for source_operation_index, operation in enumerate(reference.operations):
        if isinstance(operation, Measurement):
            measurement_count += 1
            witness_id = f"m{measurement_count}"
            measurement_ids.append(witness_id)
            clbit_to_measurement_id[operation.clbit] = witness_id
        else:
            gate_count += 1
            witness_id = f"g{gate_count}"
            gate_ids.append(witness_id)
        index_rows.append(
            {
                "source_operation_index": source_operation_index,
                "witness_id": witness_id,
                "operation": _operation_payload(operation),
            }
        )
    return gate_ids, measurement_ids, index_rows, clbit_to_measurement_id


def _source_index_to_witness(reference: Circuit) -> dict[int, str]:
    mapping: dict[int, str] = {}
    gate_count = 0
    measurement_count = 0
    for source_operation_index, operation in enumerate(reference.operations):
        if isinstance(operation, Measurement):
            measurement_count += 1
            mapping[source_operation_index] = f"m{measurement_count}"
        else:
            gate_count += 1
            mapping[source_operation_index] = f"g{gate_count}"
    return mapping


def _measurement_ids_for_assertion(
    report_item: dict[str, Any], clbit_to_measurement_id: dict[int, str]
) -> list[str]:
    if report_item["kind"] == "parity":
        bit_indices = report_item["bits"]
    else:
        bit_indices = list(range(len(report_item["states"][0])))
    return [
        clbit_to_measurement_id[index]
        for index in bit_indices
        if index in clbit_to_measurement_id
    ]


def _measurement_id_from_label(label: str, clbit_to_measurement_id: dict[int, str]) -> str | None:
    match = re.fullmatch(r"c\[(\d+)\]", label)
    if match is None:
        return None
    return clbit_to_measurement_id.get(int(match.group(1)))


def _quantum_circuits_match(reference: Circuit, hybrid_circuit: Circuit) -> bool:
    return (
        reference.num_qubits == hybrid_circuit.num_qubits
        and reference.num_clbits == hybrid_circuit.num_clbits
        and reference.operations == hybrid_circuit.operations
    )


def build_causal_audit(
    reference_qasm: str,
    candidate_qasm: str,
    assertions: list[dict],
    hybrid_source: str,
    measurement_bits: list[int],
    target: str,
) -> dict[str, Any]:
    reference = parse_qasm(reference_qasm)
    hybrid_circuit, _hybrid_statements = parse_hybrid(hybrid_source)
    if not _quantum_circuits_match(reference, hybrid_circuit):
        raise ValueError("hybrid quantum circuit must exactly match the reference circuit")

    source_witness_map = _source_index_to_witness(reference)
    gate_witness_ids, measurement_witness_ids, witness_index, clbit_to_measurement_id = (
        _split_witness_ids(reference)
    )

    _selected_native_ir, certificate = compile_with_proof(reference_qasm, target)
    mutation = diagnose_mutation(reference_qasm, candidate_qasm)
    assertion_report = evaluate_assertions(reference, assertions)
    hybrid_report = trace_hybrid(hybrid_source, measurement_bits)

    prooftrace_stage = {
        "stage": "prooftrace",
        "witness_ids": _ordered_unique(
            [
                source_witness_map[index]
                for item in certificate["lineage"]
                for index in item["source_operation_indices"]
                if index in source_witness_map
            ]
        ),
        "certificate": {
            "schema_version": certificate["schema_version"],
            "selected_target": certificate["selected_target"],
            "source_sha256": certificate["source_sha256"],
            "optimized_qasm_sha256": certificate["optimized_qasm_sha256"],
            "equivalence": certificate["equivalence"],
            "metrics": certificate["metrics"],
            "portability": certificate["portability"],
        },
        "lineage_aliases": [
            {
                "optimized_operation_index": item["optimized_operation_index"],
                "source_operation_indices": item["source_operation_indices"],
                "source_witness_ids": [
                    source_witness_map[index] for index in item["source_operation_indices"]
                ],
                "operation": item["operation"],
            }
            for item in certificate["lineage"]
        ],
        "rewrite_aliases": [
            {
                "rule": item["rule"],
                "source_operation_indices": item["source_operation_indices"],
                "source_witness_ids": [
                    source_witness_map[index] for index in item["source_operation_indices"]
                ],
                "before": item["before"],
                "after": item["after"],
            }
            for item in certificate["rewrites"]
        ],
    }

    divergence_witness_id = None
    if mutation["scope"] != "structural-mismatch" and mutation["first_divergent_gate"] is not None:
        divergence_index = mutation["first_divergent_gate"]
        if 0 <= divergence_index < len(gate_witness_ids):
            divergence_witness_id = gate_witness_ids[divergence_index]
    counterfactual_stage = {
        "stage": "counterfactual",
        "witness_ids": [] if divergence_witness_id is None else [divergence_witness_id],
        "counterfactual": dict(mutation, reference_witness_id=divergence_witness_id),
    }

    assertion_rows = []
    assertion_stage_witness_ids: list[str] = []
    for item in assertion_report:
        measurement_ids = _measurement_ids_for_assertion(item, clbit_to_measurement_id)
        assertion_stage_witness_ids.extend(measurement_ids)
        assertion_rows.append({**item, "measurement_witness_ids": measurement_ids})
    assertions_stage = {
        "stage": "assertions",
        "witness_ids": _ordered_unique(assertion_stage_witness_ids),
        "assertions": assertion_rows,
    }

    branch_events = []
    hybrid_stage_witness_ids: list[str] = []
    for event in hybrid_report["branch_events"]:
        measurement_ids = [
            measurement_id
            for measurement_id in (
                _measurement_id_from_label(label, clbit_to_measurement_id)
                for label in event["influencing_measurements"]
            )
            if measurement_id is not None
        ]
        hybrid_stage_witness_ids.extend(measurement_ids)
        branch_events.append({**event, "measurement_witness_ids": measurement_ids})
    hybrid_stage = {
        "stage": "hybrid",
        "witness_ids": _ordered_unique(hybrid_stage_witness_ids),
        "hybrid": {
            "schema_version": hybrid_report["schema_version"],
            "measurement_inputs": hybrid_report["measurement_inputs"],
            "loaded_measurement_inputs": hybrid_report["loaded_measurement_inputs"],
            "omitted_measurement_inputs": hybrid_report["omitted_measurement_inputs"],
            "quantum_operations": hybrid_report["quantum_operations"],
            "quantum_machine_trace": hybrid_report["quantum_machine_trace"],
            "quantum_machine_coverage": hybrid_report["quantum_machine_coverage"],
            "assembly": hybrid_report["assembly"],
            "branch_path": hybrid_report["branch_path"],
            "branch_events": branch_events,
            "final_registers": hybrid_report["final_registers"],
        },
    }

    payload = {
        "schema_version": WITNESS_SCHEMA,
        "inputs": {
            "reference_qasm": reference_qasm,
            "candidate_qasm": candidate_qasm,
            "assertions": assertions,
            "hybrid_source": hybrid_source,
            "measurement_bits": list(measurement_bits),
            "target": target,
        },
        "witness_index": {
            "source_operations": witness_index,
            "gate_witness_ids": gate_witness_ids,
            "measurement_witness_ids": measurement_witness_ids,
        },
        "witness_chain": [
            prooftrace_stage,
            counterfactual_stage,
            assertions_stage,
            hybrid_stage,
        ],
    }
    return _with_integrity(payload)


def verify_causal_audit(audit: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(audit, dict):
        return {"valid": False, "reason": "audit must be a dictionary"}
    if audit.get("schema_version") != WITNESS_SCHEMA:
        return {"valid": False, "reason": "schema_version mismatch"}
    integrity = audit.get("integrity")
    if not isinstance(integrity, dict):
        return {"valid": False, "reason": "missing integrity block"}
    declared_sha = integrity.get("audit_sha256")
    if not isinstance(declared_sha, str):
        return {"valid": False, "reason": "missing integrity.audit_sha256"}

    payload = {
        key: value
        for key, value in audit.items()
        if key not in {"integrity", "verification"}
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
        rebuilt = build_causal_audit(
            audit["inputs"]["reference_qasm"],
            audit["inputs"]["candidate_qasm"],
            audit["inputs"]["assertions"],
            audit["inputs"]["hybrid_source"],
            audit["inputs"]["measurement_bits"],
            audit["inputs"]["target"],
        )
    except Exception as exc:  # pragma: no cover - defensive verifier path
        return {"valid": False, "reason": f"rebuild failed: {exc}"}

    normalized_audit = {
        key: value for key, value in audit.items() if key != "verification"
    }
    if rebuilt != normalized_audit:
        return {
            "valid": False,
            "reason": "recomputed audit mismatch",
            "expected_audit_sha256": rebuilt["integrity"]["audit_sha256"],
            "observed_audit_sha256": declared_sha,
        }
    return {"valid": True, "audit_sha256": declared_sha}
