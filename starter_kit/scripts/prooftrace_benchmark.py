"""Deterministic mutation and rewrite benchmark for ProofTrace certificates."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Sequence

try:
    from .. import adapter
    from ..loomq.emitters import emit
    from ..loomq.native_ir import parse_native_ir, verify_native_ir
    from ..loomq.prooftrace import optimize_circuit
    from ..loomq.qasm import Circuit, Gate, Measurement, parse_qasm
    from ..loomq.semantic_equivalence import compare_circuit_semantics
except ImportError:  # Extracted starter_kit root.
    import adapter
    from loomq.emitters import emit
    from loomq.native_ir import parse_native_ir, verify_native_ir
    from loomq.prooftrace import optimize_circuit
    from loomq.qasm import Circuit, Gate, Measurement, parse_qasm
    from loomq.semantic_equivalence import compare_circuit_semantics


ROOT = Path(__file__).resolve().parents[1]
CIRCUIT_NAMES = (
    "bell.qasm",
    "ghz3.qasm",
    "deutsch_jozsa_balanced.qasm",
    "grover3.qasm",
    "qft4.qasm",
)
HEADER_LINES = {"spinq": 4, "originq": 2, "braket": 4}
EXPECTED_CORPUS_SHA256 = "2f8dedadd11c815acb89ef7e5dfc85292420c5a5df81b76bbb4c95ee9d4c8f49"
EXPECTED_MUTANTS = 225
EXPECTED_PORTABILITY_CHECKS = 15
EXPECTED_REWRITE_CHECKS = 132
REWRITE_PATTERNS = (
    (Gate("h", (0,)), Gate("h", (0,))),
    (Gate("x", (0,)), Gate("x", (0,))),
    (Gate("s", (0,)), Gate("sdg", (0,))),
    (Gate("t", (0,)), Gate("tdg", (0,))),
    (Gate("rz", (0,), 0.125), Gate("rz", (0,), -0.125)),
    (Gate("cx", (0, 1)), Gate("cx", (0, 1))),
    (Gate("swap", (0, 1)), Gate("swap", (0, 1))),
    (Gate("sdg", (0,)), Gate("s", (0,))),
)


def _variant(circuit: Circuit, pattern: Sequence[Gate]) -> str:
    insertion = next(
        (
            index
            for index, operation in enumerate(circuit.operations)
            if isinstance(operation, Measurement)
        ),
        len(circuit.operations),
    )
    operations = [
        *circuit.operations[:insertion],
        *pattern,
        *circuit.operations[insertion:],
    ]
    return Circuit(circuit.num_qubits, circuit.num_clbits, operations).to_qasm2()


def run_benchmark() -> dict:
    digest = hashlib.sha256()
    mutants: set[tuple[str, str, str]] = set()
    detected_mutants = 0
    false_accept_details: list[dict] = []
    semantic_checks = 0
    semantic_rejections = 0
    semantic_false_accept_details: list[dict] = []
    semantic_scope_skips: list[dict] = []
    portability_checks = 0
    rewrite_checks = 0
    failures: list[dict] = []

    for circuit_name in CIRCUIT_NAMES:
        source = (ROOT / "circuits" / circuit_name).read_text(encoding="utf-8")
        circuit = parse_qasm(source)
        optimized, _rewrites, _lineage = optimize_circuit(circuit)

        certificate = adapter.prooftrace(source, "spinq")
        for target, report in certificate["portability"].items():
            portability_checks += 1
            if not report["roundtrip_verified"]:
                failures.append(
                    {"circuit": circuit_name, "target": target, "kind": "portability"}
                )

        for target in adapter.SUPPORTED_TARGETS:
            native_ir = emit(optimized, target)
            verify_native_ir(optimized, native_ir, target)
            lines = native_ir.rstrip("\n").splitlines()
            for instruction_index in range(HEADER_LINES[target], len(lines)):
                mutated = "\n".join(
                    [*lines[:instruction_index], *lines[instruction_index + 1 :]]
                ) + "\n"
                mutants.add((circuit_name, target, mutated))

        patterns = REWRITE_PATTERNS
        if circuit.num_qubits >= 3:
            patterns = (
                *patterns,
                (Gate("ccx", (0, 1, 2)), Gate("ccx", (0, 1, 2))),
            )
        for pattern in patterns:
            redundant_source = _variant(circuit, pattern)
            for target in adapter.SUPPORTED_TARGETS:
                rewrite_checks += 1
                baseline_native, _baseline_proof = adapter.transpile_with_proof(
                    source, target
                )
                candidate_native, proof = adapter.transpile_with_proof(
                    redundant_source, target
                )
                if candidate_native != baseline_native or not proof["rewrites"]:
                    failures.append(
                        {
                            "circuit": circuit_name,
                            "target": target,
                            "kind": "rewrite",
                        }
                    )

    for circuit_name, target, mutated in sorted(mutants):
        descriptor = f"{circuit_name}\0{target}\0{mutated}"
        digest.update(descriptor.encode("utf-8"))
        source = (ROOT / "circuits" / circuit_name).read_text(encoding="utf-8")
        expected, _rewrites, _lineage = optimize_circuit(parse_qasm(source))
        try:
            verify_native_ir(expected, mutated, target)
        except ValueError:
            detected_mutants += 1
        else:
            if len(false_accept_details) < 20:
                false_accept_details.append(
                    {"circuit": circuit_name, "target": target, "kind": "delete-line"}
                )
        try:
            parsed = parse_native_ir(mutated, target)
            semantic_checks += 1
            semantic_report = compare_circuit_semantics(expected, parsed)
        except ValueError as exc:
            if len(semantic_scope_skips) < 20:
                semantic_scope_skips.append(
                    {
                        "circuit": circuit_name,
                        "target": target,
                        "kind": "delete-line",
                        "reason": str(exc),
                    }
                )
        else:
            if semantic_report["verified"]:
                if len(semantic_false_accept_details) < 20:
                    semantic_false_accept_details.append(
                        {"circuit": circuit_name, "target": target, "kind": "delete-line"}
                    )
            else:
                semantic_rejections += 1

    false_accepts = len(mutants) - detected_mutants
    semantic_false_accepts = semantic_checks - semantic_rejections
    return {
        "schema_version": "loomq-prooftrace-benchmark-v1",
        "circuit_count": len(CIRCUIT_NAMES),
        "total_mutants": len(mutants),
        "detected_mutants": detected_mutants,
        "false_accepts": false_accepts,
        "semantic_checks": semantic_checks,
        "semantic_rejections": semantic_rejections,
        "semantic_false_accepts": semantic_false_accepts,
        "semantic_false_accept_details": semantic_false_accept_details,
        "semantic_scope_skips": semantic_scope_skips,
        "portability_checks": portability_checks,
        "rewrite_checks": rewrite_checks,
        "corpus_sha256": digest.hexdigest(),
        "false_accept_details": false_accept_details,
        "failures": failures[:20],
        "passed": (
            false_accepts == 0
            and semantic_false_accepts == 0
            and not semantic_scope_skips
            and not failures
        ),
    }


def validate_report(report: dict) -> bool:
    """Bind benchmark claims to the committed corpus and exact check counts."""
    return bool(
        report.get("schema_version") == "loomq-prooftrace-benchmark-v1"
        and report.get("corpus_sha256") == EXPECTED_CORPUS_SHA256
        and report.get("total_mutants") == EXPECTED_MUTANTS
        and report.get("detected_mutants") == EXPECTED_MUTANTS
        and report.get("false_accepts") == 0
        and report.get("semantic_checks") == EXPECTED_MUTANTS
        and report.get("semantic_rejections") == EXPECTED_MUTANTS
        and report.get("semantic_false_accepts") == 0
        and report.get("semantic_scope_skips") == []
        and report.get("portability_checks") == EXPECTED_PORTABILITY_CHECKS
        and report.get("rewrite_checks") == EXPECTED_REWRITE_CHECKS
        and report.get("passed") is True
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行 ProofTrace 确定性变异基准")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args(argv)
    report = run_benchmark()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"ProofTrace: {report['detected_mutants']}/{report['total_mutants']} "
            f"mutants, {report['portability_checks']} portability checks, "
            f"{report['rewrite_checks']} rewrite checks"
        )
    return 0 if validate_report(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
