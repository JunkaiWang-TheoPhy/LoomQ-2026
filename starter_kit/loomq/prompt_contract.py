"""Deterministic semantic contracts for LoomQ L2 natural-language requests."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from typing import Any


PROMPT_CONTRACT_SCHEMA = "loomq-prompt-contract-v1"

_FENCED_CODE = re.compile(r"```.*?(?:```|\Z)", re.DOTALL)
_DASH_TRANSLATION = str.maketrans(
    {
        "‐": "-",
        "‑": "-",
        "‒": "-",
        "–": "-",
        "—": "-",
        "−": "-",
    }
)
_ENGLISH_NUMBERS = {
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
}
_CHINESE_NUMBERS = {
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


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _sha256_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _semantic_text(prompt: str) -> tuple[str, int]:
    normalized = unicodedata.normalize("NFKC", prompt).translate(_DASH_TRANSLATION)
    removed = len(_FENCED_CODE.findall(normalized))
    without_code = _FENCED_CODE.sub(" ", normalized)
    return re.sub(r"\s+", " ", without_code).strip().lower(), removed


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _contains_unnegated(text: str, terms: tuple[str, ...]) -> bool:
    """Return whether a term occurs outside a locally negated clause."""
    for term in terms:
        start = 0
        while True:
            index = text.find(term, start)
            if index < 0:
                break
            prefix = text[:index]
            clause = re.split(
                r"[,.;:!?，。；！？]|\b(?:but|however|except)\b|(?:但是|但|不过)",
                prefix,
            )[-1]
            directly_negated = re.search(
                r"(?:\b(?:do not|don't|does not|doesn't|not)\b|"
                r"(?:不要|不需要|无需|并非|不是))[^,.;:!?，。；！？]{0,64}$",
                clause,
            )
            if directly_negated is None:
                return True
            start = index + len(term)
    return False


def classify_task(prompt: str) -> str:
    text, _removed = _semantic_text(prompt)
    backend_objects = (
        "后端",
        "平台",
        "模拟器",
        "simulator",
        "qpu",
        "量子硬件",
        "真机",
        "backend",
        "platform",
        "spinq",
        "originq",
        "braket",
        "aws",
    )
    explicit_backend_actions = (
        "推荐",
        "选择",
        "选哪个",
        "选择哪个",
        "应该选",
        "应该用",
        "应该",
        "which backend",
        "which platform",
        "which qpu",
        "which simulator",
        "should i use",
        "use",
        "choose",
        "select",
        "recommend",
        "which",
        "what",
        "looking for",
        "find",
        "用哪个",
        "拿哪个",
        "跑哪个",
        "用",
    )
    repair_terms = ("修复", "纠错", "改正", "repair", "fix", "correct")
    generation_terms = ("生成", "创建", "制备", "generate", "create", "prepare")
    qasm_objects = (
        "qasm",
        "电路",
        "量子态",
        "bell",
        "ghz",
        "epr",
        "w state",
        "w 态",
        "w态",
        "猫态",
        "cat state",
        "纠缠",
        "superposition",
        "叠加",
    )
    backend_only_patterns = (
        r"不要.{0,24}(?:修复|生成).{0,24}(?:只要|只需).{0,12}(?:推荐|选择)",
        r"(?:do not|don't).{0,32}(?:repair|fix|generate).{0,32}(?:just|only).{0,16}(?:recommend|choose|select)",
    )
    qasm_only_patterns = (
        r"不要.{0,24}(?:推荐|选择).{0,24}(?:只要|只需).{0,12}(?:修复|生成)",
        r"(?:do not|don't).{0,32}(?:recommend|choose|select).{0,32}(?:just|only).{0,16}(?:repair|fix|generate)",
    )
    direct_generation_patterns = (
        r"\buse\b.{0,48}\b(?:to\s+)?(?:generate|create|prepare)\b.{0,48}\b(?:qasm|circuit|code)\b",
        r"用.{0,48}(?:生成|创建|制备).{0,48}(?:qasm|电路|代码)",
    )
    backend_request_patterns = (
        r"\b(?:i\s+)?(?:need|needs|want)\s+(?:a|an|the|one|some\s+)?(?:[\w-]+\s+){0,5}(?:backend|platform|simulator|qpu)\b",
        r"(?:需要|想要).{0,24}(?:后端|平台|模拟器|真机|量子硬件)",
    )
    if any(re.search(pattern, text) for pattern in backend_only_patterns):
        return "backend"
    if any(re.search(pattern, text) for pattern in qasm_only_patterns):
        return "repair" if _contains_any(text, repair_terms) else "generate"
    if any(re.search(pattern, text) for pattern in direct_generation_patterns):
        return "generate"
    has_backend_object = _contains_unnegated(text, backend_objects)
    has_backend_action = _contains_unnegated(text, explicit_backend_actions) or any(
        re.search(pattern, text) for pattern in backend_request_patterns
    )
    if has_backend_object and has_backend_action:
        return "backend"
    if _contains_unnegated(text, repair_terms):
        return "repair"
    if _contains_unnegated(text, generation_terms) and _contains_unnegated(
        text, qasm_objects
    ):
        return "generate"
    return "generate"


def _number_before_unit(text: str) -> int | None:
    unit = r"(?:(?:量子)?(?:比特|位)|qubits?|q[ -]?bits?|quantum\s+bits?)"
    match = re.search(rf"(\d+)\s*-?\s*(?:个\s*)?{unit}", text)
    if match:
        return int(match.group(1))
    match = re.search(rf"{unit}\s*[:=]?\s*(\d+)", text)
    if match:
        return int(match.group(1))
    for word, value in _ENGLISH_NUMBERS.items():
        if re.search(rf"\b{word}\s*-?\s*{unit}\b", text):
            return value
    for character, value in _CHINESE_NUMBERS.items():
        if re.search(rf"{character}\s*(?:个\s*)?(?:量子)?(?:比特|位)", text):
            return value
    return None


def extract_qubit_count(prompt: str) -> int | None:
    text, _removed = _semantic_text(prompt)
    return _number_before_unit(text)


def _goal_scope(text: str) -> str:
    markers = (
        r"so\s+(?:that\s+)?it\s+(?:prepares?|creates?|generates?)",
        r"to\s+(?:prepare|create|generate)",
        r"使(?:它|其)?(?:制备|生成|创建)",
        r"目标态\s*[:：]?",
    )
    matches = [match for pattern in markers for match in re.finditer(pattern, text)]
    if not matches:
        return text
    last = max(matches, key=lambda match: match.end())
    return text[last.end() :]


def _state_spec_from_text(text: str) -> dict[str, Any] | None:
    basis = re.search(r"\|\s*([01]+)\s*>|\bcomputational\s+basis\s+([01]+)\b", text)
    if basis:
        bits = basis.group(1) or basis.group(2)
        return {
            "family": "computational basis",
            "qubits": len(bits),
            "basis_bits": bits,
        }

    qubits = _number_before_unit(text)
    if _contains_any(
        text,
        (
            "均匀叠加",
            "等概率叠加",
            "等权叠加",
            "uniform superposition",
            "equal superposition",
            "equal-weight superposition",
            "equal weight superposition",
        ),
    ):
        return (
            {"family": "uniform superposition", "qubits": qubits}
            if qubits is not None
            else None
        )
    if (
        "w 态" in text
        or "w态" in text
        or re.search(r"\bw(?:[ -]?state)?\b", text)
        or "single-excitation state" in text
        or "single excitation state" in text
    ):
        return {"family": "W", "qubits": qubits or 3}
    if _contains_any(
        text,
        (
            "bell",
            "贝尔",
            "epr",
            "纠缠对",
            "entangled pair",
            "maximally entangled pair",
        ),
    ):
        return {"family": "Bell", "qubits": 2}
    maximally_entangled = _contains_any(text, ("最大纠缠", "maximally entangled"))
    if maximally_entangled and qubits == 2:
        return {"family": "Bell", "qubits": 2}
    if (
        "ghz" in text
        or "greenberger-horne-zeilinger" in text
        or "greenberger horne zeilinger" in text
        or "猫态" in text
        or "cat state" in text
        or "cat-state" in text
        or maximally_entangled
    ):
        return {"family": "GHZ", "qubits": qubits or 3}
    return None


def extract_state_spec(prompt: str) -> dict[str, Any] | None:
    text, _removed = _semantic_text(prompt)
    scoped = _goal_scope(text)
    return _state_spec_from_text(scoped) or _state_spec_from_text(text)


def extract_state_goal(prompt: str) -> tuple[str, int] | None:
    spec = extract_state_spec(prompt)
    if spec is None:
        return None
    return spec["family"], spec["qubits"]


def extract_backend_constraints(prompt: str) -> dict[str, Any]:
    text, _removed = _semantic_text(prompt)
    normalized = re.sub(r"[-_]+", " ", text)
    platforms: list[str] = []
    for platform, terms in (
        ("spinq", ("spinq", "量旋")),
        ("originq", ("originq", "本源")),
        ("braket", ("braket", "aws")),
    ):
        if _contains_unnegated(text, terms):
            platforms.append(platform)
    no_queue = _contains_any(
        normalized,
        (
            "零排队",
            "无排队",
            "不排队",
            "免排队",
            "无需排队",
            "没有排队",
            "zero queue",
            "no queue",
            "without queue",
            "without waiting",
            "no waiting",
            "no wait",
        ),
    )
    free = _contains_unnegated(
        text,
        (
            "免费",
            "零成本",
            "零费用",
            "无费用",
            "不收费",
            "free",
            "no cost",
            "without charge",
            "at no charge",
            "free of charge",
        ),
    )
    qpu = _contains_unnegated(text, ("真机", "量子硬件", "qpu"))
    simulator = _contains_unnegated(text, ("模拟器", "simulator"))
    no_account = _contains_any(
        text,
        (
            "无需账号",
            "无需账户",
            "无需注册",
            "无需登录",
            "免注册",
            "免登录",
            "no account",
            "without an account",
            "without account",
            "no login",
            "without login",
        ),
    )
    local_only = _contains_unnegated(
        text, ("本地", "离线", "local", "locally", "offline")
    )
    return {
        "minimum_qubits": _number_before_unit(text),
        "no_queue": no_queue,
        "free": free,
        "kinds": [kind for kind, present in (("qpu", qpu), ("simulator", simulator)) if present],
        "platforms": platforms,
        "requires_account": False if no_account else None,
        "local_only": local_only,
    }


def _semantic_payload(contract: dict[str, Any]) -> dict[str, Any]:
    return {
        "task_kind": contract["task_kind"],
        "state_goal": contract["state_goal"],
        "backend_constraints": contract["backend_constraints"],
    }


def build_prompt_contract(prompt: str) -> dict[str, Any]:
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("prompt must be a non-empty string")
    _text, removed_code_blocks = _semantic_text(prompt)
    state_goal = extract_state_spec(prompt)
    payload: dict[str, Any] = {
        "schema_version": PROMPT_CONTRACT_SCHEMA,
        "task_kind": classify_task(prompt),
        "state_goal": state_goal,
        "backend_constraints": extract_backend_constraints(prompt),
        "normalization": {"removed_code_blocks": removed_code_blocks},
    }
    semantic_sha256 = _sha256_text(_canonical_json(_semantic_payload(payload)))
    contract_sha256 = _sha256_text(_canonical_json(payload))
    payload["integrity"] = {
        "algorithm": "sha256",
        "request_sha256": _sha256_text(prompt),
        "semantic_sha256": semantic_sha256,
        "contract_sha256": contract_sha256,
        "is_signature": False,
        "note": "These digests detect content changes; they do not authenticate authorship.",
    }
    return payload


def verify_prompt_contract(contract: dict[str, Any], prompt: str) -> dict[str, Any]:
    if not isinstance(contract, dict):
        return {"valid": False, "reason": "contract must be a dictionary"}
    if contract.get("schema_version") != PROMPT_CONTRACT_SCHEMA:
        return {"valid": False, "reason": "schema_version mismatch"}
    integrity = contract.get("integrity")
    if not isinstance(integrity, dict):
        return {"valid": False, "reason": "missing integrity block"}
    payload = {key: value for key, value in contract.items() if key != "integrity"}
    observed_sha = integrity.get("contract_sha256")
    computed_sha = _sha256_text(_canonical_json(payload))
    if observed_sha != computed_sha:
        return {
            "valid": False,
            "reason": "contract checksum mismatch",
            "expected_contract_sha256": computed_sha,
            "observed_contract_sha256": observed_sha,
        }
    try:
        rebuilt = build_prompt_contract(prompt)
    except (TypeError, ValueError) as exc:
        return {"valid": False, "reason": f"rebuild failed: {exc}"}
    if rebuilt != contract:
        return {
            "valid": False,
            "reason": "recomputed contract mismatch",
            "expected_contract_sha256": rebuilt["integrity"]["contract_sha256"],
            "observed_contract_sha256": observed_sha,
        }
    return {"valid": True, "contract_sha256": observed_sha}
