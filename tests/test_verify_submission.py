import json
import subprocess
import sys
import unittest
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
        self.assertEqual(
            [phase["name"] for phase in report["phases"]],
            ["compile", "l1", "l3", "quantum-riscv"],
        )


if __name__ == "__main__":
    unittest.main()
