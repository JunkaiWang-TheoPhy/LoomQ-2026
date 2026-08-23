"""Grounded L2 agent with QASM validation and one bounded repair turn."""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any, Callable, Dict, List

from .qasm import QASMError, parse_qasm
from .simulator import probabilities


ChatCompletion = Callable[[List[Dict[str, Any]]], Dict[str, Any]]
_QASM_BLOCK = re.compile(
    r"OPENQASM\s+2\.0;.*?(?=^\s*```|\Z)", re.DOTALL | re.MULTILINE | re.IGNORECASE
)


def _capability_payload() -> Dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "backend_capabilities.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _capability_table() -> str:
    return json.dumps(_capability_payload(), ensure_ascii=False, indent=2)


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
    generation_intent = (
        "生成",
        "创建",
        "制备",
        "修复",
        "纠错",
        "改正",
        "generate",
        "create",
        "prepare",
        "repair",
        "fix",
    )
    if any(term in lowered for term in generation_intent):
        return True
    selection_intent = (
        "选哪个",
        "选择哪个",
        "推荐",
        "应该选",
        "应该用",
        "后端",
        "平台",
        "which backend",
        "which platform",
        "choose",
        "select",
        "recommend",
    )
    if any(term in lowered for term in selection_intent):
        return False
    qasm_terms = (
        "qasm",
        "电路",
        "量子态",
        "bell",
        "ghz",
        "测量",
        "纠缠",
    )
    if any(term in lowered for term in qasm_terms):
        return True
    backend_terms = ("排队", "费用", "成本", "backend")
    return not any(term in lowered for term in backend_terms)


def _qasm_from_reply(reply: str) -> str:
    match = _QASM_BLOCK.search(reply)
    if not match:
        raise QASMError("response contains no OpenQASM 2.0 program")
    return match.group(0).strip()


def _qubit_count(prompt: str) -> int | None:
    match = re.search(
        r"(\d+)\s*-?\s*(?:个?\s*)?(?:量子)?(?:比特|qubits?)"
        r"|(?:qubits?)\s*[:=]?\s*(\d+)",
        prompt.lower(),
    )
    return int(match.group(1) or match.group(2)) if match else None


def _requested_qubits(prompt: str, default: int | None = None) -> int | None:
    qubits = _qubit_count(prompt)
    if qubits is not None:
        return qubits
    chinese_digits = {
        "二": 2,
        "两": 2,
        "三": 3,
        "四": 4,
        "五": 5,
        "六": 6,
        "七": 7,
        "八": 8,
        "九": 9,
    }
    for character, value in chinese_digits.items():
        if re.search(character + r"\s*(?:个?\s*)?(?:量子)?比特", prompt.lower()):
            return value
    return default


def _state_goal(prompt: str) -> tuple[str, int] | None:
    lowered = prompt.lower()
    basis = re.search(r"\|\s*([01]+)\s*>", lowered)
    if basis:
        return "computational basis", len(basis.group(1))
    if any(
        term in lowered
        for term in ("均匀叠加", "等概率叠加", "uniform superposition", "equal superposition")
    ):
        qubits = _requested_qubits(prompt)
        return ("uniform superposition", qubits) if qubits is not None else None
    if "w 态" in lowered or "w态" in lowered or re.search(r"\bw(?: state)?\b", lowered):
        return "W", _requested_qubits(prompt, 3) or 3
    if "bell" in lowered or "贝尔" in lowered:
        return "Bell", 2
    if "ghz" not in lowered and "猫态" not in lowered and "最大纠缠" not in lowered:
        return None
    return "GHZ", _requested_qubits(prompt, 3) or 3


def _expected_distribution(prompt: str, name: str, qubits: int) -> Dict[str, float]:
    if name in ("Bell", "GHZ"):
        return {"0" * qubits: 0.5, "1" * qubits: 0.5}
    if name == "W":
        probability = 1.0 / qubits
        return {
            format(1 << index, f"0{qubits}b"): probability for index in range(qubits)
        }
    if name == "uniform superposition":
        probability = 1.0 / (1 << qubits)
        return {
            format(index, f"0{qubits}b"): probability for index in range(1 << qubits)
        }
    if name == "computational basis":
        match = re.search(r"\|\s*([01]+)\s*>", prompt)
        assert match is not None
        return {match.group(1): 1.0}
    raise ValueError(f"unsupported target-state family: {name}")


def _validate_state_goal(prompt: str, qasm: str) -> None:
    goal = _state_goal(prompt)
    if goal is None:
        return
    name, qubits = goal
    circuit = parse_qasm(qasm)
    if circuit.num_qubits != qubits or circuit.num_clbits != qubits:
        raise QASMError(
            f"{name} request requires exactly {qubits} qubits and {qubits} classical bits"
        )
    observed = probabilities(circuit)
    expected = _expected_distribution(prompt, name, qubits)
    states = set(observed) | set(expected)
    distance = math.sqrt(
        sum(
            (math.sqrt(observed.get(state, 0.0)) - math.sqrt(expected.get(state, 0.0)))
            ** 2
            for state in states
        )
    ) / math.sqrt(2.0)
    if 1.0 - distance < 0.999999:
        raise QASMError(f"QASM does not prepare the requested {name} target state")


