"""Zero-dependency local web lab backed by the public LoomQ adapter contract."""

from __future__ import annotations

import argparse
import json
import os
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict
from urllib.parse import urlparse

try:
    from .. import adapter
    from .agent import normalize_history
    from .assertions import diagnose_mutation, diagnose_observed_execution, evaluate_assertions
    from .prompt_contract import build_prompt_contract, verify_prompt_contract
    from .simulator import trace_statevector
    from .qasm import parse_qasm
    from .witness import build_causal_audit, verify_causal_audit
except ImportError:  # Direct execution from starter_kit/.
    import adapter
    from loomq.agent import normalize_history
    from loomq.assertions import diagnose_mutation, diagnose_observed_execution, evaluate_assertions
    from loomq.prompt_contract import build_prompt_contract, verify_prompt_contract
    from loomq.simulator import trace_statevector
    from loomq.qasm import parse_qasm
    from loomq.witness import build_causal_audit, verify_causal_audit


_WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/favicon.ico": ("favicon.svg", "image/svg+xml"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/enhancements.css": ("enhancements.css", "text/css; charset=utf-8"),
}


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
        path = urlparse(self.path).path
        if path == "/api/health":
            self._send_json(HTTPStatus.OK, {"status": "ok", "service": "loomq-web"})
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
        native_ir, proof = adapter.transpile_with_proof(qasm, target)
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
