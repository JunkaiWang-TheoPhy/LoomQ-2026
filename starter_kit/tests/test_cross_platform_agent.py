import unittest
from unittest.mock import patch
import json
import threading
import urllib.request

from loomq.cross_platform_agent import build_cross_platform_plan
from loomq.web import create_server


BELL_QASM = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""


class CrossPlatformAgentTests(unittest.TestCase):
    def test_one_agent_request_is_compiled_and_checked_on_all_local_platform_adapters(self):
        def completion(_messages):
            return {"choices": [{"message": {"content": f"```qasm\n{BELL_QASM}```"}}]}

        report = build_cross_platform_plan(
            "生成一个两比特 Bell 态并测量，比较三个平台",
            completion,
            shots=128,
        )

        self.assertEqual(report["schema_version"], "loomq-cross-platform-agent-plan-v1")
        self.assertEqual(report["platform_count"], 3)
        self.assertEqual(set(report["platforms"]), {"spinq", "originq", "braket"})
        self.assertTrue(report["consistency"]["all_counts_equal"])
        self.assertEqual(report["recommended_backend"], "spinq_taurus_simulator")
        for adapter_report in report["adapters"]:
            self.assertEqual(sum(adapter_report["result"]["counts"].values()), 128)
            self.assertTrue(adapter_report["counts_match_reference"])
            self.assertTrue(adapter_report["native_ir"])

    def test_cross_platform_plan_rejects_unverified_model_output(self):
        def completion(_messages):
            return {"choices": [{"message": {"content": "no circuit"}}]}

        with self.assertRaisesRegex(RuntimeError, "failed deterministic validation"):
            build_cross_platform_plan("生成一个全新的拓扑态实验", completion)

    def test_web_endpoint_returns_the_cross_platform_plan(self):
        server = create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://{server.server_address[0]}:{server.server_port}"
        fake_plan = {"schema_version": "loomq-cross-platform-agent-plan-v1", "platform_count": 3}
        try:
            request = urllib.request.Request(
                base + "/api/cross-platform-agent",
                data=json.dumps({"prompt": "生成 Bell 态"}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with patch.dict(
                "os.environ",
                {
                    "LOOMQ_LLM_BASE_URL": "http://fixture",
                    "LOOMQ_LLM_API_KEY": "fixture",
                    "LOOMQ_LLM_MODEL": "fixture",
                },
            ), patch("loomq.web.adapter.cross_platform_agent", return_value=fake_plan):
                with urllib.request.urlopen(request, timeout=3) as response:
                    payload = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(payload, fake_plan)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
