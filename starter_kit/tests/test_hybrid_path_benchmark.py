import json
import unittest

from scripts.hybrid_path_benchmark import run_benchmark, validate_report


class HybridPathBenchmarkTests(unittest.TestCase):
    def test_benchmark_runs_the_committed_four_fixture_corpus(self):
        report = run_benchmark()

        self.assertEqual(report["schema_version"], "loomq-hybrid-path-benchmark-v1")
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


if __name__ == "__main__":
    unittest.main()
