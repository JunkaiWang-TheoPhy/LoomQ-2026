"""Zero-dependency local web lab backed by the public LoomQ adapter contract."""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import parse_qs, urlparse

try:
    from .. import adapter
    from .agent import normalize_history
    from .assertions import diagnose_mutation, diagnose_observed_execution, evaluate_assertions
    from .prompt_contract import build_prompt_contract, verify_prompt_contract
    from .simulator import trace_statevector
    from .qasm import parse_qasm
    from .witness import build_causal_audit, verify_causal_audit
    from .story_world import build_story_world
    from .quantum_intro import build_quantum_intro, measure_quantum_coin
except ImportError:  # Direct execution from starter_kit/.
    import adapter
    from loomq.agent import normalize_history
    from loomq.assertions import diagnose_mutation, diagnose_observed_execution, evaluate_assertions
    from loomq.prompt_contract import build_prompt_contract, verify_prompt_contract
    from loomq.simulator import trace_statevector
    from loomq.qasm import parse_qasm
    from loomq.witness import build_causal_audit, verify_causal_audit
    from loomq.story_world import build_story_world
    from loomq.quantum_intro import build_quantum_intro, measure_quantum_coin


_WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/favicon.ico": ("favicon.svg", "image/svg+xml"),
    "/favicon.svg": ("favicon.svg", "image/svg+xml"),
    "/assets/shenicest-logo.png": ("assets/shenicest-logo.png", "image/png"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/inquiry.js": ("inquiry.js", "text/javascript; charset=utf-8"),
    "/quantum-guide.js": ("quantum-guide.js", "text/javascript; charset=utf-8"),
    "/assets/quantum-world-journey.png": (
        "assets/quantum-world-journey.png",
        "image/png",
    ),
    "/assets/story/zero-point-station.png": (
        "assets/story/zero-point-station.png",
        "image/png",
    ),
    "/assets/story/eighty-years-window.png": (
        "assets/story/eighty-years-window.png",
        "image/png",
    ),
    "/assets/story/second-badge.png": (
        "assets/story/second-badge.png",
        "image/png",
    ),
    "/assets/story/inside-tide-line.png": (
        "assets/story/inside-tide-line.png",
        "image/png",
    ),
    "/assets/story/night-grid.png": (
        "assets/story/night-grid.png",
        "image/png",
    ),
    "/assets/story/evidence-tower.png": (
        "assets/story/evidence-tower.png",
        "image/png",
    ),
    "/assets/story/double-life-village-earth-2d.png": (
        "assets/story/double-life-village-earth-2d.png",
        "image/png",
    ),
    "/assets/story/double-life-village-cosmos-2d.png": (
        "assets/story/double-life-village-cosmos-2d.png",
        "image/png",
    ),
    "/assets/quantum-guide/village-face.png": (
        "assets/quantum-guide/village-face.png",
        "image/png",
    ),
    "/assets/quantum-guide/cosmos-face.png": (
        "assets/quantum-guide/cosmos-face.png",
        "image/png",
    ),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/enhancements.css": ("enhancements.css", "text/css; charset=utf-8"),
    "/case.html": ("case.html", "text/html; charset=utf-8"),
    "/case.js": ("case.js", "text/javascript; charset=utf-8"),
    "/case.css": ("case.css", "text/css; charset=utf-8"),
}

# Story artwork is local-only and explicitly allow-listed so the narrative
# page can load the same assets in the browser and in the file-mode preview.
for _story_asset in (
    "zero-point-station.png",
    "eighty-years-window.png",
    "second-badge.png",
    "inside-tide-line.png",
    "night-grid.png",
    "evidence-tower.png",
    "double-life-village-earth-2d.png",
    "double-life-village-cosmos-2d.png",
):
    _STATIC[f"/assets/story/{_story_asset}"] = (f"assets/story/{_story_asset}", "image/png")

_BELL_INQUIRY_CONTROL = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""

