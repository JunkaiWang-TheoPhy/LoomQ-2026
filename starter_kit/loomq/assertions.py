"""Local assertion checks and execution diagnostics for LoomQ circuits."""

from __future__ import annotations

import cmath
import math
from collections.abc import Mapping, Sequence
from statistics import NormalDist
from typing import Any

from .qasm import Circuit, Measurement, Operation, parse_qasm
from .simulator import _iter_exact_state_steps, probabilities


_FINITE_SHOT_CONFIDENCE_MODE = "finite-shots"
_EXACT_LOCAL_MODE = "exact-local"
_PROVIDER_PROBABILITY_MODE = "provider-probabilities"
_STATE_TOLERANCE = 1e-12
_DIAGNOSIS_MAX_QUBITS = 8


def _is_real_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_unit_interval(value: object, field: str) -> float:
    if not _is_real_number(value):
        raise ValueError(f"{field} must be a real number in [0, 1]")
    number = float(value)
    if not math.isfinite(number) or not 0.0 <= number <= 1.0:
        raise ValueError(f"{field} must be a real number in [0, 1]")
    return number


def _require_confidence(confidence: object) -> float:
    if not _is_real_number(confidence):
        raise ValueError("confidence must be a real number in (0, 1)")
    level = float(confidence)
    if not 0.0 < level < 1.0:
        raise ValueError("confidence must be a real number in (0, 1)")
    return level


def _require_shots(shots: object) -> int:
    if not isinstance(shots, int) or isinstance(shots, bool) or shots <= 0:
        raise ValueError("shots must be a positive integer")
    return shots


def _normalize_probability_distribution(
    distribution: Mapping[str, float | int],
) -> tuple[dict[str, float], int]:
    if not isinstance(distribution, Mapping) or not distribution:
        raise ValueError("distribution must be a non-empty mapping")

    normalized: dict[str, float] = {}
    width: int | None = None
    total = 0.0
    for state, raw_value in distribution.items():
        if not isinstance(state, str) or not state or any(bit not in "01" for bit in state):
            raise ValueError("distribution keys must be non-empty bit strings")
        if width is None:
            width = len(state)
        elif len(state) != width:
            raise ValueError("distribution keys must all have the same width")
        if not _is_real_number(raw_value):
            raise ValueError("distribution values must be finite non-negative real numbers")
        value = float(raw_value)
        if not math.isfinite(value) or value < 0.0:
            raise ValueError("distribution values must be finite non-negative real numbers")
        total += value
        normalized[state] = value
    if total <= 0.0:
        raise ValueError("distribution must have positive total mass")
    return ({state: value / total for state, value in normalized.items()}, width or 0)


def _normalize_count_distribution(
    distribution: Mapping[str, float | int], shots: int
) -> tuple[dict[str, int], dict[str, float], int]:
    if not isinstance(distribution, Mapping) or not distribution:
        raise ValueError("distribution must be a non-empty mapping")

    counts: dict[str, int] = {}
    width: int | None = None
    total = 0
    for state, raw_value in distribution.items():
        if not isinstance(state, str) or not state or any(bit not in "01" for bit in state):
            raise ValueError("distribution keys must be non-empty bit strings")
        if width is None:
            width = len(state)
        elif len(state) != width:
            raise ValueError("distribution keys must all have the same width")
        if not isinstance(raw_value, int) or isinstance(raw_value, bool) or raw_value < 0:
            raise ValueError("finite-shot distributions must contain non-negative integer counts")
        total += raw_value
        counts[state] = raw_value
    if total != shots:
        raise ValueError("finite-shot distributions must sum to shots")
    if total <= 0:
        raise ValueError("finite-shot distributions must contain at least one shot")
    normalized = {state: count / shots for state, count in counts.items()}
    return counts, normalized, width or 0


def _normalize_states(states: object, width: int) -> list[str]:
    if not isinstance(states, Sequence) or isinstance(states, (str, bytes)):
        raise ValueError("states must be a non-empty list of unique bit strings")
    normalized: list[str] = []
    seen: set[str] = set()
    for state in states:
        if not isinstance(state, str) or len(state) != width or any(bit not in "01" for bit in state):
            raise ValueError("states must be a non-empty list of unique bit strings")
        if state in seen:
            raise ValueError("states must be a non-empty list of unique bit strings")
        seen.add(state)
        normalized.append(state)
    if not normalized:
        raise ValueError("states must be a non-empty list of unique bit strings")
    return normalized


