#!/usr/bin/env python3
"""Credential-free end-to-end check for the quantum RISC-V bonus path."""

from __future__ import annotations

import json

try:
    from .loomq.qasm import Circuit, Gate, Measurement
    from .loomq.quantum_riscv import CUSTOM_0_OPCODE, decode_program, encode_circuit
    from .riscv_emulator import TinyRISCVEmulator
except ImportError:
    from loomq.qasm import Circuit, Gate, Measurement
    from loomq.quantum_riscv import CUSTOM_0_OPCODE, decode_program, encode_circuit
    from riscv_emulator import TinyRISCVEmulator


def evaluate_bonus() -> dict:
    circuit = Circuit(
        2,
        2,
        [
            Gate("h", (0,)),
            Gate("cx", (0, 1)),
            Measurement(0, 0),
            Measurement(1, 1),
        ],
    )
    encoded = encode_circuit(circuit)
    restored = decode_program(encoded)
    emulator = TinyRISCVEmulator()
    emulator.load_quantum_program(encoded)
    result = emulator.execute_quantum(1024)
    checks = {
        "custom_opcode": all(word & 0x7F == CUSTOM_0_OPCODE for word in encoded.words),
        "round_trip": restored == circuit,
        "little_endian_bytes": len(encoded.to_bytes()) == 4 * len(encoded.words),
        "bell_counts": result["counts"] == {"00": 512, "11": 512},
    }
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "machine_words": [f"0x{word:08x}" for word in encoded.words],
        "counts": result["counts"],
    }


def main() -> int:
    report = evaluate_bonus()
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