_BELL_INQUIRY_VARIANT = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
measure q -> c;
"""


class LoomQWebHandler(BaseHTTPRequestHandler):
    server_version = "LoomQWeb/1.0"

    def log_message(self, format: str, *args: object) -> None:
        print("[loomq-web] " + format % args)

    def _send_bytes(self, status: int, content_type: str, body: bytes) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'")
        self.end_headers()
        self.wfile.write(body)

    def _send_json(self, status: int, payload: Dict[str, Any]) -> None:
        self._send_bytes(
            status,
            "application/json; charset=utf-8",
            json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        )

    def _error(self, status: int, code: str, message: str) -> None:
        self._send_json(status, {"error": {"code": code, "message": message}})

    def _payload(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise ValueError("Content-Length 必须是整数") from exc
        if length <= 0 or length > 1_000_000:
            raise ValueError("请求正文必须为 1–1000000 字节的 JSON")
        try:
            payload = json.loads(self.rfile.read(length))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError("请求正文不是合法 JSON") from exc
        if not isinstance(payload, dict):
            raise ValueError("JSON 顶层必须是对象")
        return payload

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "loomq-web"})
            return
        if path == "/api/story-world":
            raw_completed = parse_qs(parsed.query).get("completed", [""])[0]
            completed = [item for item in raw_completed.split(",") if item]
            try:
                self._send_json(HTTPStatus.OK, build_story_world(completed))
            except (TypeError, ValueError) as exc:
                self._error(HTTPStatus.BAD_REQUEST, "invalid_story_progress", str(exc))
            return
        if path == "/api/quantum-intro":
            self._send_json(HTTPStatus.OK, build_quantum_intro())
            return
        asset = _STATIC.get(path)
        if asset is None:
            self._error(HTTPStatus.NOT_FOUND, "not_found", "页面不存在")
            return
        filename, content_type = asset
        try:
            body = (_WEB_ROOT / filename).read_bytes()
        except OSError:
            self._error(HTTPStatus.INTERNAL_SERVER_ERROR, "asset_missing", "Web 资源不完整")
            return
        self._send_bytes(HTTPStatus.OK, content_type, body)

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        try:
            payload = self._payload()
            if path == "/api/run":
                self._run(payload)
                return
            if path == "/api/assert":
                self._assert(payload)
                return
            if path == "/api/compare":
                self._compare(payload)
                return
            if path == "/api/causal-audit":
                self._causal_audit(payload)
                return
            if path == "/api/hybrid-trace":
                self._hybrid_trace(payload)
                return
            if path == "/api/hybrid-paths":
                self._hybrid_paths(payload)
                return
            if path == "/api/hybrid-path-certificate":
                self._hybrid_paths(payload)
                return
            if path == "/api/prompt-contract":
                self._prompt_contract(payload)
                return
            if path == "/api/inquiry":
                self._inquiry(payload)
                return
            if path == "/api/quantum-intro/measure":
                self._quantum_intro_measure(payload)
                return
            if path == "/api/agent":
                self._agent(payload)
                return
            self._error(HTTPStatus.NOT_FOUND, "not_found", "API 路径不存在")
        except (TypeError, ValueError) as exc:
            self._error(HTTPStatus.BAD_REQUEST, "invalid_request", str(exc))
        except Exception as exc:  # Deliberately hide internals and environment values.
            self._error(
                HTTPStatus.INTERNAL_SERVER_ERROR,
                "internal_error",
                f"请求执行失败：{type(exc).__name__}",
            )

    def do_DELETE(self) -> None:
        self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", "该路径不支持 DELETE")

    def do_PUT(self) -> None:
        self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", "该路径不支持 PUT")

    def do_PATCH(self) -> None:
        self._error(HTTPStatus.METHOD_NOT_ALLOWED, "method_not_allowed", "该路径不支持 PATCH")

    def _quantum_intro_measure(self, payload: Dict[str, Any]) -> None:
        outcome = payload.get("outcome")
        if outcome is not None and isinstance(outcome, bool):
            raise ValueError("outcome 必须是 0 或 1")
        self._send_json(HTTPStatus.OK, measure_quantum_coin(outcome))

    def _run(self, payload: Dict[str, Any]) -> None:
        qasm = payload.get("qasm")
        target = payload.get("target", "spinq")
        shots = payload.get("shots", 1024)
        if not isinstance(qasm, str) or not qasm.strip():
            raise ValueError("qasm 必须是非空字符串")
        if target not in adapter.SUPPORTED_TARGETS:
            raise ValueError("target 必须是 spinq、originq 或 braket")
        if not isinstance(shots, int) or isinstance(shots, bool) or shots <= 0 or shots > 100_000:
            raise ValueError("shots 必须是 1–100000 的整数")
        result = adapter.run(qasm, target, shots)
        proof = None
        proof_status = "available"
        proof_notice = ""
        try:
            native_ir, proof = adapter.transpile_with_proof(qasm, target)
        except ValueError as exc:
            if "supports at most 8 qubits" not in str(exc):
                raise
            native_ir = adapter.transpile(qasm, target)
            proof_status = "out_of_scope"
            proof_notice = (
                "no whole-circuit certificate beyond 8 qubits; "
                "kept run result and requested-target structural compilation only"
            )
        probabilities = {
            state: count / result["shots"] for state, count in result["counts"].items()
        }
        trace_notice = ""
        try:
            trace = trace_statevector(parse_qasm(qasm))
        except ValueError as exc:
            trace = []
            trace_notice = str(exc)
        self._send_json(
            HTTPStatus.OK,
            {
                "result": result,
                "probabilities": probabilities,
                "native_ir": native_ir,
                "proof": proof,
                "proof_status": proof_status,
                "proof_notice": proof_notice,
                "trace": trace,
                "trace_notice": trace_notice,
            },
        )

    def _assert(self, payload: Dict[str, Any]) -> None:
        qasm = payload.get("qasm")
        assertions = payload.get("assertions")
        observed = payload.get("observed")
        shots = payload.get("shots")
        if not isinstance(qasm, str) or not qasm.strip():
            raise ValueError("qasm 必须是非空字符串")
        if not isinstance(assertions, list) or not assertions:
            raise ValueError("assertions 必须是非空列表")
        circuit = parse_qasm(qasm)
        if observed is None:
            if shots is not None:
                raise ValueError("shots 只能和 observed 一起提供")
            report = evaluate_assertions(circuit, assertions)
            self._send_json(
                HTTPStatus.OK,
                {
                    "mode": "exact-local",
                    "assertions": report,
                    "attribution_caveat": "本地精确断言不归因具体噪声机制。",
                },
            )
            return
        if not isinstance(observed, dict) or not observed:
            raise ValueError("observed 必须是非空对象")
        if shots is not None and (
            not isinstance(shots, int) or isinstance(shots, bool) or shots <= 0 or shots > 100_000
        ):
            raise ValueError("shots 必须是 1–100000 的整数")
        diagnosis = diagnose_observed_execution(
            circuit,
            observed,
            assertions,
            shots=shots,
        )
        self._send_json(
            HTTPStatus.OK,
            {
                "mode": "observed-execution",
                "diagnosis": diagnosis,
            },
        )

    def _hybrid_trace(self, payload: Dict[str, Any]) -> None:
        source = payload.get("source")
        measurement_bits = payload.get("measurement_bits")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source 必须是非空字符串")
        if measurement_bits is None:
            raise ValueError("measurement_bits 必须提供")
        self._send_json(HTTPStatus.OK, adapter.trace_hybrid(source, measurement_bits))

    def _hybrid_paths(self, payload: Dict[str, Any]) -> None:
        source = payload.get("source")
        if not isinstance(source, str) or not source.strip():
            raise ValueError("source 必须是非空字符串")
        max_outcomes = payload.get("max_outcomes", 256)
        if isinstance(max_outcomes, bool) or not isinstance(max_outcomes, int):
            raise ValueError("max_outcomes 必须是 1–256 的整数")
        if max_outcomes <= 0 or max_outcomes > 256:
            raise ValueError("max_outcomes 必须是 1–256 的整数")
        certificate = adapter.certify_hybrid_paths(source, max_outcomes=max_outcomes)
        verification = adapter.verify_hybrid_path_certificate(source, certificate)
        self._send_json(
            HTTPStatus.OK,
            {
                "certificate": certificate,
                "verification": verification,
            },
        )

    def _compare(self, payload: Dict[str, Any]) -> None:
        reference_qasm = payload.get("reference_qasm")
        candidate_qasm = payload.get("candidate_qasm")
        if not isinstance(reference_qasm, str) or not reference_qasm.strip():
            raise ValueError("reference_qasm 必须是非空字符串")
        if not isinstance(candidate_qasm, str) or not candidate_qasm.strip():
            raise ValueError("candidate_qasm 必须是非空字符串")
        report = diagnose_mutation(reference_qasm, candidate_qasm)
        if report["scope"] == "structural-mismatch":
            reason = report.get("reason", "结构不同")
            labels = {
                "register declarations differ": "寄存器声明不同",
                "measurement mappings differ": "测量映射不同",
            }
            report["explanation"] = (
                f"两个电路的{labels.get(reason, reason)}，因此不能把差异归因到某一扇量子门。"
            )
        elif report["first_divergent_gate"] is None:
            report["explanation"] = (
                "在 |0…0⟩ 输入和全局相位等价范围内，没有发现中间量子态分歧。"
            )
        else:
            gate_number = report["first_divergent_gate"] + 1
            distance = report["final_distribution_distance"]
            report["explanation"] = (
                f"第 {gate_number} 扇门后首次出现精确态分歧；"
                f"最终测量分布的总变差距离为 {distance:.6f}。"
            )
        report["scope_note"] = (
            "结论只适用于最多 8 比特、|0…0⟩ 输入的本地精确状态比较，并忽略全局相位；"
            "它不诊断真实硬件噪声来源。"
        )
        self._send_json(HTTPStatus.OK, report)

    def _causal_audit(self, payload: Dict[str, Any]) -> None:
        reference_qasm = payload.get("reference_qasm")
        candidate_qasm = payload.get("candidate_qasm")
        assertions = payload.get("assertions")
        hybrid_source = payload.get("hybrid_source")
        measurement_bits = payload.get("measurement_bits")
        target = payload.get("target", "spinq")
        if not isinstance(reference_qasm, str) or not reference_qasm.strip():
            raise ValueError("reference_qasm 必须是非空字符串")
        if not isinstance(candidate_qasm, str) or not candidate_qasm.strip():
            raise ValueError("candidate_qasm 必须是非空字符串")
        if not isinstance(assertions, list) or not assertions:
            raise ValueError("assertions 必须是非空列表")
        if not isinstance(hybrid_source, str) or not hybrid_source.strip():
            raise ValueError("hybrid_source 必须是非空字符串")
        if measurement_bits is None:
            raise ValueError("measurement_bits 必须提供")
        if target not in adapter.SUPPORTED_TARGETS:
            raise ValueError("target 必须是 spinq、originq 或 braket")
        audit = build_causal_audit(
            reference_qasm,
            candidate_qasm,
            assertions,
            hybrid_source,
            measurement_bits,
            target,
        )
        audit["verification"] = verify_causal_audit(audit)
        self._send_json(HTTPStatus.OK, audit)

    def _prompt_contract(self, payload: Dict[str, Any]) -> None:
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt 必须是非空字符串")
        if len(prompt) > 20_000:
            raise ValueError("prompt 最多 20000 个字符")
        contract = build_prompt_contract(prompt)
        self._send_json(
            HTTPStatus.OK,
            {
                "contract": contract,
                "verification": verify_prompt_contract(contract, prompt),
            },
        )

    def _inquiry(self, payload: Dict[str, Any]) -> None:
        mission = payload.get("mission")
        prediction = payload.get("prediction")
        conclusion = payload.get("conclusion")
        shots = payload.get("shots", 128)
        if mission != "bell-gates":
            raise ValueError("mission 目前必须是 bell-gates")
        if prediction not in {"h-opens-branches", "cx-opens-branches", "not-sure"}:
            raise ValueError("prediction 不是该探究任务提供的选项")
        if conclusion not in {
            "h-opens-branches-cx-correlates",
            "cx-opens-branches",
            "proves-nonlocality",
        }:
            raise ValueError("conclusion 不是该探究任务提供的选项")
        if not isinstance(shots, int) or isinstance(shots, bool) or shots < 16 or shots > 100_000:
            raise ValueError("shots 必须是 16–100000 的整数")

        control_result = adapter.run(_BELL_INQUIRY_CONTROL, "spinq", shots)
        variant_result = adapter.run(_BELL_INQUIRY_VARIANT, "spinq", shots)
        comparison = diagnose_mutation(_BELL_INQUIRY_CONTROL, _BELL_INQUIRY_VARIANT)

        def probabilities(result: Dict[str, Any]) -> Dict[str, float]:
            """Normalize the observed counts recorded in this inquiry passport."""
            return {
                state: count / result["shots"]
                for state, count in result["counts"].items()
            }

        control_probabilities = probabilities(control_result)
        variant_probabilities = probabilities(variant_result)
        control_states = sorted(
            state for state, value in control_probabilities.items() if value > 0
        )
        variant_states = sorted(
            state for state, value in variant_probabilities.items() if value > 0
        )
        evidence_matches_mission = (
            control_states == ["00", "11"]
            and variant_states == ["00", "01"]
            and comparison.get("first_divergent_gate") == 1
            and (comparison.get("reference_operation") or {}).get("gate") == "cx"
        )
        observed_control = "、".join(control_states) or "无"
        observed_variant = "、".join(variant_states) or "无"
        observed_change = (
            f"本次对照观察到 {observed_control}；删掉 CX 后观察到 {observed_variant}。"
        )
        prediction_reviews = {
            "h-opens-branches": {
                "status": "matched" if evidence_matches_mission else "inconclusive",
                "reason": observed_change
                + (
                    " 结果支持 H 先产生两种 Z 基测量结果。"
                    if evidence_matches_mission
                    else " 本次有限采样不足以核验预测。"
                ),
            },
            "cx-opens-branches": {
                "status": "revised" if evidence_matches_mission else "inconclusive",
                "reason": observed_change
                + (
                    " 禁用 CX 后仍观察到 q0 的两种结果，因此需修正原预测。"
                    if evidence_matches_mission
                    else " 本次有限采样不足以修正预测。"
                ),
            },
            "not-sure": {
                "status": "observed" if evidence_matches_mission else "inconclusive",
                "reason": observed_change
                + (
                    " 该差异与 g2 的 CX 操作一致。"
                    if evidence_matches_mission
                    else " 本次有限采样未呈现任务要求的完整证据形状。"
                ),
            },
        }
        conclusion_audits = {
            "h-opens-branches-cx-correlates": {
                "status": "supported",
                "claim": "对 |00⟩ 输入，H 使 q0 的 Z 基测量出现 0/1 两种结果；CX 将 q0 的值关联到 q1。",
                "reason": observed_change
                + " 对照只禁用了 CX，因此观测差异定位到 g2。",
            },
            "cx-opens-branches": {
                "status": "unsupported",
                "claim": "CX 使 q0 的 Z 基测量首次出现 0/1 两种结果。",
                "reason": observed_change
                + " 禁用 CX 后 q0 仍取到 0/1，因此该结论不受实验支持。",
            },
            "proves-nonlocality": {
                "status": "unsupported",
                "claim": "这次 Z 基实验完整证明了 Bell 非定域性。",
                "reason": "当前实验只比较计算基测量相关性；完整的非定域性检验需要额外测量设置与统计判据。",
            },
        }
        conclusion_evidence = [
            {"experiment": "control", "observed_states": control_states},
            {"experiment": "variant", "observed_states": variant_states},
            {
                "first_divergent_gate": None
                if comparison.get("first_divergent_gate") is None
                else f"g{comparison['first_divergent_gate'] + 1}",
                "reference_operation": (
                    comparison.get("reference_operation") or {}
                ).get("gate"),
            },
        ]
        audited_conclusions = {}
        for audit_id, audit in conclusion_audits.items():
            if not evidence_matches_mission and audit_id != "proves-nonlocality":
                audit = {
                    "status": "inconclusive",
                    "claim": audit["claim"],
                    "reason": observed_change
                    + " 本次有限采样未满足任务的预期证据形状，系统拒绝替学习者下结论。",
                }
            audited_conclusions[audit_id] = {
                **audit,
                "evidence": conclusion_evidence,
            }
        conclusion_audit = audited_conclusions[conclusion]
        self._send_json(
            HTTPStatus.OK,
            {
                "schema_version": "loomq-inquiry-passport-v1",
                "mission": {
                    "id": "bell-gates",
                    "title": "H 和 CX 分别做了什么？",
                    "question": "删掉 CX 后，Bell 电路的测量分布会怎样变化？",
                },
                "learner": {"prediction": prediction, "conclusion": conclusion},
                "prediction_review": prediction_reviews[prediction],
                "experiment": {
                    "control": {
                        "qasm": _BELL_INQUIRY_CONTROL,
                        "result": control_result,
                        "probabilities": control_probabilities,
                    },
                    "variant": {
                        "qasm": _BELL_INQUIRY_VARIANT,
                        "result": variant_result,
                        "probabilities": variant_probabilities,
                    },
                    "changed_variable": {
                        "action": "disable",
                        "witness_id": "g2",
                        "operation": "cx q[0],q[1]",
                    },
                },
                "comparison": comparison,
                "conclusion_audit": conclusion_audit,
                "conclusion_audits": audited_conclusions,
                "scope_caveats": [
                    "该实验展示计算基测量相关性，不能单独证明 Bell 非定域性",
                    "结果来自本地理想模拟和有限 shots，不诊断真实硬件噪声来源",
                    "这里的“分支”仅指本地理想模拟中概率非零的计算基测量结果",
                ],
                "replay": {
                    "endpoint": "/api/inquiry",
                    "request": {
                        "mission": mission,
                        "prediction": prediction,
                        "conclusion": conclusion,
                        "shots": shots,
                    },
                },
            },
        )

    def _agent(self, payload: Dict[str, Any]) -> None:
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt 必须是非空字符串")
        if len(prompt) > 20_000:
            raise ValueError("prompt 最多 20000 个字符")
        history = normalize_history(payload.get("history"))
        required = ("LOOMQ_LLM_BASE_URL", "LOOMQ_LLM_API_KEY", "LOOMQ_LLM_MODEL")
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "llm_not_configured",
                "请先在启动服务的 shell 配置 " + "、".join(missing),
            )
            return
        reply = adapter.agent_chat(prompt, history)
        self._send_json(HTTPStatus.OK, {"reply": reply})


def create_server(host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    """Create a local threaded server; callers own serve/shutdown lifecycle."""
    return ThreadingHTTPServer((host, port), LoomQWebHandler)


def main() -> int:
    parser = argparse.ArgumentParser(description="LoomQ 零依赖本地 Web 实验台")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = create_server(args.host, args.port)
    print(f"LoomQ Web Lab: http://{args.host}:{server.server_port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
