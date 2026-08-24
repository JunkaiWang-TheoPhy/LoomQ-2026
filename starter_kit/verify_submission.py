#!/usr/bin/env python3
"""Run every credential-free scored-path check with one command."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parent


def _phase(
    name: str,
    command: Sequence[str] | None,
    *,
    optional: bool = False,
    skip_reason: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "command": None if command is None else list(command),
        "optional": optional,
        "skip_reason": skip_reason,
    }


def default_phases() -> list[dict[str, Any]]:
    node_path = shutil.which("node")
    return [
        _phase("compile", [sys.executable, "-m", "compileall", "-q", str(ROOT)]),
        _phase(
            "frontend-syntax",
            None if node_path is None else [node_path, "--check", str(ROOT / "web" / "app.js")],
            optional=node_path is None,
            skip_reason="node not found; skipping optional frontend syntax check",
        ),
        _phase(
            "web-integration",
            [
                sys.executable,
                "-m",
                "unittest",
                "tests.test_web",
                "tests.test_assertions",
                "tests.test_hybrid_trace",
                "-v",
            ],
        ),
        _phase(
            "archive-tests",
            [
                sys.executable,
                "-m",
                "unittest",
                "discover",
                "-s",
                str(ROOT / "tests"),
                "-v",
            ],
        ),
        _phase(
            "l2-corpus",
            [sys.executable, "-m", "scripts.l2_stress_campaign", "--dry-run"],
        ),
        _phase(
            "hardware-evidence",
            [sys.executable, "-m", "scripts.validate_hardware_evidence"],
        ),
        _phase(
            "pyquafu-evidence",
            [sys.executable, "-m", "scripts.quafu_cross_validate", "--validate"],
        ),
        _phase(
            "prooftrace-benchmark",
            [sys.executable, "-m", "scripts.prooftrace_benchmark", "--json"],
        ),
        _phase(
            "offline-stress-evidence",
            [sys.executable, "-m", "scripts.offline_stress_campaign", "--validate"],
        ),
        _phase(
            "l1",
            [
                sys.executable,
                str(ROOT / "evaluator.py"),
                "--level",
                "l1",
                "--target",
                "spinq,originq,braket",
            ],
        ),
        _phase("l3", [sys.executable, str(ROOT / "evaluator.py"), "--level", "l3"]),
        _phase("quantum-riscv", [sys.executable, str(ROOT / "bonus_evaluator.py")]),
    ]


def run_phases(phases: Sequence[dict[str, Any]]) -> dict:
    results = []
    for phase in phases:
        name = str(phase["name"])
        command = phase["command"]
        if command is None:
            if not phase.get("optional"):
                results.append(
                    {
                        "name": name,
                        "passed": False,
                        "skipped": False,
                        "returncode": 1,
                        "stdout": "",
                        "stderr": str(phase["skip_reason"] or "required phase is missing its command"),
                    }
                )
                continue
            results.append(
                {
                    "name": name,
                    "passed": True,
                    "skipped": True,
                    "returncode": 0,
                    "stdout": str(phase["skip_reason"]),
                    "stderr": "",
                }
            )
            continue
        completed = subprocess.run(
            list(command),
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )
        results.append(
            {
                "name": name,
                "passed": completed.returncode == 0,
                "skipped": False,
                "returncode": completed.returncode,
                "stdout": completed.stdout.strip(),
                "stderr": completed.stderr.strip(),
            }
        )
    return {"passed": all(result["passed"] for result in results), "phases": results}


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="一条命令验证 LoomQ L1、L3 与量子 RISC-V Bonus"
    )
    parser.add_argument("--json", action="store_true", help="只输出机器可读 JSON")
    args = parser.parse_args(argv)
    report = run_phases(default_phases())
    if args.json:
        print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    else:
        for phase in report["phases"]:
            label = "SKIP" if phase.get("skipped") else ("PASS" if phase["passed"] else "FAIL")
            print(f"[{label}] {phase['name']}")
            detail = phase["stdout"] or phase["stderr"]
            if detail:
                print(detail)
        print("全部无凭据验证通过。" if report["passed"] else "存在失败阶段，请查看上方诊断。")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
