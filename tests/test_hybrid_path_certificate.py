import unittest

from starter_kit import adapter
from starter_kit.loomq.hybrid_path_certificate import verify_hybrid_path_certificate


HYBRID = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
classical {
  if (c[0] == 1) { r1 = 7; } else { r1 = 3; }
}
"""

DETERMINISTIC = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1]; creg c[1];
x q[0];
measure q -> c;
classical {
  if (c[0] == 1) { r1 = 7; } else { r1 = 3; }
}
"""


class HybridPathCertificateTests(unittest.TestCase):
    def test_reports_exact_path_probabilities_and_unreachable_outcomes(self):
        certificate = adapter.hybrid_path_certificate(HYBRID)
        self.assertEqual(certificate["schema_version"], "loomq-hybrid-path-certificate-v1")
        self.assertEqual(certificate["projected_measurement_bits"], [0])
        self.assertEqual(
            [item["branch_path"] for item in certificate["path_probabilities"]],
            ["if1:F", "if1:T"],
        )
        self.assertEqual(
            [item["probability"] for item in certificate["path_probabilities"]],
            [0.5, 0.5],
        )
        self.assertEqual(certificate["unreachable_outcomes"], [])
        self.assertTrue(verify_hybrid_path_certificate(certificate)["valid"])

    def test_records_unreachable_outcomes_with_zero_probability(self):
        certificate = adapter.hybrid_path_certificate(DETERMINISTIC)
        self.assertEqual(
            [item["branch_path"] for item in certificate["path_probabilities"]],
            ["if1:T"],
        )
        self.assertEqual(
            [item["probability"] for item in certificate["path_probabilities"]],
            [1.0],
        )
        self.assertEqual(
            certificate["unreachable_outcomes"],
            [{"measurement_bits": [0], "branch_path": "if1:F", "probability": 0.0}],
        )


if __name__ == "__main__":
    unittest.main()
