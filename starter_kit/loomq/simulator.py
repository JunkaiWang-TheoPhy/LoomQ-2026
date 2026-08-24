"""Small exact state-vector engine for the published LoomQ gate subset."""

from __future__ import annotations

import cmath
import math
from typing import Dict, Iterator, List, Sequence, Tuple

from .qasm import Circuit, Gate, Measurement


StateVector = List[complex]
SparseState = Dict[int, complex]
Matrix2 = Tuple[Tuple[complex, complex], Tuple[complex, complex]]
MAX_SIMULATOR_QUBITS = 20
MAX_LOCAL_QUBITS = 30
MAX_SPARSE_STATES = 1_000_000


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


def _initial_state(num_qubits: int) -> StateVector:
    state: StateVector = [0j] * (1 << num_qubits)
    state[0] = 1 + 0j
    return state


def _iter_exact_state_steps(
    circuit: Circuit,
) -> Iterator[Tuple[Dict[str, object], StateVector]]:
    if circuit.num_qubits > MAX_SIMULATOR_QUBITS:
        raise ValueError(
            f"local statevector simulation supports at most {MAX_SIMULATOR_QUBITS} qubits"
        )

    state = _initial_state(circuit.num_qubits)
    yield {"kind": "initial", "label": "initial |0…0⟩"}, state.copy()

    measurements: List[Measurement] = []
    measurement_seen = False
    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            measurement_seen = True
            measurements.append(operation)
            continue
        if measurement_seen:
            raise ValueError("mid-circuit measurement is outside the LoomQ L1 contract")
        _apply_gate(state, operation)
        yield (
            {
                "kind": "gate",
                "gate": operation.name,
                "qubits": list(operation.qubits),
                "parameter": operation.parameter,
            },
            state.copy(),
        )
    if measurements:
        yield (
            {
                "kind": "measure",
                "mappings": [
                    {"qubit": item.qubit, "clbit": item.clbit}
                    for item in measurements
                ],
            },
            state.copy(),
        )


def simulate_statevector(circuit: Circuit) -> StateVector:
    """Return the final state before terminal measurements."""
    final_state: StateVector | None = None
    for _operation, state in _iter_exact_state_steps(circuit):
        final_state = state
    return final_state if final_state is not None else _initial_state(circuit.num_qubits)


def _simulate_sparse(circuit: Circuit) -> SparseState:
    """Simulate up to 30 qubits while bounding populated basis states."""
    if circuit.num_qubits > MAX_LOCAL_QUBITS:
        raise ValueError(
            f"local execution supports at most {MAX_LOCAL_QUBITS} qubits"
        )

    state: SparseState = {0: 1 + 0j}
    measurement_seen = False
    for operation in circuit.operations:
        if isinstance(operation, Measurement):
            measurement_seen = True
            continue
        if measurement_seen:
            raise ValueError("mid-circuit measurement is outside the LoomQ L1 contract")

        if len(operation.qubits) == 1:
            matrix = _single_matrix(operation)
            mask = 1 << operation.qubits[0]
            pairs: Dict[int, List[complex]] = {}
            for index, amplitude in state.items():
                zero_index = index & ~mask
                pair = pairs.setdefault(zero_index, [0j, 0j])
                pair[1 if index & mask else 0] = amplitude
            updated: SparseState = {}
            for zero_index, (zero, one) in pairs.items():
                one_index = zero_index | mask
                zero_result = matrix[0][0] * zero + matrix[0][1] * one
                one_result = matrix[1][0] * zero + matrix[1][1] * one
                if abs(zero_result) ** 2 > 1e-15:
                    updated[zero_index] = zero_result
                if abs(one_result) ** 2 > 1e-15:
                    updated[one_index] = one_result
                if len(updated) > MAX_SPARSE_STATES:
                    raise ValueError(
                        "local sparse simulation exceeds the 1000000 "
                        "populated-state safety limit"
                    )
            state = updated
        elif operation.name == "cx":
            control, target = operation.qubits
            control_mask, target_mask = 1 << control, 1 << target
            state = {
                index ^ target_mask if index & control_mask else index: amplitude
                for index, amplitude in state.items()
            }
        elif operation.name == "ccx":
            left, right, target = operation.qubits
            controls = (1 << left) | (1 << right)
            target_mask = 1 << target
            state = {
                index ^ target_mask if index & controls == controls else index: amplitude
                for index, amplitude in state.items()
            }
        elif operation.name == "swap":
            left_mask, right_mask = 1 << operation.qubits[0], 1 << operation.qubits[1]
            swapped: SparseState = {}
            for index, amplitude in state.items():
                if bool(index & left_mask) != bool(index & right_mask):
                    index ^= left_mask | right_mask
                swapped[index] = amplitude
            state = swapped
        elif operation.name == "cu1":
            assert operation.parameter is not None
            mask = (1 << operation.qubits[0]) | (1 << operation.qubits[1])
            phase = cmath.exp(1j * operation.parameter)
            state = {
                index: amplitude * phase if index & mask == mask else amplitude
                for index, amplitude in state.items()
            }
        else:
            raise ValueError(f"unsupported simulated gate: {operation.name}")

        if len(state) > MAX_SPARSE_STATES:
            raise ValueError(
                "local sparse simulation exceeds the 1000000 populated-state safety limit"
            )
    return state


