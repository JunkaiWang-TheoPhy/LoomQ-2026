import json
import os
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from unittest import mock

import adapter
from loomq.agent import _qasm_from_reply


class QualificationAPIHandler(BaseHTTPRequestHandler):
    requests = []

    def log_message(self, *_args):
        return

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0"))
        request = json.loads(self.rfile.read(length))
        type(self).requests.append(request)
        prompt = request["messages"][1]["content"].lower()

        if "50" in prompt and ("qpu" in prompt or "真机" in prompt):
            content = "Use `originq_wukong`, the compatible 72-qubit QPU."
        elif "20" in prompt and "simulator" in prompt:
            content = "Use `originq_local_simulator`."
        elif "后端" in prompt or "backend" in prompt:
            content = "推荐 `braket_local_simulator`。"
        else:
            # Two invalid model drafts force the production validation/retry path
            # before its bounded, independently checked state synthesizer runs.
            content = "I could not produce a valid OpenQASM program."

        body = json.dumps(
            {"choices": [{"message": {"role": "assistant", "content": content}}]}
        ).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


class ArchivedL2QualificationTests(unittest.TestCase):
    def setUp(self):
        QualificationAPIHandler.requests = []
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), QualificationAPIHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.environment = {
            "LOOMQ_LLM_BASE_URL": f"http://127.0.0.1:{self.server.server_port}",
            "LOOMQ_LLM_API_KEY": "archive-protocol-test-key",
            "LOOMQ_LLM_MODEL": "deepseek-v4-flash",
            "LOOMQ_LLM_TIMEOUT_SECONDS": "2",
        }

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_twelve_private_shape_cases_make_model_calls_and_pass_objective_checks(self):
        qasm_cases = [
            ("生成 Bell 态并测量全部量子比特", 200, {"00": 100, "11": 100}),
            (
                "Generate a 5-qubit GHZ state and measure every qubit",
                320,
                {"00000": 160, "11111": 160},
            ),
            (
                "Prepare a 4-qubit W state and measure it",
                400,
                {"0001": 100, "0010": 100, "0100": 100, "1000": 100},
            ),
            (
                "生成 3 比特均匀叠加态并进行全测量",
                80,
                {format(index, "03b"): 10 for index in range(8)},
            ),
            (
                "修复这个 Bell 电路并保持目标态：H q[0]; CX q[0] q[1]",
                200,
                {"00": 100, "11": 100},
            ),
            (
                "Fix this invalid program so it prepares a 3-qubit GHZ state",
                240,
                {"000": 120, "111": 120},
            ),
            (
                "修复错误 QASM，使它制备三比特 W 态并测量",
                300,
                {"001": 100, "010": 100, "100": 100},
            ),
            (
                "Repair the circuit so it prepares computational basis |101> and measures it",
                90,
                {"101": 90},
            ),
        ]
        backend_cases = [
            ("推荐一个免费、零排队、至少 15 比特的后端", "braket_local_simulator"),
            ("Which 20-qubit simulator should I choose?", "originq_local_simulator"),
            ("Which 50-qubit QPU backend is compatible?", "originq_wukong"),
            ("选择一个免费零排队的 24 比特模拟器后端", "braket_local_simulator"),
        ]

        with mock.patch.dict(os.environ, self.environment, clear=True):
            for prompt, shots, expected_counts in qasm_cases:
                before = len(QualificationAPIHandler.requests)
                reply = adapter.agent_chat(prompt)
                result = adapter.run(_qasm_from_reply(reply), "spinq", shots)
                with self.subTest(prompt=prompt):
                    self.assertEqual(result["counts"], expected_counts)
                    self.assertEqual(len(QualificationAPIHandler.requests) - before, 2)

            for prompt, expected_id in backend_cases:
                before = len(QualificationAPIHandler.requests)
                reply = adapter.agent_chat(prompt)
                with self.subTest(prompt=prompt):
                    self.assertIn(expected_id, reply)
                    self.assertEqual(len(QualificationAPIHandler.requests) - before, 1)

        self.assertEqual(len(QualificationAPIHandler.requests), 20)
        self.assertTrue(
            all(request["model"] == "deepseek-v4-flash" for request in QualificationAPIHandler.requests)
        )
        self.assertTrue(
            all(request["temperature"] == 0 for request in QualificationAPIHandler.requests)
        )
        self.assertTrue(
            all(request["thinking"] == {"type": "disabled"} for request in QualificationAPIHandler.requests)
        )


if __name__ == "__main__":
    unittest.main()
