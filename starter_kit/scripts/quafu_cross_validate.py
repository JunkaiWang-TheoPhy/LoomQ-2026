"""Cross-check LoomQ statevectors and target counts against PyQuafu."""

from __future__ import annotations

import argparse
import cmath
import hashlib
import importlib.metadata
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Sequence

try:
    from .. import adapter
    from ..loomq.qasm import parse_qasm
    from ..loomq.simulator import simulate_statevector
except ImportError:  # Extracted starter_kit root.
    import adapter
    from loomq.qasm import parse_qasm
    from loomq.simulator import simulate_statevector


SCHEMA_VERSION = "loomq-pyquafu-cross-validation-v1"
SEED = 20260824
SHOTS = 997
OFFICIAL_GATES = ("h", "x", "s", "sdg", "t", "tdg", "rz", "ry", "cx", "cu1", "swap", "ccx")
EXPECTED_CORPUS_SHA256 = "fa7328082a572c99a1b7b51af79b68faaf4647f037ae0dc112669098432e1c64"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "evidence" / "files" / "pyquafu-cross-validation-summary.json"


def _operation(gate: str, generator: random.Random) -> str:
    if gate in {"h", "x", "s", "sdg", "t", "tdg"}:
        return f"{gate} q[{generator.randrange(3)}];"
    if gate in {"rz", "ry"}:
        angle = generator.choice((math.pi / 7, -math.pi / 3, 0.271, -0.419))
        return f"{gate}({angle!r}) q[{generator.randrange(3)}];"
    if gate in {"cx", "cu1", "swap"}:
        left, right = generator.sample(range(3), 2)
        if gate == "cu1":
            return f"cu1({generator.choice((math.pi / 5, -0.337))!r}) q[{left}],q[{right}];"
        return f"{gate} q[{left}],q[{right}];"
    operands = generator.sample(range(3), 3)
    return f"ccx q[{operands[0]}],q[{operands[1]}],q[{operands[2]}];"


def build_corpus() -> list[str]:
    generator = random.Random(SEED)
    corpus = []
    for case_index in range(40):
        operations = [_operation(OFFICIAL_GATES[case_index % len(OFFICIAL_GATES)], generator)]
        operations.extend(_operation(generator.choice(OFFICIAL_GATES), generator) for _ in range(17))
        corpus.append(
            "\n".join(
                [
                    "OPENQASM 2.0;",
                    'include "qelib1.inc";',
                    "qreg q[3];",
                    "creg c[3];",
                    *operations,
                    "measure q -> c;",
                ]
            )
        )
    return corpus


def gates_in(corpus: Iterable[str]) -> set[str]:
    found = set()
    for source in corpus:
        for line in source.splitlines():
            token = line.strip().split("(", 1)[0].split(" ", 1)[0]
            if token in OFFICIAL_GATES:
                found.add(token)
    return found


def corpus_sha256(corpus: Sequence[str]) -> str:
    serialized = "\n\n--- loomq-case ---\n\n".join(corpus).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()


def _align_global_phase(ours: Sequence[complex], reference: Sequence[complex]) -> list[complex]:
    pivot = next((index for index, value in enumerate(reference) if abs(value) > 1e-12), None)
    if pivot is None:
        raise ValueError("PyQuafu returned an all-zero statevector")
    phase = ours[pivot] / reference[pivot]
    if abs(phase) > 1e-12:
        phase /= abs(phase)
    return [phase * value for value in reference]


def _counts_from_reference(statevector: Sequence[complex], shots: int) -> dict[str, int]:
    raw = {
        format(index, "03b"): abs(value) ** 2 * shots
        for index, value in enumerate(statevector)
        if abs(value) ** 2 > 1e-14
    }
    counts = {state: math.floor(value) for state, value in raw.items()}
    remaining = shots - sum(counts.values())
    order = sorted(raw, key=lambda state: (-(raw[state] - counts[state]), state))
    for state in order[:remaining]:
        counts[state] += 1
    return {state: count for state, count in counts.items() if count}