def _normalize_bits(bits: object, width: int) -> list[int]:
    if not isinstance(bits, Sequence) or isinstance(bits, (str, bytes)) or not bits:
        raise ValueError("bits must be a non-empty list of bit indices")
    normalized: list[int] = []
    seen: set[int] = set()
    for bit in bits:
        if not isinstance(bit, int) or isinstance(bit, bool):
            raise ValueError("bits must be a non-empty list of bit indices")
        if bit < 0 or bit >= width:
            raise ValueError("bit index out of range")
        if bit in seen:
            raise ValueError("bits must not contain duplicates")
        seen.add(bit)
        normalized.append(bit)
    return normalized


def _validate_expected_parity(expected: object) -> str:
    if expected not in {"even", "odd"}:
        raise ValueError("expected parity must be 'even' or 'odd'")
    return expected


def _support_probability(distribution: Mapping[str, float], states: Sequence[str]) -> float:
    return sum(distribution.get(state, 0.0) for state in states)


def _parity_probability(distribution: Mapping[str, float], bits: Sequence[int], expected: str) -> float:
    target = 0 if expected == "even" else 1
    probability = 0.0
    for state, value in distribution.items():
        parity = sum(int(state[-1 - bit]) for bit in bits) % 2
        if parity == target:
            probability += value
    return probability


def _uniformity_total_variation(distribution: Mapping[str, float], states: Sequence[str]) -> float:
    state_set = set(states)
    target_probability = 1.0 / len(states)
    inside = sum(abs(distribution.get(state, 0.0) - target_probability) for state in states)
    outside = sum(value for state, value in distribution.items() if state not in state_set)
    return (inside + outside) / 2.0


def _wilson_interval(successes: int, shots: int, confidence: float) -> tuple[float, float]:
    alpha = 1.0 - confidence
    z_score = NormalDist().inv_cdf(1.0 - alpha / 2.0)
    proportion = successes / shots
    z_square = z_score * z_score
    denominator = 1.0 + z_square / shots
    center = (proportion + z_square / (2.0 * shots)) / denominator
    margin = z_score * math.sqrt(
        (proportion * (1.0 - proportion) + z_square / (4.0 * shots)) / shots
    ) / denominator
    return (max(0.0, center - margin), min(1.0, center + margin))


def _uniformity_interval(
    distribution: Mapping[str, float], states: Sequence[str], shots: int, confidence: float
) -> tuple[float, float]:
    empirical = _uniformity_total_variation(distribution, states)
    alpha = 1.0 - confidence
    categories = len(states) + 1
    radius = categories * math.sqrt(math.log(2.0 * categories / alpha) / (2.0 * shots)) / 2.0
    return (max(0.0, empirical - radius), min(1.0, empirical + radius))


