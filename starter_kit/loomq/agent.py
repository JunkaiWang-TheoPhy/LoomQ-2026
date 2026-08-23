"""Grounded L2 agent with QASM validation and one bounded repair turn."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List

from .qasm import QASMError, parse_qasm


ChatCompletion = Callable[[List[Dict[str, Any]]], Dict[str, Any]]
_QASM_BLOCK = re.compile(
    r"OPENQASM\s+2\.0;.*?(?=^\s*```|\Z)", re.DOTALL | re.MULTILINE | re.IGNORECASE
)


def _capability_table() -> str:
    path = Path(__file__).resolve().parents[1] / "backend_capabilities.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _system_prompt() -> str:
    return """你是 LoomQ 量子计算助理。你的输出会由确定性程序验证。

任务边界：
1. 若用户要求生成或修复量子电路，返回完整可执行的 OpenQASM 2.0。必须包含
   OPENQASM 2.0、qelib1.inc、qreg、creg 和测量；门只能使用
   h, x, s, sdg, t, tdg, rz, ry, cx, cu1, swap, ccx。保留用户声明的目标态。
2. 若用户要求选择后端，只能依据下方官方能力表。回答中必须原样包含至少一个
   规范后端标识（id 字段），并同时满足比特数、硬件种类、排队和费用约束。
3. 不编造运行结果、job ID、平台能力或账号状态。不要输出 API Key。
4. 对零基础用户使用简洁中文解释，但把可机读 QASM 放在独立代码块中。

官方后端能力表：
""" + _capability_table()


def _assistant_content(response: Dict[str, Any]) -> str:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("LoomQ L2 API returned no assistant content") from exc
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LoomQ L2 API returned no assistant content")
    return content


def _expects_qasm(prompt: str) -> bool:
    lowered = prompt.lower()
    qasm_terms = (
        "qasm",
        "电路",
        "量子态",
        "纠错",
        "修复",
        "生成",
        "bell",
        "ghz",
        "测量",
        "纠缠",
    )
    if any(term in lowered for term in qasm_terms):
        return True
    backend_terms = ("后端", "平台", "排队", "费用", "成本", "backend")
    return not any(term in lowered for term in backend_terms)


def _validate_qasm_reply(reply: str) -> None:
    match = _QASM_BLOCK.search(reply)
    if not match:
        raise QASMError("response contains no OpenQASM 2.0 program")
    parse_qasm(match.group(0).strip())


def chat(prompt: str, completion: ChatCompletion) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": prompt},
    ]
    first = _assistant_content(completion(messages))
    if not _expects_qasm(prompt) and not _QASM_BLOCK.search(first):
        return first

    try:
        _validate_qasm_reply(first)
        return first
    except QASMError as exc:
        messages.extend(
            [
                {"role": "assistant", "content": first},
                {
                    "role": "user",
                    "content": (
                        "确定性校验未通过："
                        + str(exc)
                        + "。请重新输出完整、语法正确且实现原意的 OpenQASM 2.0。"
                    ),
                },
            ]
        )

    repaired = _assistant_content(completion(messages))
    try:
        _validate_qasm_reply(repaired)
    except QASMError as exc:
        raise RuntimeError(f"model did not produce valid OpenQASM 2.0 after retry: {exc}") from exc
    return repaired
