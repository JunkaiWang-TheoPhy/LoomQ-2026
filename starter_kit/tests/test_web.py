import json
import os
import threading
import unittest
import urllib.error
import urllib.request
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
