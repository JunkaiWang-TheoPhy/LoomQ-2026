"""Run and validate a deterministic 40,000-check credential-free campaign."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Sequence

try:
    from .. import adapter
    from ..loomq.qasm import parse_qasm
    from ..loomq.quantum_riscv import (
        EncodedQuantumProgram,
        decode_program,
        encode_circuit,
    )
    from ..loomq.runtime import BACKEND_NAMES
    from ..loomq.simulator import probabilities
    from ..riscv_emulator import TinyRISCVEmulator
except ImportError:  # Extracted starter_kit root.
    import adapter
    from loomq.qasm import parse_qasm
    from loomq.quantum_riscv import EncodedQuantumProgram, decode_program, encode_circuit
    from loomq.runtime import BACKEND_NAMES
    from loomq.simulator import probabilities
    from riscv_emulator import TinyRISCVEmulator


SCHEMA_VERSION = "loomq-offline-stress-v1"
SEED = 20260824
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "evidence" / "files" / "offline-stress-summary.json"
CAMPAIGN_SPECS = {
    "l1_simulator": 3_000,
    "l1_targets": 9_000,
    "quantum_riscv_roundtrip": 3_000,
    "l3_differential": 20_000,
    "parser_rejection": 2_500,
    "riscv_rejection": 2_500,
}
EXPECTED_TOTAL_CHECKS = sum(CAMPAIGN_SPECS.values())
EXPECTED_CORPUS_SHA256 = "ecd3452fe15fe326dacb798cb03de0ce5ecf411f18cd25f9c8fd765502f3722a"
GATES = ("h", "x", "s", "sdg", "t", "tdg", "rz", "ry", "cx", "cu1", "swap", "ccx")


def _operation(gate: str, generator: random.Random) -> str:
    if gate in {"h", "x", "s", "sdg", "t", "tdg"}:
        return f"{gate} q[{generator.randrange(3)}];"
    if gate in {"rz", "ry"}:
        angle = generator.choice((math.pi / 7, -math.pi / 3, 0.271, -0.419))
        return f"{gate}({angle!r}) q[{generator.randrange(3)}];"
    qubits = generator.sample(range(3), 3)
    if gate == "ccx":
        return f"ccx q[{qubits[0]}],q[{qubits[1]}],q[{qubits[2]}];"
    if gate == "cu1":
        return f"cu1({generator.choice((math.pi / 5, -0.337))!r}) q[{qubits[0]}],q[{qubits[1]}];"
    return f"{gate} q[{qubits[0]}],q[{qubits[1]}];"


def _qasm_case(index: int, generator: random.Random) -> str:
    operations = [_operation(GATES[index % len(GATES)], generator)]
    operations.extend(_operation(generator.choice(GATES), generator) for _ in range(11))
    return "\n".join(
        (
            "OPENQASM 2.0;",
            'include "qelib1.inc";',
            "qreg q[3];",
            "creg c[3];",
            *operations,
            "measure q -> c;",
        )
    )


def _hybrid_case(index: int, generator: random.Random) -> tuple[str, Callable[[int, int], int]]:
    left = generator.randint(-50, 50)
    right = generator.randint(-50, 50)
    offset = generator.randint(-20, 20)
    comparison = generator.choice(("==", "!="))
    source = f'''OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2]; measure q -> c;
classical {{
  r1 = {left}; r2 = {right};
  if (c[0] {comparison} c[1]) {{ r3 = r1 + r2; }} else {{ r3 = r2 - r1; }}
  r4 = r3 + {offset};
}}
'''

    def expected(c0: int, c1: int) -> int:
        condition = c0 == c1
        if comparison == "!=":
            condition = not condition
        return (left + right if condition else right - left) + offset

    return source, expected


def run_campaign(
    *,
    l1_circuits: int = 3_000,
    l3_programs: int = 5_000,
    invalid_qasm_cases: int = 2_500,
    invalid_riscv_cases: int = 2_500,
) -> dict:
    generator = random.Random(SEED)
    digest = hashlib.sha256()
    failures: list[dict] = []
    campaigns = {
        name: {"checks": 0, "passed": 0, "failures": 0}
        for name in CAMPAIGN_SPECS
    }

    def record(name: str, case: int, action: Callable[[], None]) -> None:
        campaigns[name]["checks"] += 1
        try:
            action()
            campaigns[name]["passed"] += 1
        except Exception as exc:  # The summary retains bounded reproducible diagnostics.
            campaigns[name]["failures"] += 1
            if len(failures) < 100:
                failures.append({"campaign": name, "case": case, "error": f"{type(exc).__name__}: {exc}"})

    for index in range(l1_circuits):
        source = _qasm_case(index, generator)
        digest.update(source.encode("utf-8") + b"\0")
        circuit = None

        def check_simulator() -> None:
            nonlocal circuit
            circuit = parse_qasm(source)
            if abs(sum(probabilities(circuit).values()) - 1.0) > 1e-12:
                raise AssertionError("probability mass is not normalized")

        record("l1_simulator", index, check_simulator)
        for target in adapter.SUPPORTED_TARGETS:
            def check_target(target: str = target) -> None:
                result = adapter.run(source, target, 97 + index % 17)
                if sum(result["counts"].values()) != result["shots"]:
                    raise AssertionError("counts do not sum to shots")
                if result["backend"] != BACKEND_NAMES[target] or not adapter.transpile(source, target).strip():
                    raise AssertionError("target contract is incomplete")

            record("l1_targets", index, check_target)

        def check_roundtrip() -> None:
            parsed = circuit if circuit is not None else parse_qasm(source)
            if decode_program(encode_circuit(parsed)) != parsed:
                raise AssertionError("quantum RISC-V roundtrip changed the circuit")

        record("quantum_riscv_roundtrip", index, check_roundtrip)

    for index in range(l3_programs):
        source, expected = _hybrid_case(index, generator)
        digest.update(source.encode("utf-8") + b"\0")
        try:
            _, assembly = adapter.compile_hybrid(source)
        except Exception as exc:
            for inputs in range(4):
                record("l3_differential", index * 4 + inputs, lambda exc=exc: (_ for _ in ()).throw(exc))
            continue
        for c0 in (0, 1):
            for c1 in (0, 1):
                def check_hybrid(c0: int = c0, c1: int = c1) -> None:
                    emulator = TinyRISCVEmulator()
                    emulator.load_program(assembly)
                    emulator.set_register("x10", c0)
                    emulator.set_register("x11", c1)
                    if emulator.execute().get("x4", 0) != expected(c0, c1):
                        raise AssertionError("compiled result differs from Python oracle")

                record("l3_differential", index * 4 + c0 * 2 + c1, check_hybrid)

    for index in range(invalid_qasm_cases):
        source = f'OPENQASM 2.0; include "qelib1.inc"; qreg q[1]; creg c[1]; rz((pi+{index % 17}) q[0];'
        digest.update(source.encode("utf-8") + b"\0")

        def reject_qasm(source: str = source) -> None:
            try:
                parse_qasm(source)
            except ValueError:
                return
            raise AssertionError("malformed QASM was accepted")

        record("parser_rejection", index, reject_qasm)

    valid = encode_circuit(parse_qasm("OPENQASM 2.0; qreg q[1]; creg c[1]; h q[0];"))
    for index in range(invalid_riscv_cases):
        corrupted = EncodedQuantumProgram(1, 1, ((valid.words[0] & ~0x7F) | (0x7F - index % 3),), ())
        digest.update(corrupted.to_bytes() + b"\0")

        def reject_riscv(corrupted: EncodedQuantumProgram = corrupted) -> None:
            try:
                decode_program(corrupted)
            except ValueError:
                return
            raise AssertionError("non-custom opcode was accepted")

        record("riscv_rejection", index, reject_riscv)

    total_checks = sum(item["checks"] for item in campaigns.values())
    passed_checks = sum(item["passed"] for item in campaigns.values())
    return {
        "schema_version": SCHEMA_VERSION,
        "seed": SEED,
        "campaigns": campaigns,
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": total_checks - passed_checks,
        "failures": failures,
        "corpus_sha256": digest.hexdigest(),
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "passed": total_checks == passed_checks,
    }


def expected_summary_fixture() -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "seed": SEED,
        "campaigns": {
            name: {"checks": checks, "passed": checks, "failures": 0}
            for name, checks in CAMPAIGN_SPECS.items()
        },
        "total_checks": EXPECTED_TOTAL_CHECKS,
        "passed_checks": EXPECTED_TOTAL_CHECKS,
        "failed_checks": 0,
        "failures": [],
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "passed": True,
    }


def validate_summary(path: Path) -> dict:
    summary = json.loads(path.read_text(encoding="utf-8"))
    if summary.get("schema_version") != SCHEMA_VERSION or summary.get("seed") != SEED:
        raise ValueError("summary schema or seed mismatch")
    if summary.get("total_checks") != EXPECTED_TOTAL_CHECKS:
        raise ValueError("total checks mismatch")
    if summary.get("passed_checks") != EXPECTED_TOTAL_CHECKS or summary.get("failed_checks") != 0:
        raise ValueError("summary does not prove a complete pass")
    if summary.get("campaigns") != expected_summary_fixture()["campaigns"]:
        raise ValueError("campaign counts mismatch")
    if summary.get("corpus_sha256") != EXPECTED_CORPUS_SHA256:
        raise ValueError("corpus hash mismatch")
    if summary.get("passed") is not True or summary.get("failures") != []:
        raise ValueError("campaign contains failures")
    return {"valid": True, "total_checks": EXPECTED_TOTAL_CHECKS, "corpus_sha256": EXPECTED_CORPUS_SHA256}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json-out", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", action="store_true")
    args = parser.parse_args(argv)
    if args.validate:
        print(json.dumps(validate_summary(args.json_out), sort_keys=True))
        return 0
    summary = run_campaign()
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in summary.items() if key != "failures"}, sort_keys=True))
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
