"""Beginner-facing quantum guide and the coin-world game mechanic.

The guide is deliberately independent of the LLM path.  A player can learn
the concepts, measure the local exact simulator, and then open the real
hardware evidence bridge without credentials in the browser.
"""

from __future__ import annotations

import secrets
from typing import Any

from .qasm import parse_qasm
from .simulator import probabilities


COIN_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];
"""

WORLD_FACES = {
    "village": {
        "label": "量子村庄",
        "asset": "/assets/quantum-guide/village-face.png",
        "measurement": 0,
        "copy": "测得 0：回到熟悉的村庄。",
    },
    "cosmos": {
        "label": "宇宙太空",
        "asset": "/assets/quantum-guide/cosmos-face.png",
        "measurement": 1,
        "copy": "测得 1：进入另一面宇宙。",
    },
}

GUIDE_LESSONS = [
    {
        "id": "bit-and-measurement",
        "title": "一枚硬币：测量会让可能变成结果",
        "concept": "普通比特像一枚已经落地的硬币；测量会把量子可能性读成一个明确结果。",
        "action": "先认识两张世界贴图，再按下测量按钮。",
    },
    {
        "id": "superposition",
        "title": "旋转的硬币：两面都在可能之中",
        "concept": "H 门把一个量子比特放进叠加态；测量前，村庄和宇宙都保留在可能性里。",
        "action": "观察概率条，再决定何时让硬币落定。",
    },
    {
        "id": "entanglement",
        "title": "两枚硬币：结果可以形成相关结构",
        "concept": "CX 门把两个量子比特的结果联系起来；这是一种可由电路和测量分布观察的相关性。",
        "action": "把第二枚硬币带入同一场景，比较两个结果。",
    },
    {
        "id": "bell-inequality",
        "title": "Bell 不等式：怎样区分预先写好的答案？",
        "concept": "Bell 的问题是：如果结果只由局部、预先写好的隐藏答案决定，多组测量相关性会满足一条上界；量子实验用不同测量设置和统计数据检验这个上界。",
        "action": "游戏先建立‘相关性’直觉，再进入多设置 Bell 实验。",
        "boundary": "单次 Z 基测量展示相关性；完整 Bell 检验需要多种测量设置和统计数据。",
    },
]


def _coin_probabilities() -> dict[str, float]:
    return {key: round(value, 12) for key, value in probabilities(parse_qasm(COIN_QASM)).items()}


def build_quantum_intro() -> dict[str, Any]:
    """Return the complete RPG prelude and the evidence bridge metadata."""

    return {
        "schema_version": "loomq-quantum-intro-v1",
        "title": "量子村庄 · 从一枚硬币开始",
        "subtitle": "游戏手册也是一份真实的量子力学入门",
        "lessons": GUIDE_LESSONS,
        "mechanic": {
            "name": "quantum-coin-world",
            "qasm": COIN_QASM,
            "probabilities": _coin_probabilities(),
            "outcome_faces": ["village", "cosmos"],
            "measurement_rule": "outcome 0 → village；outcome 1 → cosmos",
            "source": "local-exact-simulator",
        },
        "hardware_bridge": {
            "label": "进入真机实验室",
            "description": "浏览真实平台任务的 QASM、job ID、原始返回和统计复核。",
            "evidence_path": "/evidence/README.md",
            "records": [
                {
                    "provider": "OriginQ Wukong 180",
                    "job_id": "9D182FA1EF76FF3807697CDF69DE7483",
                    "result_path": "/evidence/files/originq-result.json",
                },
                {
                    "provider": "SpinQ Cloud",
                    "job_id": "G-260824-0001",
                    "result_path": "/evidence/files/spinq-result.json",
                },
            ],
        },
    }


def measure_quantum_coin(outcome: int | None = None) -> dict[str, Any]:
    """Measure the H-prepared coin and map the observed bit to a world face."""

    if outcome is None:
        outcome = secrets.randbelow(2)
    if isinstance(outcome, bool) or outcome not in (0, 1):
        raise ValueError("outcome must be 0 or 1")
    face = "village" if outcome == 0 else "cosmos"
    result = WORLD_FACES[face]
    return {
        "schema_version": "loomq-quantum-coin-measurement-v1",
        "outcome": outcome,
        "face": face,
        "face_label": result["label"],
        "asset": result["asset"],
        "copy": result["copy"],
        "qasm": COIN_QASM,
        "probabilities": _coin_probabilities(),
        "source": "local-exact-simulator",
        "hardware_bridge": "/api/quantum-intro",
    }
