"""A complete, replayable vertical slice for the first Atlas case.

This module owns the quest lifecycle.  The browser may render it as dialogue,
cards, or a map scene, but it cannot skip a chapter or silently turn a choice
into a correct answer.
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping


SCHEMA_VERSION = "loomq-eighty-year-quest-v1"
CASE_ID = "eightieth-year"
CHAPTER_IDS = (
    "arrival",
    "memory-room",
    "divergence-probe",
    "copy-request",
    "family-hearing",
    "signature",
    "return-visit",
)
CLUE_IDS = ("paper-diary", "copy-summary", "daughter-letter")
CHOICE_IDS = ("autonomy-first", "dual-signature", "defer")


def _base_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "quest_id": CASE_ID,
        "chapter": "arrival",
        "status": "active",
        "clues": [],
        "evidence": [],
        "probe": None,
        "decisions": {},
        "ending": None,
        "unlocks": [],
        "consequences": [],
        "relationships": {"shen-yao": 0, "young-copy": 0, "daughter": 0},
        "return_visits": 0,
    }


def create_state() -> dict[str, Any]:
    return _base_state()


def current_scene(state: Mapping[str, Any]) -> dict[str, Any]:
    _validate_state(state)
    scenes = {
        "arrival": {
            "chapter": "arrival",
            "title": "长日照护院",
            "text": "沈遥和她的青年副本正在争论：谁有资格解释她现在的生活？先听两个人说完，再决定要查什么。",
            "actions": ["meet-shen-yao"],
        },
        "memory-room": {
            "chapter": "memory-room",
            "title": "三份记忆",
            "text": "纸质日记、青年副本摘要和女儿的信互相矛盾。没有哪一份材料自动拥有最终解释权。",
            "actions": [f"collect-{clue}" for clue in CLUE_IDS if clue not in state["clues"]],
        },
        "divergence-probe": {
            "chapter": "divergence-probe",
            "title": "记忆分歧实验",
            "text": "只改变一个条件，比较两条记忆线路在哪里第一次分开。实验不判定人格，只记录可复核的差异。",
            "actions": ["run-memory-probe"],
        },
        "copy-request": {
            "chapter": "copy-request",
            "title": "副本的请求",
            "text": "青年副本请求删除一段记忆。它说自己是在保护沈遥，也承认自己可能只是被设计成讨人喜欢。",
            "actions": ["hear-copy-request"],
        },
        "family-hearing": {
            "chapter": "family-hearing",
            "title": "家属听证",
            "text": "女儿需要副本继续照护，沈遥却不愿再被年轻时的自己代表。玩家必须让双方都留下可追溯的请求。",
            "actions": ["hold-family-hearing"],
        },
        "signature": {
            "chapter": "signature",
            "title": "签名之前",
            "text": "现在没有标准答案。你要决定的是：谁能签字、谁必须被听见，以及哪些不确定性要继续保留。",
            "actions": [f"choose-{choice}" for choice in CHOICE_IDS],
        },
        "return-visit": {
            "chapter": "return-visit",
            "title": "第二天回访",
            "text": "结案不是离场。回到照护院，看看你的决定如何改变两个人的说话方式，再把证据带回地图。",
            "actions": ["return-to-care-home"],
        },
    }
    return deepcopy(scenes[state["chapter"]])


def available_actions(state: Mapping[str, Any]) -> list[str]:
    return current_scene(state)["actions"]


def _require_action(state: Mapping[str, Any], action: str) -> None:
    if action.startswith("collect-") and state.get("chapter") != "memory-room":
        raise ValueError("cannot collect memory clue outside memory-room")
    if action not in available_actions(state):
        raise ValueError(f"action unavailable in {state['chapter']}: {action}")


def _copy_and_update(state: Mapping[str, Any]) -> dict[str, Any]:
    updated = deepcopy(dict(state))
    _validate_state(updated)
    return updated


def transition(state: Mapping[str, Any], action: str, payload: Mapping[str, Any] | None = None) -> dict[str, Any]:
    updated = _copy_and_update(state)
    if action.startswith("choose-") and action.removeprefix("choose-") not in CHOICE_IDS:
        raise ValueError(f"unknown choice: {action.removeprefix('choose-')}")
    _require_action(updated, action)
    payload = {} if payload is None else dict(payload)

    if action == "meet-shen-yao":
        updated["chapter"] = "memory-room"
        updated["relationships"]["shen-yao"] += 1
    elif action.startswith("collect-"):
        clue = action.removeprefix("collect-")
        if updated["chapter"] != "memory-room":
            raise ValueError("cannot collect memory clue outside memory-room")
        updated["clues"].append(clue)
        if len(updated["clues"]) == len(CLUE_IDS):
            updated["chapter"] = "divergence-probe"
    elif action == "run-memory-probe":
        if not payload.get("first_divergent_gate") and payload.get("first_divergent_gate") != 0:
            raise ValueError("probe requires evidence: first_divergent_gate")
        updated["probe"] = {
            "first_divergent_gate": payload["first_divergent_gate"],
            "scope": "local-circuit-comparison",
        }
        updated["evidence"].append("memory-divergence")
        updated["chapter"] = "copy-request"
    elif action == "hear-copy-request":
        updated["relationships"]["young-copy"] += 1
        updated["chapter"] = "family-hearing"
    elif action == "hold-family-hearing":
        updated["relationships"]["daughter"] += 1
        updated["decisions"]["family-hearing"] = True
        updated["chapter"] = "signature"
    elif action.startswith("choose-"):
        choice = action.removeprefix("choose-")
        updated["ending"] = choice
        updated["decisions"]["signature"] = choice
        updated["chapter"] = "return-visit"
        if choice == "autonomy-first":
            updated["relationships"]["shen-yao"] += 2
            updated["relationships"]["young-copy"] -= 1
            updated["consequences"].extend(["copy-autonomy-revoked", "shen-yao-signs-alone"])
        elif choice == "dual-signature":
            updated["relationships"]["shen-yao"] += 1
            updated["relationships"]["young-copy"] += 1
            updated["consequences"].extend(["joint-consent-required", "care-function-retained"])
        else:
            updated["consequences"].extend(["observation-period-opened", "family-must-return"])
    elif action == "return-to-care-home":
        updated["return_visits"] += 1
        updated["status"] = "complete"
        if "memory-dual-signature" not in updated["evidence"]:
            updated["evidence"].append("memory-dual-signature")
        updated["unlocks"].append("second-badge")

    _validate_state(updated)
    return updated


def _validate_state(state: Mapping[str, Any]) -> None:
    if state.get("schema_version") != SCHEMA_VERSION or state.get("quest_id") != CASE_ID:
        raise ValueError("state invariant: wrong quest schema")
    if state.get("chapter") not in CHAPTER_IDS:
        raise ValueError("state invariant: unknown chapter")
    if state.get("status") not in {"active", "complete"}:
        raise ValueError("state invariant: unknown status")
    clues = state.get("clues")
    if not isinstance(clues, list) or len(set(clues)) != len(clues) or not set(clues).issubset(CLUE_IDS):
        raise ValueError("state invariant: invalid clues")
    if CHAPTER_IDS.index(state["chapter"]) > CHAPTER_IDS.index("memory-room") and not clues:
        raise ValueError("state invariant: chapter requires an initial meeting")
    if CHAPTER_IDS.index(state["chapter"]) >= CHAPTER_IDS.index("divergence-probe") and len(clues) != len(CLUE_IDS):
        raise ValueError("state invariant: probe chapter requires all clues")
    if state["chapter"] in {"copy-request", "family-hearing", "signature", "return-visit"} and not state.get("probe"):
        raise ValueError("state invariant: hearing requires probe evidence")
    if state["chapter"] in {"signature", "return-visit"} and not state.get("decisions", {}).get("family-hearing", True):
        raise ValueError("state invariant: signature requires a hearing")
    if state.get("status") == "complete":
        if state.get("chapter") != "return-visit" or not state.get("ending") or not state.get("return_visits"):
            raise ValueError("state invariant: complete quest requires return visit")
        if "second-badge" not in state.get("unlocks", []):
            raise ValueError("state invariant: complete quest must unlock next case")


def restore_state(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError("state invariant: state must be an object")
    restored = deepcopy(dict(value))
    _validate_state(restored)
    return restored


__all__ = [
    "CASE_ID",
    "CHAPTER_IDS",
    "CHOICE_IDS",
    "available_actions",
    "create_state",
    "current_scene",
    "restore_state",
    "transition",
]
