import json
import tempfile
import unittest
from pathlib import Path

from scripts import offline_stress_campaign as campaign


class OfflineStressCampaignTests(unittest.TestCase):
    def test_small_campaign_exercises_every_lane_without_failure(self):
        report = campaign.run_campaign(
            l1_circuits=2,
            l3_programs=2,
            invalid_qasm_cases=2,
            invalid_riscv_cases=2,
        )

        self.assertTrue(report["passed"], report["failures"])
        self.assertEqual(report["total_checks"], 22)
        self.assertEqual(set(report["campaigns"]), set(campaign.CAMPAIGN_SPECS))

    def test_committed_summary_validator_binds_scale_and_corpus(self):
        report = campaign.expected_summary_fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.json"
            path.write_text(json.dumps(report), encoding="utf-8")
            self.assertTrue(campaign.validate_summary(path)["valid"])
            report["total_checks"] -= 1
            path.write_text(json.dumps(report), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "total checks"):
                campaign.validate_summary(path)


if __name__ == "__main__":
    unittest.main()
