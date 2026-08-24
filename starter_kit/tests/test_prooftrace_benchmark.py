import json
import unittest

from scripts.prooftrace_benchmark import run_benchmark, validate_report


class ProofTraceBenchmarkTests(unittest.TestCase):
    def test_committed_corpus_detects_every_native_ir_deletion(self):
        report = run_benchmark()

        self.assertGreaterEqual(report["total_mutants"], 200)
        self.assertEqual(report["detected_mutants"], report["total_mutants"])
        self.assertEqual(report["false_accepts"], 0)
        self.assertEqual(report["portability_checks"], 15)
        self.assertGreaterEqual(report["rewrite_checks"], 120)
        self.assertTrue(report["passed"])

    def test_benchmark_is_deterministic_and_json_safe(self):
        first = run_benchmark()
        second = run_benchmark()

        self.assertEqual(first, second)
        self.assertRegex(first["corpus_sha256"], r"^[0-9a-f]{64}$")
        self.assertTrue(validate_report(first))
        tampered = {**first, "corpus_sha256": "0" * 64}
        self.assertFalse(validate_report(tampered))
        json.dumps(first, sort_keys=True)


if __name__ == "__main__":
    unittest.main()
