import copy
import json
import unittest
from unittest import mock

import loomq.hybrid_paths as hybrid_paths_module
from loomq.hybrid_paths import (
    certify_hybrid_paths,
    measurement_branch_probabilities,
    verify_hybrid_path_certificate,
)
from loomq.qasm import parse_qasm


MID_CIRCUIT_COLLAPSE = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1];
measure q[0] -> c[0];
x q[0];
"""

BELL = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""

DETERMINISTIC_BRANCH = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1];
measure q[0] -> c[0];
classical {
  if (c[0] == 1) { r1 = 9; } else { r1 = 4; }
}
"""

NESTED_UNIFORM_BRANCH = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
h q[1];
measure q -> c;
classical {
  if (c[0] == 1) {
    if (c[1] != 0) { r4 = 100; } else { r4 = 70; }
  } else {
    r4 = 10;
  }
}
"""

SHARED_PATH_DIFFERENT_REGISTERS = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[1];
measure q -> c;
classical {
  if (c[0] == 0) { r1 = 5; } else { r1 = 9; }
  r2 = c[1];
}
"""

HIGH_QUBIT_MID_CIRCUIT_COLLAPSE = """OPENQASM 2.0; include "qelib1.inc";
qreg q[21]; creg c[1];
h q[20];
measure q[20] -> c[0];
h q[20];
measure q[20] -> c[0];
"""

HIGH_QUBIT_SPARSE_BRANCH = """OPENQASM 2.0; include "qelib1.inc";
qreg q[21]; creg c[1];
h q[20];
measure q[20] -> c[0];
h q[20];
measure q[20] -> c[0];
classical {
  if (c[0] == 1) { r1 = 9; } else { r1 = 4; }
}
"""

HIGH_QUBIT_SPARSE_OVERFLOW = """OPENQASM 2.0; include "qelib1.inc";
qreg q[21]; creg c[1];
h q[0];
h q[1];
h q[2];
measure q[20] -> c[0];
"""


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def outcomes_by_key(certificate):
    return {item["outcome"]: item for item in certificate["outcomes"]}


def path_groups_by_id(certificate):
    return {item["path_id"]: item for item in certificate["path_groups"]}


def high_qubit_collapse_qasm(num_qubits):
    high = num_qubits - 1
    return f"""OPENQASM 2.0; include "qelib1.inc";
qreg q[{num_qubits}]; creg c[1];
h q[{high}];
measure q[{high}] -> c[0];
h q[{high}];
measure q[{high}] -> c[0];
"""


class MeasurementBranchProbabilitiesTests(unittest.TestCase):
    def test_mid_circuit_measurement_collapses_at_the_measurement_point(self):
        self.assertEqual(
            measurement_branch_probabilities(parse_qasm(MID_CIRCUIT_COLLAPSE)),
            {"0": 1.0},
        )

    def test_terminal_bell_measurement_reports_exact_literals(self):
        self.assertEqual(
            measurement_branch_probabilities(parse_qasm(BELL)),
            {"00": 0.5, "11": 0.5},
        )

    def test_measurement_branching_rejects_live_history_overflow(self):
        with self.assertRaisesRegex(ValueError, "max_branches"):
            measurement_branch_probabilities(parse_qasm(BELL), max_branches=1)

    def test_sparse_high_qubit_measurement_keeps_exact_mid_circuit_collapse(self):
        self.assertEqual(
            measurement_branch_probabilities(parse_qasm(HIGH_QUBIT_MID_CIRCUIT_COLLAPSE)),
            {"0": 0.5, "1": 0.5},
        )

    def test_sparse_high_qubit_branching_fails_closed_at_populated_state_limit(self):
        with mock.patch.object(hybrid_paths_module, "MAX_SPARSE_STATES", 4):
            with self.assertRaisesRegex(ValueError, "local sparse simulation exceeds"):
                measurement_branch_probabilities(parse_qasm(HIGH_QUBIT_SPARSE_OVERFLOW))

    def test_dense_and_sparse_paths_match_across_the_20_qubit_boundary(self):
        dense = measurement_branch_probabilities(parse_qasm(high_qubit_collapse_qasm(20)))
        sparse = measurement_branch_probabilities(parse_qasm(high_qubit_collapse_qasm(21)))
        self.assertEqual(dense, sparse)


