import json
import unittest

from scripts.prooftrace_benchmark import run_benchmark, validate_report


class ProofTraceBenchmarkTests(unittest.TestCase):
    def test_committed_corpus_detects_every_native_ir_deletion(self):
        report = run_benchmark()

        self.assertEqual(report["circuit_count"], 5)
        self.assertGreaterEqual(report["total_mutants"], 200)
        self.assertEqual(report["detected_mutants"], report["total_mutants"])
        self.assertEqual(report["false_accepts"], 0)
        self.assertEqual(report["false_accept_details"], [])
        self.assertEqual(report["semantic_checks"], report["total_mutants"])
        self.assertEqual(report["semantic_rejections"], report["total_mutants"])
        self.assertEqual(report["semantic_false_accepts"], 0)
        self.assertEqual(report["semantic_false_accept_details"], [])
        self.assertEqual(report["semantic_scope_skips"], [])
        self.assertEqual(report["portability_checks"], 15)
        self.assertGreaterEqual(report["rewrite_checks"], 120)
        self.assertEqual(report["failures"], [])
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

    def test_validate_report_fails_closed_on_fixed_contract_mutations(self):
        report = run_benchmark()

        for field, value in (
            ("circuit_count", report["circuit_count"] + 1),
            ("false_accept_details", [{"circuit": "bell.qasm"}]),
            ("semantic_false_accept_details", [{"circuit": "bell.qasm"}]),
            ("semantic_scope_skips", [{"circuit": "bell.qasm"}]),
            ("failures", [{"circuit": "bell.qasm"}]),
        ):
            with self.subTest(field=field):
                tampered = {**report, field: value}
                self.assertFalse(validate_report(tampered))


if __name__ == "__main__":
    unittest.main()
