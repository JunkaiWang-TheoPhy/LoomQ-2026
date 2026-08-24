"""Hybrid-QASM replay orchestration built on the shared compiler and RISC-V trace engine."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Dict, List, Set, Tuple

try:
    from .hybrid import _Compiler, _quantum_operations, parse_hybrid
    from .qasm import Circuit, Gate, Measurement
    from .quantum_riscv import CUSTOM_0_OPCODE, decode_program, encode_circuit
    from ..riscv_emulator import TinyRISCVEmulator
except ImportError:
    from loomq.hybrid import _Compiler, _quantum_operations, parse_hybrid
    from loomq.qasm import Circuit, Gate, Measurement
    from loomq.quantum_riscv import CUSTOM_0_OPCODE, decode_program, encode_circuit
    from riscv_emulator import TinyRISCVEmulator


TRACE_SCHEMA_VERSION = "loomq-hybrid-trace-v1"
_MEASUREMENT_REGISTER_BASE = 10
_MEASUREMENT_REGISTER_LIMIT = 31
_CUSTOM_OPERAND_LIMIT = 32


def _validate_measurement_bits(measurement_bits: Sequence[int], expected: int) -> List[int]:
    if isinstance(measurement_bits, (str, bytes, bytearray)) or not isinstance(
        measurement_bits, Sequence
    ):
        raise ValueError("measurement_bits must be a non-string sequence")
    values = list(measurement_bits)
    if len(values) != expected:
        raise ValueError(
            f"measurement_bits length must equal the declared classical register length {expected}"
        )
    for index, value in enumerate(values):
        if isinstance(value, bool):
            raise ValueError("measurement_bits values must be integers 0 or 1, not booleans")
        if not isinstance(value, int) or value not in {0, 1}:
            raise ValueError(
                f"measurement_bits[{index}] must be an integer 0 or 1"
            )
    return values


def _format_decoded_operation(operation: Gate | Measurement) -> str:
    if isinstance(operation, Measurement):
        return f"measure q[{operation.qubit}] -> c[{operation.clbit}]"
    parameter = f"({operation.parameter!r})" if operation.parameter is not None else ""
    operands = ",".join(f"q[{index}]" for index in operation.qubits)
    return f"{operation.name}{parameter} {operands}"


def _register_index(name: str) -> int:
    return int(name.removeprefix("x"))


def _register_measurements(indexes: Set[int]) -> List[str]:
    return [f"c[{index}]" for index in sorted(indexes)]


def _machine_encoding_reason(operation: Gate | Measurement) -> str | None:
    if isinstance(operation, Measurement):
        if operation.qubit >= _CUSTOM_OPERAND_LIMIT:
            return "quantum bit exceeds custom-0 5-bit operand field"
        if operation.clbit >= _CUSTOM_OPERAND_LIMIT:
            return "classical bit exceeds custom-0 5-bit operand field"
        return None
    if any(qubit >= _CUSTOM_OPERAND_LIMIT for qubit in operation.qubits):
        return "quantum bit exceeds custom-0 5-bit operand field"
    return None


def _build_quantum_machine_trace(
    circuit: Circuit,
) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    representable_operations = []
    omitted_operations = []
    for index, operation in enumerate(circuit.operations):
        reason = _machine_encoding_reason(operation)
        if reason is not None:
            omitted_operations.append(
                {
                    "index": index,
                    "operation": _format_decoded_operation(operation),
                    "reason": reason,
                }
            )
            continue
        representable_operations.append((index, operation))

    if representable_operations:
        encoded_program = encode_circuit(
            Circuit(
                min(circuit.num_qubits, _CUSTOM_OPERAND_LIMIT),
                min(circuit.num_clbits, _CUSTOM_OPERAND_LIMIT),
                [operation for _, operation in representable_operations],
            )
        )
        decoded_program = decode_program(encoded_program)
        quantum_machine_trace = [
            {
                "index": original_index,
                "word": f"0x{word:08x}",
                "opcode": f"0x{CUSTOM_0_OPCODE:02x}",
                "decoded_operation": _format_decoded_operation(operation),
            }
            for (original_index, _), word, operation in zip(
                representable_operations,
                encoded_program.words,
                decoded_program.operations,
            )
        ]
    else:
        quantum_machine_trace = []

    return quantum_machine_trace, {
        "total_operations": len(circuit.operations),
        "encoded_operations": len(representable_operations),
        "fully_encoded": len(omitted_operations) == 0,
        "omitted_operations": omitted_operations,
    }


def _measurement_input_loads(
    measurement_bits: Sequence[int],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    loaded_inputs = []
    omitted_inputs = []
    for index, bit in enumerate(measurement_bits):
        register = _MEASUREMENT_REGISTER_BASE + index
        if register > _MEASUREMENT_REGISTER_LIMIT:
            omitted_inputs.append(
                {
                    "measurement": f"c[{index}]",
                    "reason": "no representable RISC-V replay register",
                }
            )
            continue
        loaded_inputs.append(
            {
                "measurement": f"c[{index}]",
                "register": f"x{register}",
                "value": bit,
            }
        )
    return loaded_inputs, omitted_inputs


def trace_hybrid(source: str, measurement_bits: Sequence[int]) -> Dict[str, Any]:
    circuit, statements = parse_hybrid(source)
    bits = _validate_measurement_bits(measurement_bits, circuit.num_clbits)

    compiler = _Compiler(statements)
    assembly = compiler.compile(statements)
    quantum_operations = _quantum_operations(circuit)
    quantum_machine_trace, quantum_machine_coverage = _build_quantum_machine_trace(
        circuit
    )
    loaded_measurement_inputs, omitted_measurement_inputs = _measurement_input_loads(bits)

    emulator = TinyRISCVEmulator()
    emulator.load_program(assembly)
    for item in loaded_measurement_inputs:
        emulator.set_register(item["register"], item["value"])
    trace = emulator.execute_with_trace()
    trace = emulator.replay_trace(trace)

    provenance: Dict[int, Set[int]] = {index: set() for index in range(32)}
    for index, bit in enumerate(bits):
        register = _MEASUREMENT_REGISTER_BASE + index
        if register > _MEASUREMENT_REGISTER_LIMIT:
            break
        if bit in {0, 1}:
            provenance[register] = {index}

    branch_lookup = {branch.pc: branch for branch in compiler.branches}
    branch_events = []
    branch_path_parts = []
    for event in trace["events"]:
        operation = event["operation"]
        args = event["args"]
        if operation == "li":
            rd = _register_index(args[0])
            if rd != 0:
                provenance[rd] = set()
            continue
        if operation == "addi":
            rd = _register_index(args[0])
            rs1 = _register_index(args[1])
            if rd != 0:
                provenance[rd] = set(provenance[rs1])
            continue
        if operation in {"add", "sub"}:
            rd = _register_index(args[0])
            rs1 = _register_index(args[1])
            rs2 = _register_index(args[2])
            if rd != 0:
                provenance[rd] = set(provenance[rs1]) | set(provenance[rs2])
            continue
        if operation not in {"beq", "bne"}:
            continue

        branch = branch_lookup.get(event["pc"])
        if branch is None:
            continue
        rs1 = _register_index(args[0])
        rs2 = _register_index(args[1])
        left = set(provenance[rs1])
        right = set(provenance[rs2])
        source_condition_true = not event["branch"]["taken"]
        branch_events.append(
            {
                "branch_id": branch.branch_id,
                "pc": event["pc"],
                "machine_operation": branch.machine_operation,
                "source_operator": branch.source_operator,
                "machine_jump_taken": event["branch"]["taken"],
                "source_condition_true": source_condition_true,
                "target_label": event["branch"]["target_label"],
                "operand_provenance": {
                    "left": _register_measurements(left),
                    "right": _register_measurements(right),
                },
                "influencing_measurements": _register_measurements(left | right),
            }
        )
        branch_path_parts.append(
            f"if{branch.branch_id}:{'T' if source_condition_true else 'F'}"
        )

    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "measurement_inputs": bits,
        "loaded_measurement_inputs": loaded_measurement_inputs,
        "omitted_measurement_inputs": omitted_measurement_inputs,
        "quantum_operations": quantum_operations,
        "quantum_machine_trace": quantum_machine_trace,
        "quantum_machine_coverage": quantum_machine_coverage,
        "assembly": assembly,
        "instruction_events": trace["events"],
        "branch_events": branch_events,
        "branch_path": " -> ".join(branch_path_parts),
        "final_registers": trace["final_registers"],
    }