def _assertion_result(
    *,
    index: int,
    kind: str,
    evidence_mode: str,
    observed_value: float,
    threshold_key: str,
    threshold_value: float,
    lower_bound: float | None,
    upper_bound: float | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    if threshold_key == "minimum_probability":
        if lower_bound is None:
            status = "pass" if observed_value >= threshold_value else "fail"
        elif lower_bound >= threshold_value:
            status = "pass"
        elif upper_bound is not None and upper_bound < threshold_value:
            status = "fail"
        else:
            status = "inconclusive"
    else:
        if lower_bound is None:
            status = "pass" if observed_value <= threshold_value else "fail"
        elif upper_bound is not None and upper_bound <= threshold_value:
            status = "pass"
        elif lower_bound > threshold_value:
            status = "fail"
        else:
            status = "inconclusive"

    result = {
        "index": index,
        "kind": kind,
        "status": status,
        "evidence_mode": evidence_mode,
        threshold_key: threshold_value,
        **extra,
    }
    if threshold_key == "minimum_probability":
        result["observed_probability"] = observed_value
    else:
        result["observed_total_variation"] = observed_value
    if lower_bound is not None and upper_bound is not None:
        result["confidence_interval"] = [lower_bound, upper_bound]
    return result


def evaluate_distribution_assertions(
    distribution: Mapping[str, float | int],
    assertions: list[dict],
    *,
    shots: int | None = None,
    confidence: float = 0.95,
) -> list[dict]:
    if not isinstance(assertions, list):
        raise ValueError("assertions must be a list")
    confidence_level = _require_confidence(confidence)

    evidence_mode = _PROVIDER_PROBABILITY_MODE
    counts: dict[str, int] | None = None
    if shots is None:
        normalized, width = _normalize_probability_distribution(distribution)
        lower_bound = upper_bound = None
    else:
        shot_count = _require_shots(shots)
        counts, normalized, width = _normalize_count_distribution(distribution, shot_count)
        evidence_mode = _FINITE_SHOT_CONFIDENCE_MODE

    report: list[dict] = []
    for index, assertion in enumerate(assertions):
        if not isinstance(assertion, dict):
            raise ValueError("assertions must contain dictionaries")
        kind = assertion.get("kind")
        if kind == "support":
            states = _normalize_states(assertion.get("states"), width)
            threshold = _require_unit_interval(assertion.get("minimum_probability"), "minimum_probability")
            observed = _support_probability(normalized, states)
            interval = None
            if counts is not None and shots is not None:
                successes = sum(counts.get(state, 0) for state in states)
                interval = _wilson_interval(successes, shots, confidence_level)
            report.append(
                _assertion_result(
                    index=index,
                    kind=kind,
                    evidence_mode=evidence_mode,
                    observed_value=observed,
                    threshold_key="minimum_probability",
                    threshold_value=threshold,
                    lower_bound=None if interval is None else interval[0],
                    upper_bound=None if interval is None else interval[1],
                    extra={"states": states},
                )
            )
            continue
        if kind == "parity":
            bits = _normalize_bits(assertion.get("bits"), width)
            expected = _validate_expected_parity(assertion.get("expected"))
            threshold = _require_unit_interval(assertion.get("minimum_probability"), "minimum_probability")
            observed = _parity_probability(normalized, bits, expected)
            interval = None
            if counts is not None and shots is not None:
                successes = 0
                for state, count in counts.items():
                    parity = sum(int(state[-1 - bit]) for bit in bits) % 2
                    if parity == (0 if expected == "even" else 1):
                        successes += count
                interval = _wilson_interval(successes, shots, confidence_level)
            report.append(
                _assertion_result(
                    index=index,
                    kind=kind,
                    evidence_mode=evidence_mode,
                    observed_value=observed,
                    threshold_key="minimum_probability",
                    threshold_value=threshold,
                    lower_bound=None if interval is None else interval[0],
                    upper_bound=None if interval is None else interval[1],
                    extra={"bits": bits, "expected": expected},
                )
            )
            continue
        if kind == "uniformity":
            states = _normalize_states(assertion.get("states"), width)
            threshold = _require_unit_interval(
                assertion.get("maximum_total_variation"), "maximum_total_variation"
            )
            observed = _uniformity_total_variation(normalized, states)
            interval = None
            if counts is not None and shots is not None:
                interval = _uniformity_interval(normalized, states, shots, confidence_level)
            report.append(
                _assertion_result(
                    index=index,
                    kind=kind,
                    evidence_mode=evidence_mode,
                    observed_value=observed,
                    threshold_key="maximum_total_variation",
                    threshold_value=threshold,
                    lower_bound=None if interval is None else interval[0],
                    upper_bound=None if interval is None else interval[1],
                    extra={"states": states},
                )
            )
            continue
        raise ValueError(f"unsupported assertion kind: {kind}")
    return report


def evaluate_assertions(circuit: Circuit, assertions: list[dict]) -> list[dict]:
    report = evaluate_distribution_assertions(probabilities(circuit), assertions)
    for item in report:
        item["evidence_mode"] = _EXACT_LOCAL_MODE
    return report


def _measurement_mappings(circuit: Circuit) -> list[tuple[int, int]]:
    return [
        (operation.qubit, operation.clbit)
        for operation in circuit.operations
        if isinstance(operation, Measurement)
    ]


def _gate_operations(circuit: Circuit) -> list[Operation]:
    return [
        operation
        for operation in circuit.operations
        if not isinstance(operation, Measurement)
    ]


def _format_operation(operation: Operation | None) -> dict[str, Any] | None:
    if operation is None:
        return None
    if isinstance(operation, Measurement):
        return {"kind": "measure", "qubit": operation.qubit, "clbit": operation.clbit}
    return {
        "kind": "gate",
        "gate": operation.name,
        "qubits": list(operation.qubits),
        "parameter": operation.parameter,
    }


def _canonicalize_global_phase(state: Sequence[complex]) -> list[complex]:
    pivot = next((amplitude for amplitude in state if abs(amplitude) > _STATE_TOLERANCE), None)
    if pivot is None:
        return list(state)
    phase = cmath.phase(pivot)
    factor = cmath.exp(-1j * phase)
    return [amplitude * factor for amplitude in state]


def _max_amplitude_delta(left: Sequence[complex], right: Sequence[complex]) -> float:
    return max(abs(a - b) for a, b in zip(left, right)) if left else 0.0


def _state_steps(circuit: Circuit) -> list[list[complex]]:
    steps: list[list[complex]] = []
    for operation, state in _iter_exact_state_steps(circuit):
        if operation["kind"] == "measure":
            continue
        steps.append(_canonicalize_global_phase(state))
    return steps


def _total_variation_distance(
    left: Mapping[str, float], right: Mapping[str, float]
) -> float:
    keys = sorted(set(left) | set(right))
    return sum(abs(left.get(key, 0.0) - right.get(key, 0.0)) for key in keys) / 2.0


def diagnose_mutation(reference_qasm: str, candidate_qasm: str) -> dict[str, Any]:
    reference = parse_qasm(reference_qasm)
    candidate = parse_qasm(candidate_qasm)

    if (
        reference.num_qubits != candidate.num_qubits
        or reference.num_clbits != candidate.num_clbits
    ):
        return {
            "scope": "structural-mismatch",
            "equivalent_output_distribution": False,
            "first_divergent_gate": None,
            "reason": "register declarations differ",
            "reference_measurements": _measurement_mappings(reference),
            "candidate_measurements": _measurement_mappings(candidate),
        }
    if _measurement_mappings(reference) != _measurement_mappings(candidate):
        return {
            "scope": "structural-mismatch",
            "equivalent_output_distribution": False,
            "first_divergent_gate": None,
            "reason": "measurement mappings differ",
            "reference_measurements": _measurement_mappings(reference),
            "candidate_measurements": _measurement_mappings(candidate),
        }
    if reference.num_qubits > _DIAGNOSIS_MAX_QUBITS:
        raise ValueError(
            f"mutation diagnosis supports at most {_DIAGNOSIS_MAX_QUBITS} qubits"
        )

    reference_steps = _state_steps(reference)
    candidate_steps = _state_steps(candidate)
    reference_gates = _gate_operations(reference)
    candidate_gates = _gate_operations(candidate)
    divergence_index: int | None = None
    amplitude_delta = 0.0
    for gate_index in range(max(len(reference_gates), len(candidate_gates))):
        reference_state = (
            reference_steps[gate_index + 1]
            if gate_index + 1 < len(reference_steps)
            else reference_steps[-1]
        )
        candidate_state = (
            candidate_steps[gate_index + 1]
            if gate_index + 1 < len(candidate_steps)
            else candidate_steps[-1]
        )
        delta = _max_amplitude_delta(reference_state, candidate_state)
        if delta > _STATE_TOLERANCE:
            divergence_index = gate_index
            amplitude_delta = delta
            break

    reference_distribution = probabilities(reference)
    candidate_distribution = probabilities(candidate)
    distance = _total_variation_distance(reference_distribution, candidate_distribution)
    return {
        "scope": "exact-up-to-global-phase-at-zero-input",
        "equivalent_output_distribution": distance <= _STATE_TOLERANCE,
        "first_divergent_gate": divergence_index,
        "reference_operation": None
        if divergence_index is None or divergence_index >= len(reference_gates)
        else _format_operation(reference_gates[divergence_index]),
        "candidate_operation": None
        if divergence_index is None or divergence_index >= len(candidate_gates)
        else _format_operation(candidate_gates[divergence_index]),
        "max_amplitude_delta": amplitude_delta,
        "final_distribution_distance": distance,
    }


def diagnose_observed_execution(
    circuit: Circuit,
    observed: Mapping[str, float | int],
    assertions: list[dict],
    *,
    shots: int | None = None,
) -> dict[str, Any]:
    reference_report = evaluate_assertions(circuit, assertions)
    if any(item["status"] != "pass" for item in reference_report):
        return {
            "classification": "reference-program-fails",
            "reference_assertions": reference_report,
            "observed_assertions": [],
            "attribution_caveat": (
                "The reference circuit does not satisfy the requested assertions locally, "
                "so this result does not attribute the mismatch to execution."
            ),
        }

    observed_report = evaluate_distribution_assertions(observed, assertions, shots=shots)
    statuses = {item["status"] for item in observed_report}
    if statuses == {"pass"}:
        classification = "consistent-with-reference"
    elif "fail" in statuses:
        classification = "execution-deviation-detected"
    else:
        classification = "inconclusive"
    return {
        "classification": classification,
        "reference_assertions": reference_report,
        "observed_assertions": observed_report,
        "attribution_caveat": (
            "This comparison only reports whether the observed data matches the local "
            "reference checks; it does not identify a physical cause."
        ),
    }
