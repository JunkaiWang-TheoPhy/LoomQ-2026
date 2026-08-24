import unittest
from unittest import mock

import verify_submission


class VerifySubmissionTests(unittest.TestCase):
    def test_frontend_syntax_phase_is_marked_skip_when_node_is_unavailable(self):
        with mock.patch("verify_submission.shutil.which", return_value=None):
            phases = verify_submission.default_phases()

        frontend = next(phase for phase in phases if phase["name"] == "frontend-syntax")
        self.assertTrue(frontend["optional"])
        self.assertIsNone(frontend["command"])
        self.assertIn("node", frontend["skip_reason"])

    def test_skipped_optional_phase_does_not_fail_the_overall_report(self):
        report = verify_submission.run_phases(
            [
                {
                    "name": "frontend-syntax",
                    "command": None,
                    "optional": True,
                    "skip_reason": "node not found",
                }
            ]
        )

        self.assertTrue(report["passed"])
        self.assertTrue(report["phases"][0]["skipped"])
        self.assertEqual(report["phases"][0]["stdout"], "node not found")

    def test_required_phase_without_command_fails_closed(self):
        report = verify_submission.run_phases(
            [
                {
                    "name": "required-phase",
                    "command": None,
                    "optional": False,
                    "skip_reason": "missing binary",
                }
            ]
        )

        self.assertFalse(report["passed"])
        self.assertFalse(report["phases"][0]["skipped"])
        self.assertEqual(report["phases"][0]["returncode"], 1)
        self.assertIn("missing binary", report["phases"][0]["stderr"])


if __name__ == "__main__":
    unittest.main()
