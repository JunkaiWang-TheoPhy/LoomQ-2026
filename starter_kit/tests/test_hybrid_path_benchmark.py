import json
import unittest
from unittest import mock

import scripts.hybrid_path_benchmark as hybrid_path_benchmark
from scripts.hybrid_path_benchmark import run_benchmark, validate_report


class HybridPathBenchmarkTests(unittest.TestCase):
    def test_benchmark_runs_the_committed_four_fixture_corpus(self):
        report = run_benchmark()

        self.assertEqual(report["schema_version"], "loomq-hybrid-path-benchmark-v1")
        self.assertEqual(
            hybrid_path_benchmark.EXPECTED_CORPUS_SHA256,
            "f452982ce91335709cc63911312a8bd1b73f48886dcea2e174b6b4d3396cc7f0",
        )
        self.assertEqual(
            report["corpus_sha256"],
            "f452982ce91335709cc63911312a8bd1b73f48886dcea2e174b6b4d3396cc7f0",
        )
        self.assertEqual(report["fixture_count"], 4)
        self.assertEqual(
            [fixture["name"] for fixture in report["fixtures"]],
            [
                "deterministic-dead-branch",
                "bell-two-path-mass",
                "nested-full-support-paths",
                "same-path-different-final-registers",
            ],
        )
        self.assertEqual(report["tamper_rejections"], 4)
        self.assertTrue(report["passed"])

    def test_report_is_deterministic_and_json_safe(self):
        first = run_benchmark()
        second = run_benchmark()

        self.assertEqual(first, second)
        self.assertRegex(first["corpus_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(validate_report(first))
        self.assertFalse(validate_report({**first, "tamper_rejections": 0}))
        self.assertFalse(validate_report({**first, "fixture_count": 3}))
        json.dumps(first, sort_keys=True)

    def test_fixture_corpus_drift_is_reported_as_a_benchmark_failure(self):
        drifted_fixtures = hybrid_path_benchmark.FIXTURES + (
            {
                "name": "drifted-fixture",
                "source": hybrid_path_benchmark.FIXTURES[0]["source"],
                "max_outcomes": 2,
                "expected": {"live_paths": 1, "dead_paths": 1, "unreachable_outcomes": 1},
            },
        )

        with mock.patch.object(hybrid_path_benchmark, "FIXTURES", drifted_fixtures):
            report = hybrid_path_benchmark.run_benchmark()

        self.assertNotEqual(report["corpus_sha256"], hybrid_path_benchmark.EXPECTED_CORPUS_SHA256)
        self.assertFalse(report["passed"])
        self.assertFalse(validate_report(report))
        self.assertIn(
            {"name": "fixture-corpus", "kind": "corpus-sha256"},
            report["failures"],
        )


if __name__ == "__main__":
    unittest.main()