class HybridPathCertificateTests(unittest.TestCase):
    def test_certificate_replays_zero_probability_outcomes_and_marks_dead_paths(self):
        certificate = certify_hybrid_paths(DETERMINISTIC_BRANCH)
        outcomes = outcomes_by_key(certificate)
        path_groups = path_groups_by_id(certificate)

        self.assertEqual(certificate["schema_version"], "loomq-hybrid-path-certificate-v1")
        self.assertEqual(certificate["bit_order"], "Outcome keys are ordered c[n-1]...c[0].")
        self.assertEqual([item["outcome"] for item in certificate["outcomes"]], ["0", "1"])
        self.assertEqual(certificate["unreachable_outcomes"], ["1"])
        self.assertEqual(certificate["dead_path_ids"], ["if1:T"])

        self.assertEqual(outcomes["0"]["probability"], 1.0)
        self.assertTrue(outcomes["0"]["reachable"])
        self.assertEqual(outcomes["0"]["path_id"], "if1:F")
        self.assertEqual(outcomes["0"]["branch_path"], "if1:F")
        self.assertEqual(outcomes["0"]["final_registers"], {"x1": 4})

        self.assertEqual(outcomes["1"]["probability"], 0.0)
        self.assertFalse(outcomes["1"]["reachable"])
        self.assertEqual(outcomes["1"]["path_id"], "if1:T")
        self.assertEqual(outcomes["1"]["branch_path"], "if1:T")
        self.assertEqual(outcomes["1"]["final_registers"], {"x1": 9})

        self.assertEqual(path_groups["if1:F"]["total_probability"], 1.0)
        self.assertEqual(path_groups["if1:F"]["outcomes"], ["0"])
        self.assertEqual(path_groups["if1:F"]["reachable_outcomes"], ["0"])
        self.assertEqual(len(path_groups["if1:F"]["final_register_sha256s"]), 1)

        self.assertEqual(path_groups["if1:T"]["total_probability"], 0.0)
        self.assertEqual(path_groups["if1:T"]["outcomes"], ["1"])
        self.assertEqual(path_groups["if1:T"]["reachable_outcomes"], [])
        self.assertEqual(len(path_groups["if1:T"]["final_register_sha256s"]), 1)

    def test_certificate_exhaustively_replays_nested_uniform_branches(self):
        certificate = certify_hybrid_paths(NESTED_UNIFORM_BRANCH)
        outcomes = outcomes_by_key(certificate)

        self.assertEqual([item["outcome"] for item in certificate["outcomes"]], ["00", "01", "10", "11"])
        self.assertEqual(
            {key: outcomes[key]["probability"] for key in ["00", "01", "10", "11"]},
            {"00": 0.25, "01": 0.25, "10": 0.25, "11": 0.25},
        )
        self.assertEqual(outcomes["10"]["path_id"], "if1:F")
        self.assertEqual(outcomes["10"]["branch_path"], "if1:F")
        self.assertEqual(outcomes["10"]["final_registers"], {"x4": 10})
        self.assertEqual(outcomes["01"]["path_id"], "if1:T -> if2:F")
        self.assertEqual(outcomes["01"]["final_registers"], {"x4": 70})
        self.assertEqual(outcomes["11"]["path_id"], "if1:T -> if2:T")
        self.assertEqual(outcomes["11"]["final_registers"], {"x4": 100})

    def test_path_groups_keep_shared_branch_paths_but_distinct_final_registers(self):
        certificate = certify_hybrid_paths(SHARED_PATH_DIFFERENT_REGISTERS)
        outcomes = outcomes_by_key(certificate)
        path_groups = path_groups_by_id(certificate)

        self.assertEqual(outcomes["00"]["path_id"], "if1:T")
        self.assertEqual(outcomes["10"]["path_id"], "if1:T")
        self.assertEqual(outcomes["00"]["final_registers"], {"x1": 5})
        self.assertEqual(outcomes["10"]["final_registers"], {"x1": 5, "x2": 1})
        self.assertEqual(path_groups["if1:T"]["outcomes"], ["00", "10"])
        self.assertEqual(path_groups["if1:T"]["reachable_outcomes"], ["00", "10"])
        self.assertEqual(len(path_groups["if1:T"]["final_register_sha256s"]), 2)

    def test_certificate_supports_sparse_high_qubit_branches_without_dense_statevector(self):
        certificate = certify_hybrid_paths(HIGH_QUBIT_SPARSE_BRANCH)
        outcomes = outcomes_by_key(certificate)

        self.assertEqual(certificate["scope"], {"num_qubits": 21, "num_clbits": 1})
        self.assertEqual(
            {key: outcomes[key]["probability"] for key in ["0", "1"]},
            {"0": 0.5, "1": 0.5},
        )
        self.assertEqual(outcomes["0"]["final_registers"], {"x1": 4})
        self.assertEqual(outcomes["1"]["final_registers"], {"x1": 9})

        verified = verify_hybrid_path_certificate(HIGH_QUBIT_SPARSE_BRANCH, certificate)
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["reason"], "ok")


