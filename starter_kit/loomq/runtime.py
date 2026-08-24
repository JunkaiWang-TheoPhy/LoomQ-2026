"""Execution and result-schema normalization for official LoomQ targets."""

from __future__ import annotations

import math
import uuid
from datetime import datetime, timezone
from typing import Dict

from .qasm import Circuit, Gate
from .simulator import MAX_SIMULATOR_QUBITS, probabilities


BACKEND_NAMES = {
    "spinq": "spinq_taurus_local",
    "originq": "originq_local_statevector",
    "braket": "braket_local_simulator",
}
LOCAL_TARGET_QUBITS = {"spinq": 24, "originq": 30, "braket": 25}


def _integer_counts(distribution: Dict[str, float], shots: int) -> Dict[str, int]:
    raw = {key: probability * shots for key, probability in distribution.items()}
    counts = {key: math.floor(value) for key, value in raw.items()}
    remaining = shots - sum(counts.values())
    order = sorted(raw, key=lambda key: (-(raw[key] - counts[key]), key))
    for key in order[:remaining]:
        counts[key] += 1
    return {key: value for key, value in counts.items() if value}


def execute(circuit: Circuit, target: str, shots: int) -> Dict[str, object]:
    if target not in BACKEND_NAMES:
        raise ValueError(f"unsupported target: {target}")
    if not isinstance(shots, int) or isinstance(shots, bool) or shots <= 0:
        raise ValueError("shots must be a positive integer")
    if circuit.num_qubits > LOCAL_TARGET_QUBITS[target]:
        raise ValueError(
            f"{target} local execution supports at most "
            f"{LOCAL_TARGET_QUBITS[target]} qubits"
        )

    distribution = probabilities(circuit)
    gate_count = sum(isinstance(operation, Gate) for operation in circuit.operations)
    return {
        "backend": BACKEND_NAMES[target],
        "job_id": f"local-{target}-{uuid.uuid4().hex}",
        "shots": shots,
        "counts": _integer_counts(distribution, shots),
        "bit_order": "little",
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "meta": {
            "engine": (
                "loomq-statevector"
                if circuit.num_qubits <= MAX_SIMULATOR_QUBITS
                else "loomq-sparse-statevector"
            ),
            "transpiled_gates": gate_count,
            "depth": gate_count,
        },
    }