def run_cross_validation() -> dict:
    try:
        from quafu import simulate
    except ImportError as exc:
        raise RuntimeError("pyquafu==0.4.5 is required for this optional cross-validation") from exc

    corpus = build_corpus()
    max_error = 0.0
    max_count_l1_distance = 0
    passed_target_checks = 0
    failures = []
    for case_index, source in enumerate(corpus):
        ours = simulate_statevector(parse_qasm(source))
        reference = list(simulate(source, shots=0).get_statevector())
        aligned = _align_global_phase(ours, reference)
        case_error = max(abs(left - right) for left, right in zip(ours, aligned))
        max_error = max(max_error, case_error)
        expected_counts = _counts_from_reference(reference, SHOTS)
        for target in adapter.SUPPORTED_TARGETS:
            result = adapter.run(source, target, SHOTS)
            native = adapter.transpile(source, target)
            states = set(result["counts"]) | set(expected_counts)
            count_l1_distance = sum(
                abs(result["counts"].get(state, 0) - expected_counts.get(state, 0))
                for state in states
            )
            max_count_l1_distance = max(max_count_l1_distance, count_l1_distance)
            if case_error <= 1e-9 and count_l1_distance <= 2 and native.strip():
                passed_target_checks += 1
            else:
                failures.append(
                    {
                        "case": case_index,
                        "target": target,
                        "amplitude_error": case_error,
                        "count_l1_distance": count_l1_distance,
                    }
                )
    target_checks = len(corpus) * len(adapter.SUPPORTED_TARGETS)
    return {
        "schema_version": SCHEMA_VERSION,
        "seed": SEED,
        "circuits": len(corpus),
        "targets_per_circuit": len(adapter.SUPPORTED_TARGETS),
        "target_checks": target_checks,
        "passed_target_checks": passed_target_checks,
        "failed_target_checks": len(failures),
        "failures": failures,
        "corpus_sha256": corpus_sha256(corpus),
        "official_gates": sorted(gates_in(corpus)),
        "pyquafu_version": importlib.metadata.version("pyquafu"),
        "max_amplitude_error": max_error,
        "max_count_l1_distance": max_count_l1_distance,
        "count_tie_tolerance_l1": 2,
        "count_comparison": "L1 distance <= 2, allowing at most one shot to move across a floating-point remainder tie",
        "global_phase_aligned": True,
        "shots_per_target_check": SHOTS,
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "passed": passed_target_checks == target_checks and not failures,
    }


def validate_summary(path: Path) -> dict:
    summary = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "schema_version": SCHEMA_VERSION,
        "seed": SEED,
        "circuits": 40,
        "targets_per_circuit": 3,
        "target_checks": 120,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "official_gates": sorted(OFFICIAL_GATES),
    }
    for key, value in expected.items():
        if summary.get(key) != value:
            raise ValueError(f"summary mismatch: {key}")
    if summary.get("passed_target_checks") != 120 or summary.get("failed_target_checks") != 0:
        raise ValueError("target check totals do not prove a complete pass")
    if summary.get("passed") is not True:
        raise ValueError("cross-validation summary is not passing")
    if summary.get("pyquafu_version") != "0.4.5":
        raise ValueError("PyQuafu version is not the documented 0.4.5 oracle")
    if summary.get("global_phase_aligned") is not True:
        raise ValueError("statevectors were not compared up to global phase")
    if summary.get("shots_per_target_check") != SHOTS:
        raise ValueError("shot count does not match the fixed campaign")
    if not isinstance(summary.get("max_amplitude_error"), (int, float)) or summary["max_amplitude_error"] > 1e-9:
        raise ValueError("amplitude error exceeds tolerance")
    if summary.get("count_tie_tolerance_l1") != 2:
        raise ValueError("count tie tolerance is not the documented one-shot bound")
    if not isinstance(summary.get("max_count_l1_distance"), int) or summary["max_count_l1_distance"] > 2:
        raise ValueError("count discretization distance exceeds one reassigned shot")
    return {"valid": True, "target_checks": 120, "corpus_sha256": EXPECTED_CORPUS_SHA256}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Cross-check LoomQ against PyQuafu 0.4.5")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    if args.validate:
        print(json.dumps(validate_summary(args.json_out), sort_keys=True))
        return 0
    summary = run_cross_validation()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