def _validate_qasm_reply(prompt: str, reply: str) -> None:
    qasm = _qasm_from_reply(reply)
    parse_qasm(qasm)
    _validate_state_goal(prompt, qasm)


def _backend_constraints(prompt: str) -> tuple[int | None, bool, bool, bool, bool]:
    lowered = prompt.lower()
    normalized = re.sub(r"[-_]+", " ", lowered)
    qubits = _qubit_count(prompt)
    no_queue = any(
        term in normalized
        for term in ("零排队", "无排队", "不排队", "zero queue", "no queue")
    )
    free = any(term in lowered for term in ("免费", "零成本", "free", "no cost"))
    qpu = any(term in lowered for term in ("真机", "量子硬件", "qpu"))
    simulator = any(term in lowered for term in ("模拟器", "simulator"))
    return qubits, no_queue, free, qpu, simulator


def _validate_backend_reply(prompt: str, reply: str) -> None:
    qubits, no_queue, free, qpu, simulator = _backend_constraints(prompt)
    compatible: List[str] = []
    all_ids: List[str] = []
    for backend in _capability_payload()["backends"]:
        backend_id = backend["id"]
        all_ids.append(backend_id)
        if qubits is not None and backend["max_qubits"] < qubits:
            continue
        if no_queue and backend["queue"] != "none":
            continue
        if free and not backend["cost"].startswith("free"):
            continue
        if qpu and backend["kind"] != "qpu":
            continue
        if simulator and backend["kind"] != "simulator":
            continue
        compatible.append(backend_id)
    mentioned = [
        backend_id
        for backend_id in all_ids
        if re.search(r"\b" + re.escape(backend_id) + r"\b", reply)
    ]
    if not mentioned or not set(mentioned) & set(compatible):
        requirements = []
        if qubits is not None:
            requirements.append(f">={qubits} qubits")
        if no_queue:
            requirements.append("queue=none")
        if free:
            requirements.append("cost=free")
        if qpu:
            requirements.append("kind=qpu")
        if simulator:
            requirements.append("kind=simulator")
        detail = ", ".join(requirements) or "official backend id"
        raise ValueError(
            f"backend recommendation violates constraints ({detail}); compatible ids: "
            + (", ".join(compatible) if compatible else "none")
        )


def _validate_reply(prompt: str, reply: str) -> None:
    if _expects_qasm(prompt):
        _validate_qasm_reply(prompt, reply)
    else:
        _validate_backend_reply(prompt, reply)


def _deterministic_state_reply(prompt: str) -> str | None:
    goal = _state_goal(prompt)
    if goal is None:
        return None
    name, qubits = goal
    operations: List[str] = []
    if name in ("Bell", "GHZ"):
        operations.append("h q[0];")
        operations.extend(f"cx q[0],q[{index}];" for index in range(1, qubits))
    elif name == "W":
        operations.append("x q[0];")
        for control in range(qubits - 1):
            target = control + 1
            half_angle = math.acos(1.0 / math.sqrt(qubits - control))
            operations.extend(
                [
                    f"ry({half_angle:.17g}) q[{target}];",
                    f"cx q[{control}],q[{target}];",
                    f"ry({-half_angle:.17g}) q[{target}];",
                    f"cx q[{control}],q[{target}];",
                    f"cx q[{target}],q[{control}];",
                ]
            )
    elif name == "uniform superposition":
        operations.extend(f"h q[{index}];" for index in range(qubits))
    elif name == "computational basis":
        match = re.search(r"\|\s*([01]+)\s*>", prompt)
        assert match is not None
        operations.extend(
            f"x q[{index}];"
            for index, bit in enumerate(reversed(match.group(1)))
            if bit == "1"
        )
    else:
        return None
    body = "\n".join(operations)
    return f"""```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[{qubits}];
creg c[{qubits}];
{body}
measure q -> c;
```"""


def chat(prompt: str, completion: ChatCompletion) -> str:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")

    messages: List[Dict[str, Any]] = [
        {"role": "system", "content": _system_prompt()},
        {"role": "user", "content": prompt},
    ]
    first = _assistant_content(completion(messages))
    try:
        _validate_reply(prompt, first)
        return first
    except (QASMError, ValueError) as exc:
        messages.extend(
            [
                {"role": "assistant", "content": first},
                {
                    "role": "user",
                    "content": (
                        "确定性校验未通过："
                        + str(exc)
                        + "。请重新回答，并严格满足原始任务、官方能力表和输出格式。"
                    ),
                },
            ]
        )

    repaired = _assistant_content(completion(messages))
    try:
        _validate_reply(prompt, repaired)
    except (QASMError, ValueError) as exc:
        fallback = _deterministic_state_reply(prompt) if _expects_qasm(prompt) else None
        if fallback is not None:
            _validate_reply(prompt, fallback)
            return fallback
        raise RuntimeError(f"model reply failed deterministic validation after retry: {exc}") from exc
    return repaired
