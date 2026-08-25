"""Cross-platform Agent orchestration over LoomQ's validated adapter contract."""

from __future__ import annotations

from typing import Any, Callable, Iterable

from .agent import ChatCompletion, _compatible_backends, chat
from .prooftrace import compile_target
from .qasm import parse_qasm
from .runtime import execute


_LOCAL_BACKENDS = {
    "spinq": "spinq_taurus_simulator",
    "originq": "originq_local_simulator",
    "braket": "braket_local_simulator",
}


def build_cross_platform_plan(
    prompt: str,
    completion: ChatCompletion,
    history: object = None,
    *,
    shots: int = 128,
    targets: Iterable[str] = ("spinq", "originq", "braket"),
) -> dict[str, Any]:
    """Generate once, then validate and replay the same QASM on every adapter.

    The function never submits cloud jobs.  It produces a portable plan with
    native IR previews, local execution results, capability-table routing, and
    a cross-platform consistency check.  Credentials remain outside this path.
    """

    if not isinstance(shots, int) or isinstance(shots, bool) or shots <= 0 or shots > 1_000_000:
        raise ValueError("shots must be an integer between 1 and 1000000")
    selected_targets = tuple(dict.fromkeys(targets))
    if not selected_targets or any(target not in _LOCAL_BACKENDS for target in selected_targets):
        raise ValueError("targets must be a non-empty subset of spinq, originq, braket")

    reply = chat(prompt, completion, history)
    marker = reply.find("OPENQASM 2.0;")
    if marker < 0:
        raise RuntimeError("cross-platform plan requires a validated OpenQASM response")
    qasm = reply[marker:]
    qasm = qasm.split("```", 1)[0].strip()
    circuit = parse_qasm(qasm)
    compatible = _compatible_backends(prompt)
    if not compatible:
        raise ValueError("no backend in the official capability table satisfies the request")
    recommended = compatible[0]

    adapters: list[dict[str, Any]] = []
    reference_counts: dict[str, int] | None = None
    for target in selected_targets:
        native_ir = compile_target(qasm, target)
        result = execute(circuit, target, shots)
        if reference_counts is None:
            reference_counts = dict(result["counts"])
        adapters.append(
            {
                "target": target,
                "backend_id": _LOCAL_BACKENDS[target],
                "native_ir": native_ir,
                "result": result,
                "counts_match_reference": dict(result["counts"]) == reference_counts,
            }
        )

    return {
        "schema_version": "loomq-cross-platform-agent-plan-v1",
        "prompt": prompt,
        "agent_reply": reply,
        "qasm": qasm,
        "shots": shots,
        "platforms": list(selected_targets),
        "platform_count": len(selected_targets),
        "backend_candidates": [backend["id"] for backend in compatible],
        "recommended_backend": recommended["id"],
        "adapters": adapters,
        "consistency": {
            "reference_target": selected_targets[0],
            "all_counts_equal": all(item["counts_match_reference"] for item in adapters),
        },
    }
