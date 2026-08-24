"""Deterministic benchmark for exhaustive Hybrid-QASM path certificates."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from typing import Any, Sequence

try:
    from .. import adapter
except ImportError:  # Extracted starter_kit root.
    import adapter


FIXTURES = (
    {
        "name": "deterministic-dead-branch",
        "source": """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1];
x q[0];
measure q -> c;
classical {
  if (c[0] == 1) { r1 = 7; } else { r1 = 3; }
}
""",
        "max_outcomes": 2,
        "expected": {"live_paths": 1, "dead_paths": 1, "unreachable_outcomes": 1},
    },
    {
        "name": "bell-two-path-mass",
        "source": """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
classical {
  if (c[0] == 1) { r1 = 7; } else { r1 = 3; }
}
""",
        "max_outcomes": 4,
        "expected": {"live_paths": 2, "dead_paths": 0, "unreachable_outcomes": 2},
    },
    {
        "name": "nested-full-support-paths",
        "source": """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
h q[1];
measure q -> c;
classical {
  if (c[0] == 1) {
    if (c[1] != 0) { r4 = 100; } else { r4 = 70; }
  } else {
    r4 = 10;
  }
}
""",
        "max_outcomes": 4,
        "expected": {"live_paths": 3, "dead_paths": 0, "unreachable_outcomes": 0},
    },
    {
        "name": "same-path-different-final-registers",
        "source": """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[1];
measure q -> c;
classical {
  if (c[0] == 0) { r1 = 5; } else { r1 = 9; }
  r2 = c[1];
}
""",
        "max_outcomes": 4,
        "expected": {"live_paths": 1, "dead_paths": 1, "unreachable_outcomes": 2},
    },
)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def _fixture_corpus_sha256() -> str:
    digest = hashlib.sha256()
    for fixture in FIXTURES:
        digest.update(_canonical_json(fixture).encode("utf-8"))
    return digest.hexdigest()


EXPECTED_CORPUS_SHA256 = _fixture_corpus_sha256()


def _tampered_certificate(certificate: dict[str, Any]) -> dict[str, Any]:
    tampered = copy.deepcopy(certificate)
    reachable = next(
        outcome for outcome in tampered["outcomes"] if outcome["reachable"]
    )
    if reachable["final_registers"]:
        register = next(iter(reachable["final_registers"]))
        reachable["final_registers"][register] += 1
    else:
        reachable["path_id"] = reachable["path_id"] + "-tampered"
    return tampered


def run_benchmark() -> dict[str, Any]:
    fixtures = []
    tamper_rejections = 0
    failures = []

    for fixture in FIXTURES:
        certificate = adapter.certify_hybrid_paths(
            fixture["source"], max_outcomes=fixture["max_outcomes"]
        )
        verification = adapter.verify_hybrid_path_certificate(
            fixture["source"], certificate
        )
        total_probability = sum(
            outcome["probability"] for outcome in certificate["outcomes"]
        )
        live_paths = sum(
            1 for item in certificate["path_groups"] if item["total_probability"] > 0
        )
        dead_paths = len(certificate["dead_path_ids"])
        unreachable_outcomes = len(certificate["unreachable_outcomes"])

        tampered = _tampered_certificate(certificate)
        tamper_result = adapter.verify_hybrid_path_certificate(
            fixture["source"], tampered
        )
        if not tamper_result["valid"]:
            tamper_rejections += 1

        fixture_report = {
            "name": fixture["name"],
            "live_paths": live_paths,
            "dead_paths": dead_paths,
            "unreachable_outcomes": unreachable_outcomes,
            "total_probability": total_probability,
            "verification_valid": verification["valid"],
            "tamper_rejected": not tamper_result["valid"],
            "certificate_sha256": certificate["integrity"]["body_sha256"],
        }
        fixtures.append(fixture_report)

        expected = fixture["expected"]
        if abs(total_probability - 1.0) > 1e-12:
            failures.append({"name": fixture["name"], "kind": "probability-total"})
        if not verification["valid"]:
            failures.append({"name": fixture["name"], "kind": "verification"})
        if live_paths != expected["live_paths"]:
            failures.append({"name": fixture["name"], "kind": "live-paths"})
        if dead_paths != expected["dead_paths"]:
            failures.append({"name": fixture["name"], "kind": "dead-paths"})
        if unreachable_outcomes != expected["unreachable_outcomes"]:
            failures.append({"name": fixture["name"], "kind": "unreachable-outcomes"})
        if tamper_result["valid"]:
            failures.append({"name": fixture["name"], "kind": "tamper-accept"})

    return {
        "schema_version": "loomq-hybrid-path-benchmark-v1",
        "fixture_count": len(FIXTURES),
        "tamper_rejections": tamper_rejections,
        "corpus_sha256": EXPECTED_CORPUS_SHA256,
        "fixtures": fixtures,
        "failures": failures,
        "passed": not failures and tamper_rejections == len(FIXTURES),
    }


def validate_report(report: dict[str, Any]) -> bool:
    return bool(
        report.get("schema_version") == "loomq-hybrid-path-benchmark-v1"
        and report.get("fixture_count") == len(FIXTURES)
        and report.get("tamper_rejections") == len(FIXTURES)
        and report.get("corpus_sha256") == EXPECTED_CORPUS_SHA256
        and report.get("passed") is True
        and not report.get("failures")
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="运行 Hybrid 路径证书确定性基准")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args(argv)
    report = run_benchmark()
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        print(
            f"Hybrid paths: {report['fixture_count']} fixtures, "
            f"{report['tamper_rejections']} tamper rejections, "
            f"corpus {report['corpus_sha256']}"
        )
    return 0 if validate_report(report) else 1


if __name__ == "__main__":
    raise SystemExit(main())