def _state_snapshot(state: Sequence[complex], num_qubits: int, max_states: int) -> Dict[str, object]:
    populated = [
        (index, amplitude, abs(amplitude) ** 2)
        for index, amplitude in enumerate(state)
        if abs(amplitude) ** 2 > 1e-15
    ]
    total = sum(probability for _index, _amplitude, probability in populated)
    ranked = sorted(populated, key=lambda item: (-item[2], item[0]))
    visible = ranked[:max_states]
    states = []
    for index, amplitude, probability in visible:
        states.append(
            {
                "basis": format(index, f"0{num_qubits}b"),
                "probability": round(probability / total, 15),
                "amplitude_real": round(amplitude.real, 15),
                "amplitude_imag": round(amplitude.imag, 15),
                "phase_radians": round(cmath.phase(amplitude), 15),
            }
        )
    return {
        "states": states,
        "truncated": len(populated) > max_states,
        "omitted_states": max(0, len(populated) - max_states),
    }


def _gate_explanation(gate: Gate) -> str:
    explanations = {
        "h": "H 门混合 0 与 1 的振幅；后续门可以让这些路径相长或相消。",
        "x": "X 门交换目标比特的 0 与 1 振幅。",
        "s": "S 门给 |1⟩ 分量增加 π/2 相位，概率暂时不变。",
        "sdg": "S† 门给 |1⟩ 分量减少 π/2 相位，概率暂时不变。",
        "t": "T 门给 |1⟩ 分量增加 π/4 相位。",
        "tdg": "T† 门给 |1⟩ 分量减少 π/4 相位。",
        "rz": "RZ 门改变 0、1 分量的相对相位。",
        "ry": "RY 门在 0 与 1 的振幅之间做实数旋转。",
        "cx": "CX 仅在控制比特为 1 时翻转目标比特，可建立跨比特相关。",
        "cu1": "CU1 仅给两个比特都为 1 的路径增加相位。",
        "swap": "SWAP 交换两个量子比特承载的状态。",
        "ccx": "CCX 仅在两个控制比特都为 1 时翻转目标比特。",
    }
    return explanations[gate.name]


def trace_statevector(
    circuit: Circuit, *, max_qubits: int = 8, max_states: int = 16
) -> List[Dict[str, object]]:
    """Return a bounded, JSON-safe state snapshot after every circuit step."""
    if circuit.num_qubits > max_qubits:
        raise ValueError(f"state trace supports at most {max_qubits} qubits")
    if max_states <= 0:
        raise ValueError("max_states must be positive")

    events: List[Dict[str, object]] = []

    def append(
        operation: Dict[str, object], explanation: str, state: Sequence[complex]
    ) -> None:
        snapshot = _state_snapshot(state, circuit.num_qubits, max_states)
        events.append(
            {
                "step": len(events),
                "operation": operation,
                "explanation": explanation,
                **snapshot,
            }
        )

    for operation, state in _iter_exact_state_steps(circuit):
        if operation["kind"] == "initial":
            explanation = "所有量子比特从 |0⟩ 开始；位串左侧是高位，q[0] 在最右侧。"
        elif operation["kind"] == "gate":
            explanation = _gate_explanation(
                Gate(
                    operation["gate"],
                    tuple(operation["qubits"]),
                    operation["parameter"],
                )
            )
        else:
            explanation = "测量把量子路径映射为经典位；这里展示的是测量前的精确概率，不是假造的单次结果。"
        append(operation, explanation, state)
    return events


def probabilities(circuit: Circuit) -> Dict[str, float]:
    """Map final basis probabilities into normalized classical bit strings."""
    if circuit.num_qubits <= MAX_SIMULATOR_QUBITS:
        basis_states = enumerate(simulate_statevector(circuit))
    else:
        basis_states = _simulate_sparse(circuit).items()
    measurements = [
        operation for operation in circuit.operations if isinstance(operation, Measurement)
    ]
    if not measurements:
        raise ValueError("circuit must contain at least one measurement")

    distribution: Dict[str, float] = {}
    for basis_index, amplitude in basis_states:
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
