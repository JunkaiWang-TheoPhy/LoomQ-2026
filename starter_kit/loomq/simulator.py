"""Small exact state-vector engine for the published LoomQ gate subset."""

from __future__ import annotations

import cmath
import math
from typing import Dict, List, Sequence, Tuple

from .qasm import Circuit, Gate, Measurement


StateVector = List[complex]
Matrix2 = Tuple[Tuple[complex, complex], Tuple[complex, complex]]


def _single_matrix(gate: Gate) -> Matrix2:
    name = gate.name
    root = 1 / math.sqrt(2)
    if name == "h":
        return ((root, root), (root, -root))
    if name == "x":
        return ((0, 1), (1, 0))
    if name == "s":
        return ((1, 0), (0, 1j))
    if name == "sdg":
        return ((1, 0), (0, -1j))
    if name == "t":
        return ((1, 0), (0, cmath.exp(1j * math.pi / 4)))
    if name == "tdg":
        return ((1, 0), (0, cmath.exp(-1j * math.pi / 4)))
    if name == "rz":
        assert gate.parameter is not None
        return (
            (cmath.exp(-0.5j * gate.parameter), 0),
            (0, cmath.exp(0.5j * gate.parameter)),
        )
    if name == "ry":
        assert gate.parameter is not None
        cosine = math.cos(gate.parameter / 2)
        sine = math.sin(gate.parameter / 2)
        return ((cosine, -sine), (sine, cosine))
    raise ValueError(f"not a single-qubit gate: {name}")


def _apply_single(state: StateVector, qubit: int, matrix: Matrix2) -> None:
    mask = 1 << qubit
    for zero_index in range(len(state)):
        if zero_index & mask:
            continue
        one_index = zero_index | mask
        zero, one = state[zero_index], state[one_index]
        state[zero_index] = matrix[0][0] * zero + matrix[0][1] * one
        state[one_index] = matrix[1][0] * zero + matrix[1][1] * one


def _apply_gate(state: StateVector, gate: Gate) -> None:
    if len(gate.qubits) == 1:
        _apply_single(state, gate.qubits[0], _single_matrix(gate))
        return

    if gate.name == "cx":
        control, target = gate.qubits
        control_mask, target_mask = 1 << control, 1 << target
        for index in range(len(state)):
            if index & control_mask and not index & target_mask:
                paired = index | target_mask
                state[index], state[paired] = state[paired], state[index]
        return

    if gate.name == "cu1":
        assert gate.parameter is not None
        mask = (1 << gate.qubits[0]) | (1 << gate.qubits[1])
        phase = cmath.exp(1j * gate.parameter)
        for index in range(len(state)):
            if index & mask == mask:
                state[index] *= phase
        return

    if gate.name == "swap":
        left_mask, right_mask = 1 << gate.qubits[0], 1 << gate.qubits[1]
        for index in range(len(state)):
            if not index & left_mask and index & right_mask:
                paired = (index | left_mask) & ~right_mask
                state[index], state[paired] = state[paired], state[index]
        return

    if gate.name == "ccx":
        left, right, target = gate.qubits
        controls = (1 << left) | (1 << right)
        target_mask = 1 << target
        for index in range(len(state)):
            if index & controls == controls and not index & target_mask:
                paired = index | target_mask
                state[index], state[paired] = state[paired], state[index]
        return

    raise ValueError(f"unsupported simulated gate: {gate.name}")


def simulate_statevector(circuit: Circuit) -> StateVector:
    """Return the final state before terminal measurements."""
    state: StateVector = [0j] * (1 << circuit.num_qubits)
    state[0] = 1 + 0j
    measurement_seen = False
    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            measurement_seen = True
            continue
        if measurement_seen:
            raise ValueError("mid-circuit measurement is outside the LoomQ L1 contract")
        _apply_gate(state, operation)
    return state


def probabilities(circuit: Circuit) -> Dict[str, float]:
    """Map final basis probabilities into normalized classical bit strings."""
    state = simulate_statevector(circuit)
    measurements = [
        operation for operation in circuit.operations if isinstance(operation, Measurement)
    ]
    if not measurements:
        raise ValueError("circuit must contain at least one measurement")

    distribution: Dict[str, float] = {}
    for basis_index, amplitude in enumerate(state):
        probability = abs(amplitude) ** 2
        if probability < 1e-15:
            continue
        classical = [0] * circuit.num_clbits
        for measurement in measurements:
            classical[measurement.clbit] = (basis_index >> measurement.qubit) & 1
        key = "".join(str(classical[index]) for index in reversed(range(circuit.num_clbits)))
        distribution[key] = distribution.get(key, 0.0) + probability

    total = sum(distribution.values())
    if total <= 0:
        raise ValueError("simulation produced no measurable probability")
    return {key: value / total for key, value in sorted(distribution.items())}