class HybridPathVerificationTests(unittest.TestCase):
    def test_verifier_fails_closed_when_stored_bound_cannot_recompute(self):
        certificate = certify_hybrid_paths(DETERMINISTIC_BRANCH)
        certificate["limits"]["max_outcomes"] = 1

        result = verify_hybrid_path_certificate(DETERMINISTIC_BRANCH, certificate)

        self.assertFalse(result["valid"])
        self.assertIn("recomputation failed", result["reason"])

    def test_certificates_are_deterministic_and_verification_recomputes_semantics(self):
        certificate = certify_hybrid_paths(SHARED_PATH_DIFFERENT_REGISTERS)
        repeated = certify_hybrid_paths(SHARED_PATH_DIFFERENT_REGISTERS)

        self.assertEqual(canonical_json(certificate), canonical_json(repeated))

        verified = verify_hybrid_path_certificate(
            SHARED_PATH_DIFFERENT_REGISTERS, certificate
        )
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["reason"], "ok")
        self.assertEqual(verified["certificate_sha256"], verified["recomputed_sha256"])

        probability_tamper = copy.deepcopy(certificate)
        probability_tamper["outcomes"][0]["probability"] = 0.75
        result = verify_hybrid_path_certificate(
            SHARED_PATH_DIFFERENT_REGISTERS, probability_tamper
        )
        self.assertFalse(result["valid"])
        self.assertIn("semantic mismatch", result["reason"])

        branch_tamper = copy.deepcopy(certificate)
        branch_tamper["outcomes"][0]["branch_events"][0]["source_condition_true"] = (
            not branch_tamper["outcomes"][0]["branch_events"][0]["source_condition_true"]
        )
        result = verify_hybrid_path_certificate(
            SHARED_PATH_DIFFERENT_REGISTERS, branch_tamper
        )
        self.assertFalse(result["valid"])
        self.assertIn("semantic mismatch", result["reason"])

        register_tamper = copy.deepcopy(certificate)
        register_tamper["outcomes"][0]["final_registers"]["x1"] += 1
        result = verify_hybrid_path_certificate(
            SHARED_PATH_DIFFERENT_REGISTERS, register_tamper
        )
        self.assertFalse(result["valid"])
        self.assertIn("semantic mismatch", result["reason"])

        source_tamper = copy.deepcopy(certificate)
        source_tamper["integrity"]["body_sha256"] = certificate["integrity"]["body_sha256"]
        changed_source = SHARED_PATH_DIFFERENT_REGISTERS.replace("r1 = 5", "r1 = 6")
        result = verify_hybrid_path_certificate(changed_source, source_tamper)
        self.assertFalse(result["valid"])
        self.assertIn("source mismatch", result["reason"])


if __name__ == "__main__":
    unittest.main()
