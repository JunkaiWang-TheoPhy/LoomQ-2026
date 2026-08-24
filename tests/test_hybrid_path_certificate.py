import importlib
import sys
import unittest
from pathlib import Path

from starter_kit import adapter
from starter_kit.loomq.hybrid_paths import verify_hybrid_path_certificate


STARTER_KIT_ROOT = Path(__file__).resolve().parents[1] / "starter_kit"
if str(STARTER_KIT_ROOT) not in sys.path:
    sys.path.insert(0, str(STARTER_KIT_ROOT))
direct_adapter = importlib.import_module("adapter")


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


def groups_by_id(certificate):
    return {item["path_id"]: item for item in certificate["path_groups"]}


class HybridPathCertificateTests(unittest.TestCase):
    def test_dual_import_adapter_entry_points_share_the_same_certificate(self):
        packaged = adapter.certify_hybrid_paths(HYBRID)
        direct = direct_adapter.certify_hybrid_paths(HYBRID)

        self.assertEqual(packaged, direct)
        self.assertEqual(adapter.hybrid_path_certificate(HYBRID), packaged)
        self.assertEqual(direct_adapter.hybrid_path_certificate(HYBRID), direct)

    def test_reports_exact_path_probabilities_and_exhaustive_unreachable_outcomes(self):
        certificate = adapter.hybrid_path_certificate(HYBRID)
        path_groups = groups_by_id(certificate)

        self.assertEqual(certificate["schema_version"], "loomq-hybrid-path-certificate-v1")
        self.assertEqual(certificate["limits"]["max_outcomes"], 256)
        self.assertEqual(
            [item["outcome"] for item in certificate["outcomes"]],
            ["00", "01", "10", "11"],
        )
        self.assertEqual(certificate["unreachable_outcomes"], ["01", "10"])
        self.assertEqual(certificate["dead_path_ids"], [])
        self.assertEqual(path_groups["if1:F"]["total_probability"], 0.5)
        self.assertEqual(path_groups["if1:F"]["reachable_outcomes"], ["00"])
        self.assertEqual(path_groups["if1:T"]["total_probability"], 0.5)
        self.assertEqual(path_groups["if1:T"]["reachable_outcomes"], ["11"])
        self.assertTrue(verify_hybrid_path_certificate(HYBRID, certificate)["valid"])

    def test_records_zero_probability_outcomes_and_dead_paths(self):
        certificate = adapter.certify_hybrid_paths(DETERMINISTIC, max_outcomes=2)
        path_groups = groups_by_id(certificate)

        self.assertEqual(certificate["limits"]["max_outcomes"], 2)
        self.assertEqual(certificate["unreachable_outcomes"], ["0"])
        self.assertEqual(certificate["dead_path_ids"], ["if1:F"])
        self.assertEqual(path_groups["if1:T"]["total_probability"], 1.0)
        self.assertEqual(path_groups["if1:F"]["total_probability"], 0.0)


if __name__ == "__main__":
    unittest.main()
