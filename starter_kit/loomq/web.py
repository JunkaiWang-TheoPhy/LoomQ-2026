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
except ImportError:  # Direct execution from starter_kit/.
    import adapter


_WEB_ROOT = Path(__file__).resolve().parents[1] / "web"
_STATIC = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
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
        native_ir = adapter.transpile(qasm, target)
        probabilities = {
            state: count / result["shots"] for state, count in result["counts"].items()
        }
        self._send_json(
            HTTPStatus.OK,
            {"result": result, "probabilities": probabilities, "native_ir": native_ir},
        )

    def _agent(self, payload: Dict[str, Any]) -> None:
        prompt = payload.get("prompt")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("prompt 必须是非空字符串")
        required = ("LOOMQ_LLM_BASE_URL", "LOOMQ_LLM_API_KEY", "LOOMQ_LLM_MODEL")
        missing = [name for name in required if not os.environ.get(name)]
        if missing:
            self._error(
                HTTPStatus.SERVICE_UNAVAILABLE,
                "llm_not_configured",
                "请先在启动服务的 shell 配置 " + "、".join(missing),
            )
            return
        reply = adapter.agent_chat(prompt)
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

