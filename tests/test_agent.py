import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

from starter_kit import adapter


VALID_GHZ = """```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;
```"""


class SequenceAPIHandler(BaseHTTPRequestHandler):
    responses = []
    requests = []

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        type(self).requests.append(json.loads(self.rfile.read(length)))
        content = type(self).responses.pop(0)
        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": content}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class AgentTests(unittest.TestCase):
    def setUp(self):
        SequenceAPIHandler.responses = []
        SequenceAPIHandler.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), SequenceAPIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.environment = {
            "LOOMQ_LLM_BASE_URL": f"http://127.0.0.1:{self.server.server_port}",
            "LOOMQ_LLM_API_KEY": "local-test-key",
            "LOOMQ_LLM_MODEL": "deepseek-v4-flash",
            "LOOMQ_LLM_TIMEOUT_SECONDS": "2",
        }

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_qasm_response_is_validated_and_retried_with_diagnostics(self):
        SequenceAPIHandler.responses = [
            "OPENQASM 2.0; include \"qelib1.inc\"; qreg q[1]; creg c[1]; h q[4];",
            VALID_GHZ,
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat("生成一个 3 比特 GHZ 态并进行全测量")

        self.assertEqual(reply, VALID_GHZ)
        self.assertEqual(len(SequenceAPIHandler.requests), 2)
        retry_messages = SequenceAPIHandler.requests[1]["messages"]
        self.assertIn("out of range", retry_messages[-1]["content"])
        self.assertEqual(SequenceAPIHandler.requests[0]["thinking"], {"type": "disabled"})

    def test_platform_qualified_generation_still_validates_qasm(self):
        SequenceAPIHandler.responses = [
            "OPENQASM 2.0; include \"qelib1.inc\"; qreg q[1]; creg c[1]; h q[9];",
            VALID_GHZ,
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat("请在 Braket 平台上生成 Bell 态并测量")

        self.assertEqual(reply, VALID_GHZ)
        self.assertEqual(len(SequenceAPIHandler.requests), 2)

    def test_backend_request_is_grounded_in_official_capability_ids(self):
        SequenceAPIHandler.responses = [
            "推荐 `braket_local_simulator`：满足 15 比特且无需排队。"
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat("15 比特、零排队，应该选择哪个后端？")

        self.assertIn("braket_local_simulator", reply)
        self.assertEqual(len(SequenceAPIHandler.requests), 1)
        system = SequenceAPIHandler.requests[0]["messages"][0]["content"]
        self.assertIn('"id": "braket_local_simulator"', system)
        self.assertIn("规范后端标识", system)

    def test_missing_choices_is_reported_without_credentials(self):
        class EmptyHandler(SequenceAPIHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length", "0"))
                self.rfile.read(length)
                body = json.dumps({"choices": []}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), EmptyHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.environment["LOOMQ_LLM_BASE_URL"] = (
            f"http://127.0.0.1:{self.server.server_port}"
        )

        with mock.patch.dict(os.environ, self.environment, clear=True):
            with self.assertRaisesRegex(RuntimeError, "no assistant content") as caught:
                adapter.agent_chat("生成 Bell 态")
        self.assertNotIn("local-test-key", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
