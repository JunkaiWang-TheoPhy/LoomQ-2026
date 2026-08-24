import json
import unittest

from loomq.assertions import (
    diagnose_mutation,
    diagnose_observed_execution,
    evaluate_assertions,
    evaluate_distribution_assertions,
)
from loomq.qasm import parse_qasm


BELL = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""


class AssertionTests(unittest.TestCase):
    def test_bell_support_parity_and_uniformity_are_machine_checkable(self):
        bell = parse_qasm(BELL)

        report = evaluate_assertions(
            bell,
            [
                {"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999},
                {"kind": "parity", "bits": [0, 1], "expected": "even", "minimum_probability": 0.999},
                {"kind": "uniformity", "states": ["00", "11"], "maximum_total_variation": 1e-12},
            ],
        )

        self.assertEqual([item["status"] for item in report], ["pass", "pass", "pass"])
        self.assertTrue(all(item["evidence_mode"] == "exact-local" for item in report))

    def test_counts_use_confidence_bounds_and_can_be_inconclusive(self):
        report = evaluate_distribution_assertions(
            {"00": 48, "11": 47, "01": 3, "10": 2},
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}],
            shots=100,
        )

        self.assertEqual(report[0]["evidence_mode"], "finite-shots")
        self.assertEqual(report[0]["status"], "inconclusive")
        self.assertIn("confidence_interval", report[0])

    def test_provider_probabilities_are_labeled_without_fabricated_interval(self):
        report = evaluate_distribution_assertions(
            {"00": 0.5, "11": 0.5},
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}],
        )

        self.assertEqual(report[0]["evidence_mode"], "provider-probabilities")
        self.assertNotIn("confidence_interval", report[0])

    def test_schema_validation_rejects_invalid_assertions(self):
        cases = [
            (
                "unsupported kind",
                {"00": 1.0},
                [{"kind": "bogus"}],
                None,
                "unsupported assertion kind",
            ),
            (
                "malformed state",
                {"00": 1.0},
                [{"kind": "support", "states": ["0x"], "minimum_probability": 0.1}],
                None,
                "states must be a non-empty list of unique bit strings",
            ),
            (
                "duplicate state",
                {"00": 1.0},
                [{"kind": "support", "states": ["00", "00"], "minimum_probability": 0.1}],
                None,
                "states must be a non-empty list of unique bit strings",
            ),
            (
                "empty states",
                {"00": 1.0},
                [{"kind": "support", "states": [], "minimum_probability": 0.1}],
                None,
                "states must be a non-empty list of unique bit strings",
            ),
            (
                "mixed widths",
                {"0": 0.5, "00": 0.5},
                [{"kind": "support", "states": ["00"], "minimum_probability": 0.1}],
                None,
                "distribution keys must all have the same width",
            ),
            (
                "invalid bit index",
                {"00": 1.0},
                [{"kind": "parity", "bits": [2], "expected": "even", "minimum_probability": 0.1}],
                None,
                "bit index out of range",
            ),
            (
                "duplicate bit index",
                {"00": 1.0},
                [{"kind": "parity", "bits": [0, 0], "expected": "even", "minimum_probability": 0.1}],
                None,
                "bits must not contain duplicates",
            ),
            (
                "invalid parity expected",
                {"00": 1.0},
                [{"kind": "parity", "bits": [0], "expected": "balanced", "minimum_probability": 0.1}],
                None,
                "expected parity must be 'even' or 'odd'",
            ),
            (
                "boolean threshold",
                {"00": 1.0},
                [{"kind": "support", "states": ["00"], "minimum_probability": True}],
                None,
                "minimum_probability must be a real number in \\[0, 1\\]",
            ),
            (
                "out of range minimum probability",
                {"00": 1.0},
                [{"kind": "support", "states": ["00"], "minimum_probability": 1.1}],
                None,
                "minimum_probability must be a real number in \\[0, 1\\]",
            ),
            (
                "out of range maximum total variation",
                {"00": 1.0},
                [{"kind": "uniformity", "states": ["00"], "maximum_total_variation": -0.1}],
                None,
                "maximum_total_variation must be a real number in \\[0, 1\\]",
            ),
            (
                "boolean distribution value",
                {"00": True},
                [{"kind": "support", "states": ["00"], "minimum_probability": 0.1}],
                None,
                "distribution values must be finite non-negative real numbers",
            ),
            (
                "non-normalizable distribution",
                {"00": 0.0, "11": 0.0},
                [{"kind": "support", "states": ["00"], "minimum_probability": 0.1}],
                None,
                "distribution must have positive total mass",
            ),
        ]

        for label, distribution, assertions, shots, pattern in cases:
            with self.subTest(label=label):
                with self.assertRaisesRegex(ValueError, pattern):
                    evaluate_distribution_assertions(distribution, assertions, shots=shots)

    def test_mutated_bell_reports_first_divergent_gate(self):
        report = diagnose_mutation(BELL, BELL.replace("cx q[0],q[1];", "x q[1];"))

        self.assertFalse(report["equivalent_output_distribution"])
        self.assertEqual(report["first_divergent_gate"], 1)
        self.assertEqual(report["scope"], "exact-up-to-global-phase-at-zero-input")

    def test_mutation_diagnosis_reports_structural_mismatch_without_simulating(self):
        report = diagnose_mutation(
            BELL,
            BELL.replace("measure q -> c;", "measure q[0] -> c[1];\nmeasure q[1] -> c[0];"),
        )

        self.assertEqual(report["scope"], "structural-mismatch")
        self.assertEqual(report["reason"], "measurement mappings differ")
        self.assertIsNone(report["first_divergent_gate"])
        self.assertNotIn("max_amplitude_delta", report)

    def test_mutation_diagnosis_rejects_more_than_eight_qubits(self):
        large = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[9];
creg c[9];
measure q -> c;
"""

        with self.assertRaisesRegex(ValueError, "at most 8 qubits"):
            diagnose_mutation(large, large)

    def test_hardware_failure_is_not_mislabeled_as_a_noise_mechanism(self):
        report = diagnose_observed_execution(
            parse_qasm(BELL),
            {"00": 55, "01": 45},
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}],
            shots=100,
        )

        self.assertEqual(report["classification"], "execution-deviation-detected")
        self.assertNotIn("depolarizing", json.dumps(report).lower())

    def test_hardware_diagnosis_can_confirm_consistency_with_reference(self):
        report = diagnose_observed_execution(
            parse_qasm(BELL),
            {"00": 55, "11": 45},
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}],
            shots=100,
        )

        self.assertEqual(report["classification"], "consistent-with-reference")
        self.assertEqual(report["observed_assertions"][0]["status"], "pass")

    def test_hardware_diagnosis_reports_reference_program_failures(self):
        report = diagnose_observed_execution(
            parse_qasm(BELL),
            {"00": 100},
            [{"kind": "support", "states": ["01"], "minimum_probability": 0.90}],
            shots=100,
        )

        self.assertEqual(report["classification"], "reference-program-fails")
        self.assertEqual(report["reference_assertions"][0]["status"], "fail")
        self.assertEqual(report["observed_assertions"], [])


if __name__ == "__main__":
    unittest.main()
