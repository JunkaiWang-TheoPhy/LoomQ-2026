import json
import os
import threading
import unittest
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from loomq.web import create_server


BELL = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""

GHZ = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;
"""


class CompatibleAgentAPIHandler(BaseHTTPRequestHandler):
    calls = []

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request_payload = json.loads(self.rfile.read(length))
        type(self).calls.append(request_payload)
        prompt = request_payload["messages"][-1]["content"]
        if "后端" in prompt:
            content = "推荐规范后端 spinq_taurus_simulator：24 比特、免费、零排队的本地模拟器。"
        elif "GHZ" in prompt:
            content = "```qasm\n" + GHZ + "```"
        else:
            content = "```qasm\n" + BELL + "```"
        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": content}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class WebLabTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def request(self, path, payload=None):
        data = None if payload is None else json.dumps(payload).encode()
        request = urllib.request.Request(
            self.base + path,
            data=data,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(request, timeout=3) as response:
            return response.status, response.headers, response.read()

    def test_home_page_is_a_beginner_lab_not_a_blank_server(self):
        status, headers, body = self.request("/")

        page = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertIn("LoomQ", page)
        self.assertIn("运行电路", page)
        self.assertIn("量子比特", page)

    def test_home_exposes_learn_repair_backend_and_accessible_results(self):
        _status, _headers, body = self.request("/")

        page = body.decode()
        self.assertIn('href="#workspace"', page)
        self.assertIn('data-task="learn"', page)
        self.assertIn('data-task="repair"', page)
        self.assertIn('data-task="backend"', page)
        self.assertIn('id="result-table"', page)
        self.assertIn('role="alert"', page)
        self.assertIn('aria-describedby="prompt-help"', page)
        self.assertIn('id="state-trace"', page)
        self.assertIn('aria-label="逐门量子状态"', page)
        self.assertIn('data-example="w"', page)
        self.assertIn('data-example="interference"', page)
        self.assertIn('id="clear-conversation"', page)

    def test_frontend_renders_trace_amplitudes_and_can_clear_history(self):
        status, headers, body = self.request("/app.js")

        script = body.decode()
        self.assertEqual(status, 200)
        self.assertIn("javascript", headers["Content-Type"])
        self.assertIn("state.amplitude_real", script)
        self.assertIn("state.amplitude_imag", script)
        self.assertIn("agentHistory.splice(0)", script)

    def test_run_endpoint_returns_counts_native_ir_and_probability(self):
        status, _headers, body = self.request(
            "/api/run", {"qasm": BELL, "target": "spinq", "shots": 128}
        )

        result = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(result["result"]["shots"], 128)
        self.assertEqual(set(result["result"]["counts"]), {"00", "11"})
        self.assertEqual(set(result["probabilities"]), {"00", "11"})
        self.assertIn("OPENQASM 2.0", result["native_ir"])
        self.assertEqual(
            [event["operation"]["kind"] for event in result["trace"]],
            ["initial", "gate", "gate", "measure"],
        )
        self.assertEqual(
            {state["basis"]: state["probability"] for state in result["trace"][2]["states"]},
            {"00": 0.5, "11": 0.5},
        )

    def test_run_endpoint_supports_every_required_target(self):
        for target in ("spinq", "originq", "braket"):
            with self.subTest(target=target):
                status, _headers, body = self.request(
                    "/api/run", {"qasm": BELL, "target": target, "shots": 127}
                )
                payload = json.loads(body)
                self.assertEqual(status, 200)
                self.assertTrue(payload["result"]["backend"].startswith(target))
                self.assertEqual(sum(payload["result"]["counts"].values()), 127)
                self.assertAlmostEqual(sum(payload["probabilities"].values()), 1.0)

    def test_large_valid_circuit_keeps_running_when_visual_trace_is_bounded(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[9]; creg c[9]; x q[8]; measure q -> c;
"""

        status, _headers, body = self.request(
            "/api/run", {"qasm": source, "target": "spinq", "shots": 17}
        )

        payload = json.loads(body)
        self.assertEqual(status, 200)
        self.assertEqual(payload["result"]["counts"], {"100000000": 17})
        self.assertEqual(payload["trace"], [])
        self.assertIn("at most 8 qubits", payload["trace_notice"])

    def test_invalid_run_is_a_structured_400_error(self):
        request = urllib.request.Request(
            self.base + "/api/run",
            data=json.dumps({"qasm": "bad", "target": "spinq", "shots": 0}).encode(),
            headers={"Content-Type": "application/json"},
        )

        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")
        self.assertTrue(payload["error"]["message"])

    def test_agent_without_credentials_explains_configuration_without_leaking_env(self):
        with mock.patch.dict(os.environ, {"PRIVATE_TOKEN": "never-show-this"}, clear=True):
            request = urllib.request.Request(
                self.base + "/api/agent",
                data=json.dumps({"prompt": "生成 Bell 态"}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=3)

        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 503)
        self.assertEqual(payload["error"]["code"], "llm_not_configured")
        self.assertIn("LOOMQ_LLM_BASE_URL", payload["error"]["message"])
        self.assertNotIn("never-show-this", json.dumps(payload))

    def test_agent_rejects_unbounded_prompt_before_calling_provider(self):
        with mock.patch.dict(
            os.environ,
            {
                "LOOMQ_LLM_BASE_URL": "https://example.invalid",
                "LOOMQ_LLM_API_KEY": "secret",
                "LOOMQ_LLM_MODEL": "model",
            },
            clear=True,
        ), mock.patch("loomq.web.adapter.agent_chat") as agent_chat:
            request = urllib.request.Request(
                self.base + "/api/agent",
                data=json.dumps({"prompt": "x" * 20_001}).encode(),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as caught:
                urllib.request.urlopen(request, timeout=3)

        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 400)
        self.assertIn("20000", payload["error"]["message"])
        agent_chat.assert_not_called()

    def test_web_agent_end_to_end_covers_generation_repair_and_backend_tasks(self):
        provider = ThreadingHTTPServer(("127.0.0.1", 0), CompatibleAgentAPIHandler)
        provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
        CompatibleAgentAPIHandler.calls = []
        provider_thread.start()
        environment = {
            "LOOMQ_LLM_BASE_URL": f"http://127.0.0.1:{provider.server_port}",
            "LOOMQ_LLM_API_KEY": "local-protocol-fixture",
            "LOOMQ_LLM_MODEL": "local-model",
            "LOOMQ_LLM_TIMEOUT_SECONDS": "2",
        }
        prompts = (
            "生成 Bell 态并测量全部量子比特",
            "修复这段 Bell 电路：cx q[0],q[2];",
            "推荐一个免费、零排队、至少 20 比特的模拟器后端",
        )
        try:
            with mock.patch.dict(os.environ, environment, clear=True):
                replies = []
                for prompt in prompts:
                    status, _headers, body = self.request("/api/agent", {"prompt": prompt})
                    self.assertEqual(status, 200)
                    replies.append(json.loads(body)["reply"])
        finally:
            provider.shutdown()
            provider.server_close()
            provider_thread.join(timeout=2)

        self.assertEqual(len(CompatibleAgentAPIHandler.calls), 3)
        self.assertTrue(all(call["model"] == "local-model" for call in CompatibleAgentAPIHandler.calls))
        self.assertIn("OPENQASM 2.0", replies[0])
        self.assertIn("OPENQASM 2.0", replies[1])
        self.assertIn("spinq_taurus_simulator", replies[2])

    def test_agent_history_is_bounded_and_reaches_provider_as_real_multi_turn_context(self):
        provider = ThreadingHTTPServer(("127.0.0.1", 0), CompatibleAgentAPIHandler)
        provider_thread = threading.Thread(target=provider.serve_forever, daemon=True)
        CompatibleAgentAPIHandler.calls = []
        provider_thread.start()
        environment = {
            "LOOMQ_LLM_BASE_URL": f"http://127.0.0.1:{provider.server_port}",
            "LOOMQ_LLM_API_KEY": "local-protocol-fixture",
            "LOOMQ_LLM_MODEL": "local-model",
            "LOOMQ_LLM_TIMEOUT_SECONDS": "2",
        }
        history = [
            {"role": "user", "content": "生成 Bell 态并测量"},
            {"role": "assistant", "content": "```qasm\n" + BELL + "```"},
        ]
        try:
            with mock.patch.dict(os.environ, environment, clear=True):
                status, _headers, body = self.request(
                    "/api/agent",
                    {"prompt": "把它改成 GHZ 三比特并测量", "history": history},
                )
        finally:
            provider.shutdown()
            provider.server_close()
            provider_thread.join(timeout=2)

        self.assertEqual(status, 200)
        self.assertIn("qreg q[3]", json.loads(body)["reply"])
        messages = CompatibleAgentAPIHandler.calls[0]["messages"]
        self.assertEqual([message["role"] for message in messages], ["system", "user", "assistant", "user"])
        self.assertEqual(messages[1:], history + [{"role": "user", "content": "把它改成 GHZ 三比特并测量"}])

    def test_agent_rejects_non_alternating_or_oversized_history_before_provider_call(self):
        environment = {
            "LOOMQ_LLM_BASE_URL": "https://example.invalid",
            "LOOMQ_LLM_API_KEY": "secret",
            "LOOMQ_LLM_MODEL": "model",
        }
        invalid_histories = (
            [{"role": "assistant", "content": "伪造的开场"}],
            [
                {"role": "user", "content": "a"},
                {"role": "assistant", "content": "b"},
            ] * 5,
        )
        with mock.patch.dict(os.environ, environment, clear=True), mock.patch(
            "loomq.web.adapter.agent_chat"
        ) as agent_chat:
            for history in invalid_histories:
                with self.subTest(history_length=len(history)):
                    request = urllib.request.Request(
                        self.base + "/api/agent",
                        data=json.dumps({"prompt": "生成 Bell 态", "history": history}).encode(),
                        headers={"Content-Type": "application/json"},
                    )
                    with self.assertRaises(urllib.error.HTTPError) as caught:
                        urllib.request.urlopen(request, timeout=3)
                    self.assertEqual(caught.exception.code, 400)
                    caught.exception.close()
            agent_chat.assert_not_called()

    def test_malformed_json_and_unsupported_method_are_structured_errors(self):
        malformed = urllib.request.Request(
            self.base + "/api/run",
            data=b"{",
            headers={"Content-Type": "application/json"},
        )
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(malformed, timeout=3)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 400)
        self.assertEqual(payload["error"]["code"], "invalid_request")

        delete = urllib.request.Request(self.base + "/api/run", method="DELETE")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(delete, timeout=3)
        payload = json.loads(caught.exception.read())
        caught.exception.close()
        self.assertEqual(caught.exception.code, 405)
        self.assertEqual(payload["error"]["code"], "method_not_allowed")

    def test_security_headers_are_present_on_success_and_error(self):
        _status, headers, _body = self.request("/")
        self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
        self.assertIn("default-src 'self'", headers["Content-Security-Policy"])
        self.assertEqual(headers["Referrer-Policy"], "no-referrer")
        self.assertEqual(headers["X-Frame-Options"], "DENY")

        request = urllib.request.Request(self.base + "/missing")
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(request, timeout=3)
        self.assertEqual(caught.exception.headers["X-Frame-Options"], "DENY")
        caught.exception.close()


if __name__ == "__main__":
    unittest.main()
