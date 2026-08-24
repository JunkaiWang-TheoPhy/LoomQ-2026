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

    def test_mutated_bell_reports_first_divergent_gate(self):
        report = diagnose_mutation(BELL, BELL.replace("cx q[0],q[1];", "x q[1];"))

        self.assertFalse(report["equivalent_output_distribution"])
        self.assertEqual(report["first_divergent_gate"], 1)
        self.assertEqual(report["scope"], "exact-up-to-global-phase-at-zero-input")

    def test_hardware_failure_is_not_mislabeled_as_a_noise_mechanism(self):
        report = diagnose_observed_execution(
            parse_qasm(BELL),
            {"00": 55, "01": 45},
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}],
            shots=100,
        )

        self.assertEqual(report["classification"], "execution-deviation-detected")
        self.assertNotIn("depolarizing", json.dumps(report).lower())


if __name__ == "__main__":
    unittest.main()
