import json
import subprocess
import sys
import unittest
from unittest import mock
from pathlib import Path

from starter_kit import verify_submission


ROOT = Path(__file__).resolve().parents[1]


class SubmissionVerifierTests(unittest.TestCase):
    def test_controlled_command_failure_is_reported_and_returns_nonzero(self):
        report = verify_submission.run_phases(
            [("controlled", [sys.executable, "-c", "raise SystemExit(7)"])]
        )

        self.assertFalse(report["passed"])
        self.assertEqual(report["phases"][0]["returncode"], 7)

    def test_real_credential_free_verification_is_one_command(self):
        result = subprocess.run(
            [sys.executable, "starter_kit/verify_submission.py", "--json"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertTrue(report["passed"])
        names = [phase["name"] for phase in report["phases"]]
        expected = {
            "compile",
            "frontend-syntax",
            "web-integration",
            "archive-tests",
            "l2-corpus",
            "hardware-evidence",
            "pyquafu-evidence",
            "prooftrace-benchmark",
            "offline-stress-evidence",
            "l1",
            "l3",
            "quantum-riscv",
        }
        self.assertTrue(expected.issubset(set(names)))
        self.assertEqual(names[0], "compile")
        self.assertLess(names.index("frontend-syntax"), names.index("web-integration"))
        self.assertLess(names.index("web-integration"), names.index("archive-tests"))
        self.assertEqual(names[-1], "quantum-riscv")

    def test_default_phases_mark_frontend_syntax_as_optional_skip_without_node(self):
        with mock.patch("starter_kit.verify_submission.shutil.which", return_value=None):
            phases = verify_submission.default_phases()

        frontend = next(phase for phase in phases if phase["name"] == "frontend-syntax")
        self.assertTrue(frontend["optional"])
        self.assertIsNone(frontend["command"])
        self.assertIn("SKIP", frontend["skip_reason"].upper().replace("SKIPPING", "SKIP"))


if __name__ == "__main__":
    unittest.main()
