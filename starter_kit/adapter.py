#!/usr/bin/env python3
"""LoomQ submission adapter contract v1.0.

This file intentionally contains no scoring implementation. Teams may implement
the functions directly or delegate to another language/runtime with subprocess.
"""

from typing import Any, Dict, List, Tuple

try:
    from . import llm_client
    from .loomq.agent import chat
    from .loomq.hybrid import compile_hybrid as compile_hybrid_program
    from .loomq.hybrid_paths import (
        certify_hybrid_paths as certify_hybrid_paths_program,
        verify_hybrid_path_certificate as verify_hybrid_path_certificate_program,
    )
    from .loomq.prooftrace import compile_target, compile_with_proof
    from .loomq.hybrid_trace import trace_hybrid as trace_hybrid_program
    from .loomq.qasm import parse_qasm
    from .loomq.runtime import execute
except ImportError:  # Direct execution from starter_kit/.
    import llm_client
    from loomq.agent import chat
    from loomq.hybrid import compile_hybrid as compile_hybrid_program
    from loomq.hybrid_paths import (
        certify_hybrid_paths as certify_hybrid_paths_program,
        verify_hybrid_path_certificate as verify_hybrid_path_certificate_program,
    )
    from loomq.prooftrace import compile_target, compile_with_proof
    from loomq.hybrid_trace import trace_hybrid as trace_hybrid_program
    from loomq.qasm import parse_qasm
    from loomq.runtime import execute


SUPPORTED_TARGETS = ("spinq", "originq", "braket")


def transpile(qasm_str: str, target: str) -> str:
    """Translate OpenQASM 2.0 into the target backend's native representation."""
    return compile_target(qasm_str, target)


def transpile_with_proof(qasm_str: str, target: str) -> Tuple[str, Dict[str, object]]:
    """Translate QASM and return its deterministic ProofTrace certificate."""
    return compile_with_proof(qasm_str, target)


def prooftrace(qasm_str: str, target: str) -> Dict[str, object]:
    """Return the proof certificate without changing the public transpile contract."""
    _native_ir, certificate = compile_with_proof(qasm_str, target)
    return certificate


def run(qasm_str: str, target: str, shots: int) -> Dict[str, Any]:
    """Execute a circuit and return the unified result schema from the rules."""
    return execute(parse_qasm(qasm_str), target, shots)


def agent_chat(prompt: str, history: object = None) -> str:
    """Optional L2 entry point using the documented LOOMQ_LLM_* environment."""
    return chat(prompt, llm_client.chat_completion, history)


def compile_hybrid(hybrid_qasm_str: str) -> Tuple[List[str], str]:
    """Optional L3 entry point. Return quantum operations and RISC-V assembly."""
    return compile_hybrid_program(hybrid_qasm_str)


def trace_hybrid(hybrid_qasm_str: str, measurement_bits: object) -> Dict[str, Any]:
    """Optional L3 replay entry point preserving compile_hybrid's published tuple contract."""
    return trace_hybrid_program(hybrid_qasm_str, measurement_bits)


def certify_hybrid_paths(hybrid_qasm_str: str, max_outcomes: int = 256) -> Dict[str, Any]:
    """Return an exact exhaustive certificate for bounded Hybrid-QASM classical outcomes."""
    return certify_hybrid_paths_program(hybrid_qasm_str, max_outcomes=max_outcomes)


def verify_hybrid_path_certificate(
    hybrid_qasm_str: str, certificate: Dict[str, Any]
) -> Dict[str, Any]:
    """Recompute a Hybrid-QASM certificate from source instead of trusting stored hashes."""
    return verify_hybrid_path_certificate_program(hybrid_qasm_str, certificate)


def hybrid_path_certificate(hybrid_qasm_str: str, max_outcomes: int = 256) -> Dict[str, Any]:
    """Compatibility alias for callers still using the older entry point name."""
    return certify_hybrid_paths(hybrid_qasm_str, max_outcomes=max_outcomes)
