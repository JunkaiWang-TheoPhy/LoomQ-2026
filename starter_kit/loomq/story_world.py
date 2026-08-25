"""Evidence-native story world for the Quantum Atlas.

The story layer is deliberately data-first.  A case can provide atmosphere and
human stakes, but it must also declare the local experiment that a browser or
CLI can replay.  Narrative claims never masquerade as physical conclusions.
"""

from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from typing import Any, Iterable, Mapping


SCHEMA_VERSION = "loomq-story-world-v1"
MAINLINE_ID = "observer-zero"
ARCHIVE_ID = "evidence-archive"
# The emotional entry point comes first; the cases then widen from one life to
# labour, climate, infrastructure and finally the politics of evidence.
CASE_IDS = ("eightieth-year", "second-badge", "inside-tide-line", "night-grid", "testimony-checker")


def _canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def _digest(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _qasm(*lines: str) -> str:
    return "\n".join(("OPENQASM 2.0;", 'include "qelib1.inc";', *lines, ""))


def _mainline() -> dict[str, Any]:
    return {
        "id": MAINLINE_ID,
        "kind": "mainline",
        "title": "零点之后的观测者",
        "region": "零点观测站",
        "question": "如果系统先替你预测，你还在做决定吗？",
        "logline": "先留下预测，只改变一扇门，再用可重放证据审计自己的判断。",
        "beats": [
            {"id": "predict", "label": "先猜", "action": "记录一个可被实验推翻的预测"},
            {"id": "perturb", "label": "只改一扇门", "action": "运行控制组与反事实组"},
            {"id": "observe", "label": "看分歧", "action": "比较实际 counts 与首个分歧门"},
            {"id": "audit", "label": "再下结论", "action": "下载带边界的实验护照"},
        ],
        "unlocks": list(CASE_IDS),
        "evidence_contract": {
            "mode": "local-counterfactual",
            "endpoint": "/api/inquiry",
            "mission": "bell-gates",
            "changed_variable": {"action": "disable", "witness_id": "g2", "operation": "cx q[0],q[1]"},
            "required_outputs": ["prediction_review", "comparison", "conclusion_audits", "replay"],
        },
        "claim_boundary": "主线是社会隐喻；本地量子实验只验证电路差异，不预测真实社会或人的行为。",
    }


def _cases() -> list[dict[str, Any]]:
    cases = [
        {
            "id": "eightieth-year",
            "kind": "case",
            "title": "她的第八十年",
            "region": "长日照护院",
            "theme": "老龄化与数字人格",
            "question": "一个人的数字记忆比本人更容易被照护时，照护的是谁？",
            "identities": {
                "public": "八十岁的沈遥，正在重新决定自己的生活。",
                "hidden": "二十年前留下的青年副本，替她预约、签字并解释她。",
            },
            "artifact": "记忆双签记录",
            "evidence_contract": {
                "mode": "local-counterfactual",
                "reference_qasm": _qasm("qreg q[1];", "creg c[1];", "h q[0];", "h q[0];", "measure q[0] -> c[0];"),
                "variant_qasm": _qasm("qreg q[1];", "creg c[1];", "h q[0];", "x q[0];", "h q[0];", "measure q[0] -> c[0];"),
                "changed_variable": {"action": "insert", "witness_id": "g2", "operation": "x q[0]"},
                "observable": "记忆版本之间的可重放输出差异",
            },
            "claim_boundary": "模拟结果不能判定人格连续性，也不能替代本人同意；它只让‘加入一个变量后结果改变’成为可见的实验结构。",
        },
        {
            "id": "second-badge",
            "kind": "case",
            "title": "第二个工牌",
            "region": "工牌广场",
            "theme": "AI 与双面人生",
            "question": "一个人的数字副本比本人更像‘好员工’时，谁拥有他的职业身份？",
            "identities": {
                "public": "白天的人类复核员，替算法给医疗建议签字。",
                "hidden": "夜里的零号复核员，替被系统降权的人修改职业记录。",
            },
            "artifact": "双重签名工牌",
            "evidence_contract": {
                "mode": "local-counterfactual",
                "reference_qasm": _qasm("qreg q[1];", "creg c[1];", "h q[0];", "measure q[0] -> c[0];"),
                "variant_qasm": _qasm("qreg q[1];", "creg c[1];", "x q[0];", "measure q[0] -> c[0];"),
                "changed_variable": {"action": "replace", "witness_id": "g1", "operation": "h → x"},
                "observable": "计算基 counts",
            },
            "claim_boundary": "实验只显示两段电路的输出差异，不能证明哪一种职业判断更公平。公平性需要制度、数据和当事人的额外证据。",
        },
        {
            "id": "inside-tide-line",
            "kind": "case",
            "title": "潮线以内",
            "region": "潮线城市",
            "theme": "气候迁移与时代灾难",
            "question": "当地图预测谁会离开，而政策又让他不得不离开，预测还是预测吗？",
            "identities": {
                "public": "白天的气候迁移规划师，绘制城市安全线。",
                "hidden": "夜里的匿名路线发送者，帮助红线以内的居民撤离。",
            },
            "artifact": "两层迁移地图",
            "evidence_contract": {
                "mode": "local-counterfactual",
                "reference_qasm": _qasm("qreg q[2];", "creg c[2];", "h q[0];", "cx q[0],q[1];", "measure q -> c;"),
                "variant_qasm": _qasm("qreg q[2];", "creg c[2];", "h q[0];", "measure q[0] -> c[0];", "measure q[1] -> c[1];"),
                "changed_variable": {"action": "disable", "witness_id": "g2", "operation": "cx q[0],q[1]"},
                "observable": "联合测量 counts 与首个分歧门",
            },
            "claim_boundary": "电路对照不能预测真实迁移，也不能替代气候模型、社区知识或政策协商；它只示范‘改变一个条件会改变哪些观测’。",
        },
        {
            "id": "night-grid",
            "kind": "case",
            "title": "电网的夜班",
            "region": "夜间电网",
            "theme": "AI 算力与公共资源",
            "question": "当数据中心和医院争夺同一度电，谁能把‘最优’说成唯一答案？",
            "identities": {
                "public": "白天的电网算法调度员，保障算力中心稳定运行。",
                "hidden": "夜里的小镇值班长，替呼吸机和水泵争取电力。",
            },
            "artifact": "负载优先级日志",
            "evidence_contract": {
                "mode": "local-interference-check",
                "reference_qasm": _qasm("qreg q[1];", "creg c[1];", "h q[0];", "s q[0];", "h q[0];", "measure q[0] -> c[0];"),
                "variant_qasm": _qasm("qreg q[1];", "creg c[1];", "h q[0];", "h q[0];", "measure q[0] -> c[0];"),
                "changed_variable": {"action": "remove", "witness_id": "g2", "operation": "s q[0]"},
                "observable": "干涉后的确定性输出与对照输出",
            },
            "claim_boundary": "电路的干涉结果不是能源调度建议；故事把‘优先级改变结果’作为隐喻，真实资源决策仍需成本、风险和公共程序。",
        },
        {
            "id": "testimony-checker",
            "kind": "case",
            "title": "证词校验器",
            "region": "无证词档案馆",
            "theme": "证据政治与不可验证者",
            "question": "一段影像无法被机器验证时，它是假的，还是系统不知道如何听见它？",
            "identities": {
                "public": "白天的全球证词校验器首席工程师。",
                "hidden": "夜里的匿名档案保管人，保存没有认证设备拍下的证词。",
            },
            "artifact": "证据关系图",
            "evidence_contract": {
                "mode": "local-observation-boundary",
                "reference_qasm": _qasm("qreg q[1];", "creg c[1];", "h q[0];", "measure q[0] -> c[0];"),
                "variant_qasm": _qasm("qreg q[1];", "creg c[1];", "x q[0];", "measure q[0] -> c[0];"),
                "changed_variable": {"action": "replace", "witness_id": "g1", "operation": "h → x"},
                "observable": "可观察结果、缺失证据和结论边界",
            },
            "claim_boundary": "本地实验只能说明观测协议如何区分两个电路，不能替代事实调查；‘不可验证’必须与‘虚假’分开。",
        },
    ]
    for case in cases:
        case["prerequisites"] = [MAINLINE_ID]
    return cases


def _validate_completion(completed_node_ids: Iterable[str]) -> tuple[str, ...]:
    values = list(completed_node_ids)
    allowed = {MAINLINE_ID, ARCHIVE_ID, *CASE_IDS}
    if any(not isinstance(value, str) for value in values):
        raise ValueError("completed story node ids must be strings")
    unknown = sorted(set(values) - allowed)
    if unknown:
        raise ValueError(f"unknown story node: {unknown[0]}")
    completed = set(values)
    if any(case_id in completed for case_id in CASE_IDS) and MAINLINE_ID not in completed:
        raise ValueError("mainline must be completed before cases")
    if ARCHIVE_ID in completed and not set(CASE_IDS).issubset(completed):
        raise ValueError("archive requires all five cases")
    return tuple(sorted(completed))


def story_progress(completed_node_ids: Iterable[str]) -> dict[str, Any]:
    completed = set(_validate_completion(completed_node_ids))
    mainline_status = "complete" if MAINLINE_ID in completed else "current"
    cases = {
        case_id: (
            "complete"
            if case_id in completed
            else "current"
            if MAINLINE_ID in completed
            else "locked"
        )
        for case_id in CASE_IDS
    }
    archive = (
        "complete"
        if ARCHIVE_ID in completed
        else "current"
        if set(CASE_IDS).issubset(completed)
        else "locked"
    )
    return {"mainline": mainline_status, "cases": cases, "archive": archive}


def build_story_world(completed_node_ids: Iterable[str] = ()) -> dict[str, Any]:
    completed = list(_validate_completion(completed_node_ids))
    body: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "world_id": "quantum-atlas",
        "title": "Quantum Atlas · 无形世界调查局",
        "mainline": _mainline(),
        "cases": _cases(),
        "archive": {
            "id": ARCHIVE_ID,
            "kind": "archive",
            "title": "零点之后的档案塔",
            "question": "哪些结论经得起重放，哪些只是我们希望相信的故事？",
            "requires": list(CASE_IDS),
        },
        "completed_node_ids": completed,
        "progress": story_progress(completed),
    }
    body["integrity"] = {"body_sha256": _digest(body)}
    return body


def verify_story_world(payload: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(payload, Mapping):
        return {"valid": False, "reason": "invalid schema: world must be a mapping"}
    integrity = payload.get("integrity")
    supplied_body = {key: value for key, value in payload.items() if key != "integrity"}
    supplied_digest = _digest(supplied_body)
    if not isinstance(integrity, Mapping) or integrity.get("body_sha256") != supplied_digest:
        return {"valid": False, "reason": "story integrity does not match body"}
    try:
        recomputed = build_story_world(payload.get("completed_node_ids", []))
    except (TypeError, ValueError) as exc:
        return {"valid": False, "reason": f"invalid schema: {exc}"}
    recomputed_body = {key: value for key, value in recomputed.items() if key != "integrity"}
    if supplied_body != recomputed_body:
        return {"valid": False, "reason": "story body does not match deterministic world"}
    return {
        "valid": True,
        "reason": "ok",
        "body_sha256": supplied_digest,
    }


__all__ = [
    "ARCHIVE_ID",
    "CASE_IDS",
    "MAINLINE_ID",
    "SCHEMA_VERSION",
    "build_story_world",
    "story_progress",
    "verify_story_world",
]
