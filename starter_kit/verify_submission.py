#!/usr/bin/env python3
"""Run every credential-free scored-path check with one command."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Sequence


ROOT = Path(__file__).resolve().parent


def default_phases() -> list[tuple[str, list[str]]]:
    return [
        ("compile", [sys.executable, "-m", "compileall", "-q", str(ROOT)]),
        (
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
        (
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
        ("l3", [sys.executable, str(ROOT / "evaluator.py"), "--level", "l3"]),
        ("quantum-riscv", [sys.executable, str(ROOT / "bonus_evaluator.py")]),
    ]


def run_phases(phases: Sequence[tuple[str, Sequence[str]]]) -> dict:
    results = []
    for name, command in phases:
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
            label = "PASS" if phase["passed"] else "FAIL"
            print(f"[{label}] {phase['name']}")
            detail = phase["stdout"] or phase["stderr"]
            if detail:
                print(detail)
        print("全部无凭据验证通过。" if report["passed"] else "存在失败阶段，请查看上方诊断。")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
