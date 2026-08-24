#!/usr/bin/env python3
"""Run LoomQ-emitted OpenQASM 3 on the optional AWS Braket local simulator."""

from __future__ import annotations

import json
from datetime import datetime, timezone

try:
    from braket.devices import LocalSimulator
    from braket.ir.openqasm import Program
except ImportError:
    LocalSimulator = None
    Program = None

try:
    from .. import adapter
except ImportError:
    try:
        from starter_kit import adapter
    except ImportError:
        import adapter


def run_on_braket_simulator(qasm_str: str, shots: int = 1024) -> dict:
    if LocalSimulator is None or Program is None:
        raise RuntimeError(
            "amazon-braket-sdk 未安装；请安装可选厂商 SDK 后运行本示例"
        )
    native_ir = adapter.transpile(qasm_str, "braket")
    task = LocalSimulator().run(Program(source=native_ir), shots=shots)
    result = task.result()
    return {
        "backend": "aws_braket_local_simulator",
        "job_id": str(result.task_metadata.id),
        "shots": shots,
        "counts": {str(key): int(value) for key, value in result.measurement_counts.items()},
        "bit_order": "little",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "meta": {
            "qubits_count": len(result.measured_qubits),
            "execution": "local-simulator",
            "job_id_source": "provider-task-metadata",
            "timestamp_source": "local-observation",
        },
    }


def main() -> None:
    qasm = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
'''
    result = run_on_braket_simulator(qasm)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
