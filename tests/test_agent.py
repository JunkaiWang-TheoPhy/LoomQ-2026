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

VALID_BELL = """```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
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
            VALID_BELL,
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat("请在 Braket 平台上生成 Bell 态并测量")

        self.assertEqual(reply, VALID_BELL)
        self.assertEqual(len(SequenceAPIHandler.requests), 2)

    def test_semantically_wrong_ghz_is_retried(self):
        SequenceAPIHandler.responses = [VALID_BELL, VALID_GHZ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat("请生成三比特最大纠缠 GHZ 态并测量全部比特")

        self.assertEqual(reply, VALID_GHZ)
        self.assertEqual(len(SequenceAPIHandler.requests), 2)
        diagnostic = SequenceAPIHandler.requests[1]["messages"][-1]["content"]
        self.assertIn("3 qubits", diagnostic)
        self.assertIn("GHZ", diagnostic)

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

    def test_incompatible_backend_is_retried_with_constraints(self):
        SequenceAPIHandler.responses = [
            "推荐 `spinq_cloud_qpu`，它很适合。",
            "推荐 `braket_local_simulator`：支持 15 比特、免费且无排队。",
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat("需要一个免费、零排队的 15 比特后端")

        self.assertIn("braket_local_simulator", reply)
        self.assertEqual(len(SequenceAPIHandler.requests), 2)
        diagnostic = SequenceAPIHandler.requests[1]["messages"][-1]["content"]
        self.assertIn("15 qubits", diagnostic)
        self.assertIn("queue=none", diagnostic)
        self.assertIn("cost=free", diagnostic)

    def test_backend_selection_wins_when_prompt_also_mentions_circuit(self):
        SequenceAPIHandler.responses = [
            "推荐 `braket_local_simulator`：15 比特且无需排队。"
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat(
                "我需要运行一个 15 比特电路，而且要求零排队，应该选哪个平台？"
            )

        self.assertIn("braket_local_simulator", reply)
        self.assertEqual(len(SequenceAPIHandler.requests), 1)

    def test_english_hyphenated_backend_constraints_are_validated(self):
        SequenceAPIHandler.responses = [
            "Use `braket_local_simulator`; it is free and has no queue."
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat(
                "Which platform should I choose for a free 15-qubit circuit with no queue?"
            )

        self.assertIn("braket_local_simulator", reply)
        self.assertEqual(len(SequenceAPIHandler.requests), 1)

    def test_zero_queue_hyphen_rejects_a_queued_backend(self):
        SequenceAPIHandler.responses = [
            "Recommend `originq_wukong`.",
            "Recommend `braket_local_simulator`.",
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            reply = adapter.agent_chat("I need a free zero-queue 15-qubit backend")

        self.assertIn("braket_local_simulator", reply)
        self.assertEqual(len(SequenceAPIHandler.requests), 2)
        self.assertIn(
            "queue=none", SequenceAPIHandler.requests[1]["messages"][-1]["content"]
        )

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
