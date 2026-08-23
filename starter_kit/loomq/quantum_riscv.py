"""Minimal 32-bit RISC-V custom-opcode encoding for LoomQ quantum operations."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .qasm import Circuit, Gate, Measurement


CUSTOM_0_OPCODE = 0x0B

_FORMAT_GATE1 = 0
_FORMAT_GATE1_PARAM = 1
_FORMAT_GATE2 = 2
_FORMAT_GATE2_PARAM = 3
_FORMAT_GATE3 = 4
_FORMAT_MEASURE = 5

_GATE_IDS = {
    "h": 0,
    "x": 1,
    "s": 2,
    "sdg": 3,
    "t": 4,
    "tdg": 5,
    "rz": 6,
    "ry": 7,
    "cx": 8,
    "cu1": 9,
    "swap": 10,
    "ccx": 11,
}
_ID_GATES = {identifier: name for name, identifier in _GATE_IDS.items()}


class QuantumRISCVError(ValueError):
    """Raised for invalid custom quantum instruction words or metadata."""


@dataclass(frozen=True)
class EncodedQuantumProgram:
    num_qubits: int
    num_clbits: int
    words: Tuple[int, ...]
    parameters: Tuple[float, ...]

    def __post_init__(self) -> None:
        if not 1 <= self.num_qubits <= 32 or not 1 <= self.num_clbits <= 32:
            raise QuantumRISCVError("quantum RISC-V supports 1..32 quantum/classical bits")
        if any(
            not isinstance(word, int) or not 0 <= word <= 0xFFFFFFFF
            for word in self.words
        ):
            raise QuantumRISCVError("machine words must be unsigned 32-bit integers")
        if len(self.parameters) > 128 or any(
            not math.isfinite(value) for value in self.parameters
        ):
            raise QuantumRISCVError("parameter table must contain at most 128 finite values")

    def to_bytes(self) -> bytes:
        return b"".join(word.to_bytes(4, "little") for word in self.words)

    @classmethod
    def from_bytes(
        cls,
        machine_code: bytes,
        *,
        num_qubits: int,
        num_clbits: int,
        parameters: Tuple[float, ...],
    ) -> "EncodedQuantumProgram":
        if len(machine_code) % 4:
            raise QuantumRISCVError("machine-code length must be a multiple of four bytes")
        words = tuple(
            int.from_bytes(machine_code[offset : offset + 4], "little")
            for offset in range(0, len(machine_code), 4)
        )
        return cls(num_qubits, num_clbits, words, tuple(parameters))


def _field(value: int, label: str) -> int:
    if not 0 <= value <= 31:
        raise QuantumRISCVError(f"{label} exceeds the 5-bit operand field")
    return value


def _word(
    instruction_format: int,
    operand0: int = 0,
    operand1: int = 0,
    operand2: int = 0,
    payload: int = 0,
) -> int:
    if not 0 <= payload <= 127:
        raise QuantumRISCVError("instruction payload exceeds seven bits")
    return (
        CUSTOM_0_OPCODE
        | (_field(operand0, "operand0") << 7)
        | (instruction_format << 12)
        | (_field(operand1, "operand1") << 15)
        | (_field(operand2, "operand2") << 20)
        | (payload << 25)
    )


def encode_circuit(circuit: Circuit) -> EncodedQuantumProgram:
    if circuit.num_qubits > 32 or circuit.num_clbits > 32:
        raise QuantumRISCVError("circuit exceeds the 5-bit operand field")
    parameters: List[float] = []
    parameter_indices: Dict[float, int] = {}
    words: List[int] = []

    def parameter_index(value: float) -> int:
        if value not in parameter_indices:
            if len(parameters) >= 128:
                raise QuantumRISCVError("parameter table exceeds seven-bit index capacity")
            parameter_indices[value] = len(parameters)
            parameters.append(value)
        return parameter_indices[value]

    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            words.append(_word(_FORMAT_MEASURE, operation.qubit, operation.clbit))
            continue
        gate_id = _GATE_IDS[operation.name]
        if operation.name in {"rz", "ry"}:
            assert operation.parameter is not None
            words.append(
                _word(
                    _FORMAT_GATE1_PARAM,
                    operation.qubits[0],
                    operand2=gate_id,
                    payload=parameter_index(operation.parameter),
                )
            )
        elif operation.name == "cu1":
            assert operation.parameter is not None
            words.append(
                _word(
                    _FORMAT_GATE2_PARAM,
                    operation.qubits[0],
                    operation.qubits[1],
                    payload=parameter_index(operation.parameter),
                )
            )
        elif len(operation.qubits) == 1:
            words.append(_word(_FORMAT_GATE1, operation.qubits[0], payload=gate_id))
        elif len(operation.qubits) == 2:
            words.append(
                _word(
                    _FORMAT_GATE2,
                    operation.qubits[0],
                    operation.qubits[1],
                    payload=gate_id,
                )
            )
        else:
            words.append(
                _word(
                    _FORMAT_GATE3,
                    operation.qubits[0],
                    operation.qubits[1],
                    operation.qubits[2],
                    gate_id,
                )
            )
    return EncodedQuantumProgram(
        circuit.num_qubits, circuit.num_clbits, tuple(words), tuple(parameters)
    )


def decode_program(program: EncodedQuantumProgram) -> Circuit:
    operations = []

    def check_operand(value: int, limit: int, label: str) -> int:
        if value >= limit:
            raise QuantumRISCVError(f"{label} operand {value} exceeds declared size {limit}")
        return value

    for word in program.words:
        if word & 0x7F != CUSTOM_0_OPCODE:
            raise QuantumRISCVError("instruction does not use the RISC-V custom-0 opcode")
        operand0 = (word >> 7) & 0x1F
        instruction_format = (word >> 12) & 0x07
        operand1 = (word >> 15) & 0x1F
        operand2 = (word >> 20) & 0x1F
        payload = (word >> 25) & 0x7F

        if instruction_format == _FORMAT_MEASURE:
            if operand2 != 0 or payload != 0:
                raise QuantumRISCVError("measurement instruction has nonzero reserved fields")
            operations.append(
                Measurement(
                    check_operand(operand0, program.num_qubits, "quantum"),
                    check_operand(operand1, program.num_clbits, "classical"),
                )
            )
            continue
        if instruction_format == _FORMAT_GATE1_PARAM:
            if operand1 != 0:
                raise QuantumRISCVError(
                    "parameterized one-qubit instruction has a nonzero reserved field"
                )
            gate_name = _ID_GATES.get(operand2)
            if gate_name not in {"rz", "ry"}:
                raise QuantumRISCVError("invalid parameterized one-qubit gate id")
            if payload >= len(program.parameters):
                raise QuantumRISCVError("parameter-table index is out of range")
            operations.append(
                Gate(
                    gate_name,
                    (check_operand(operand0, program.num_qubits, "quantum"),),
                    program.parameters[payload],
                )
            )
            continue
        if instruction_format == _FORMAT_GATE2_PARAM:
            if operand2 != 0:
                raise QuantumRISCVError(
                    "parameterized two-qubit instruction has a nonzero reserved field"
                )
            if payload >= len(program.parameters):
                raise QuantumRISCVError("parameter-table index is out of range")
            operations.append(
                Gate(
                    "cu1",
                    (
                        check_operand(operand0, program.num_qubits, "quantum"),
                        check_operand(operand1, program.num_qubits, "quantum"),
                    ),
                    program.parameters[payload],
                )
            )
            continue

        gate_name = _ID_GATES.get(payload)
        expected = {
            _FORMAT_GATE1: {"h", "x", "s", "sdg", "t", "tdg"},
            _FORMAT_GATE2: {"cx", "swap"},
            _FORMAT_GATE3: {"ccx"},
        }.get(instruction_format)
        if expected is None or gate_name not in expected:
            raise QuantumRISCVError("instruction format and gate id are inconsistent")
        if instruction_format == _FORMAT_GATE1 and (operand1 != 0 or operand2 != 0):
            raise QuantumRISCVError("one-qubit instruction has nonzero reserved fields")
        if instruction_format == _FORMAT_GATE2 and operand2 != 0:
            raise QuantumRISCVError("two-qubit instruction has a nonzero reserved field")
        arity = {_FORMAT_GATE1: 1, _FORMAT_GATE2: 2, _FORMAT_GATE3: 3}[
            instruction_format
        ]
        raw_qubits = (operand0, operand1, operand2)[:arity]
        qubits = tuple(
            check_operand(value, program.num_qubits, "quantum") for value in raw_qubits
        )
        if len(set(qubits)) != len(qubits):
            raise QuantumRISCVError("quantum instruction reuses a qubit operand")
        operations.append(Gate(gate_name, qubits))

    return Circuit(program.num_qubits, program.num_clbits, operations)
