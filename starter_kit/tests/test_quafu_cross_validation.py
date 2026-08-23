import json
import tempfile
import unittest
from pathlib import Path

from scripts import quafu_cross_validate as cross_validate


class QuafuCrossValidationTests(unittest.TestCase):
    def test_corpus_is_fixed_unique_and_covers_all_official_gates(self):
        corpus = cross_validate.build_corpus()

        self.assertEqual(len(corpus), 40)
        self.assertEqual(len(set(corpus)), 40)
        self.assertEqual(cross_validate.gates_in(corpus), set(cross_validate.OFFICIAL_GATES))
        self.assertEqual(
            cross_validate.corpus_sha256(corpus),
            cross_validate.EXPECTED_CORPUS_SHA256,
        )

    def test_summary_validator_binds_corpus_targets_and_success_counts(self):
        summary = {
            "schema_version": cross_validate.SCHEMA_VERSION,
            "seed": cross_validate.SEED,
            "circuits": 40,
            "targets_per_circuit": 3,
            "target_checks": 120,
            "passed_target_checks": 120,
            "failed_target_checks": 0,
            "corpus_sha256": cross_validate.EXPECTED_CORPUS_SHA256,
            "official_gates": sorted(cross_validate.OFFICIAL_GATES),
            "pyquafu_version": "0.4.5",
            "max_amplitude_error": 1e-12,
            "max_count_l1_distance": 2,
            "count_tie_tolerance_l1": 2,
            "global_phase_aligned": True,
            "shots_per_target_check": cross_validate.SHOTS,
            "passed": True,
        }
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "summary.json"
            path.write_text(json.dumps(summary), encoding="utf-8")
            self.assertTrue(cross_validate.validate_summary(path)["valid"])
            summary["passed_target_checks"] = 119
            path.write_text(json.dumps(summary), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "target check"):
                cross_validate.validate_summary(path)

            summary["passed_target_checks"] = 120
            summary["pyquafu_version"] = "0.0.0"
            path.write_text(json.dumps(summary), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "PyQuafu version"):
                cross_validate.validate_summary(path)


if __name__ == "__main__":
    unittest.main()
