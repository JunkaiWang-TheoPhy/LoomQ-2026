#!/usr/bin/env python3
"""LoomQ submission adapter contract v1.0.

This file intentionally contains no scoring implementation. Teams may implement
the functions directly or delegate to another language/runtime with subprocess.
"""

from typing import Any, Dict, List, Tuple

try:
    from . import llm_client
    from .loomq.agent import chat
    from .loomq.emitters import emit
    from .loomq.qasm import parse_qasm
    from .loomq.runtime import execute
except ImportError:  # Direct execution from starter_kit/.
    import llm_client
    from loomq.agent import chat
    from loomq.emitters import emit
    from loomq.qasm import parse_qasm
    from loomq.runtime import execute


SUPPORTED_TARGETS = ("spinq", "originq", "braket")


def transpile(qasm_str: str, target: str) -> str:
    """Translate OpenQASM 2.0 into the target backend's native representation."""
    return emit(parse_qasm(qasm_str), target)


def run(qasm_str: str, target: str, shots: int) -> Dict[str, Any]:
    """Execute a circuit and return the unified result schema from the rules."""
    return execute(parse_qasm(qasm_str), target, shots)


def agent_chat(prompt: str) -> str:
    """Optional L2 entry point using the documented LOOMQ_LLM_* environment."""
    return chat(prompt, llm_client.chat_completion)


def compile_hybrid(hybrid_qasm_str: str) -> Tuple[List[str], str]:
    """Optional L3 entry point. Return quantum operations and RISC-V assembly."""
    raise NotImplementedError(
        "L3 is optional; implement compile_hybrid(hybrid_qasm_str) to enter"
    )
