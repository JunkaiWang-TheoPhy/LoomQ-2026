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


if __name__ == "__main__":
    unittest.main()
