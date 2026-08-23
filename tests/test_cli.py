import json
import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

from starter_kit import loomq_cli


ROOT = Path(__file__).resolve().parents[1]


class CLITests(unittest.TestCase):
    def run_cli(self, *arguments):
        return subprocess.run(
            [sys.executable, "-m", "starter_kit.loomq_cli", *arguments],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def write_bell(self, directory):
        path = Path(directory) / "bell.qasm"
        path.write_text(
            """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0]; cx q[0],q[1]; measure q -> c;
""",
            encoding="utf-8",
        )
        return path

    def test_help_exposes_beginner_workflow(self):
        result = self.run_cli("--help")

        self.assertEqual(result.returncode, 0)
        self.assertIn("transpile", result.stdout)
        self.assertIn("run", result.stdout)
        self.assertIn("trace", result.stdout)
        self.assertIn("chat", result.stdout)

    def test_transpile_prints_target_ir(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_bell(directory)
            result = self.run_cli("transpile", "--target", "braket", str(path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("OPENQASM 3.0", result.stdout)
        self.assertIn("cnot q[0],q[1]", result.stdout)

    def test_run_json_is_machine_readable_and_schema_complete(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_bell(directory)
            result = self.run_cli(
                "run", "--target", "spinq", "--shots", "64", "--json", str(path)
            )

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(payload["counts"], {"00": 32, "11": 32})
        self.assertEqual(payload["bit_order"], "little")

    def test_default_run_explains_counts_with_visible_bars(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_bell(directory)
            result = self.run_cli("run", "--target", "originq", "--shots", "16", str(path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("00 |", result.stdout)
        self.assertIn("11 |", result.stdout)
        self.assertIn("最右侧是 c[0]", result.stdout)

    def test_trace_explains_each_gate_and_phase_as_json(self):
        source = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1]; creg c[1];
h q[0]; s q[0]; measure q -> c;
"""
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "phase.qasm"
            path.write_text(source, encoding="utf-8")
            result = self.run_cli("trace", "--json", str(path))

        self.assertEqual(result.returncode, 0, result.stderr)
        payload = json.loads(result.stdout)
        self.assertEqual(
            [event["operation"]["kind"] for event in payload],
            ["initial", "gate", "gate", "measure"],
        )
        self.assertEqual(payload[2]["operation"]["gate"], "s")
        self.assertAlmostEqual(payload[2]["states"][1]["phase_radians"], 1.5707963267948966)

    def test_trace_human_output_is_a_beginner_readable_gate_story(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write_bell(directory)
            result = self.run_cli("trace", str(path))

        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("逐门状态故事", result.stdout)
        self.assertIn("01 · H · q[0]", result.stdout)
        self.assertIn("02 · CX · q[0], q[1]", result.stdout)
        self.assertIn("|00⟩ P=50.00%", result.stdout)
        self.assertIn("|11⟩ P=50.00%", result.stdout)

    def test_invalid_qasm_returns_actionable_error_without_traceback(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bad.qasm"
            path.write_text("h q[0];", encoding="utf-8")
            result = self.run_cli("run", "--target", "spinq", str(path))

        self.assertEqual(result.returncode, 2)
        self.assertIn("missing OPENQASM 2.0", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_ask_generates_runs_and_explains_in_one_command(self):
        reply = """当然可以：
```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0]; cx q[0],q[1]; measure q -> c;
```
"""
        output = io.StringIO()

        with mock.patch.object(loomq_cli.adapter, "agent_chat", return_value=reply):
            with redirect_stdout(output):
                status = loomq_cli.main(
                    ["ask", "--target", "spinq", "--shots", "16", "生成 Bell 态"]
                )

        rendered = output.getvalue()
        self.assertEqual(status, 0)
        self.assertIn("OPENQASM 2.0", rendered)
        self.assertIn("00 |", rendered)
        self.assertIn("11 |", rendered)
        self.assertIn("自然语言目标已经转换并完成本地验证", rendered)


if __name__ == "__main__":
    unittest.main()
