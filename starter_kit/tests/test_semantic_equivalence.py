import copy
import hashlib
import json
import math
import unittest

from starter_kit.loomq.qasm import Circuit, Gate, Measurement
from starter_kit.loomq.semantic_equivalence import (
    compare_circuit_semantics,
    verify_semantic_equivalence_certificate,
)


def canonical_json(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def measured_circuit(num_qubits, gates=(), measurements=None):
    if measurements is None:
        measurements = [Measurement(index, index) for index in range(num_qubits)]
    return Circuit(num_qubits, num_qubits, [*gates, *measurements])


class CompareCircuitSemanticsTests(unittest.TestCase):
    def test_identical_circuits_produce_a_verified_certificate(self):
        bell = measured_circuit(
            2,
            gates=(Gate("h", (0,)), Gate("cx", (0, 1))),
        )

        report = compare_circuit_semantics(bell, bell)

        self.assertEqual(report["schema_version"], "loomq-semantic-equivalence-v1")
        self.assertTrue(report["verified"])
        self.assertEqual(report["method"], "complete-unitary-column-comparison-v1")
        self.assertEqual(report["scope"], {"max_qubits": 8, "tolerance": 1e-12})
        self.assertEqual(
            report["dimensions"],
            {"num_qubits": 2, "num_clbits": 2, "unitary_dimension": 4},
        )
        self.assertTrue(report["identical_measurement_map"])
        self.assertEqual(
            report["reference_measurements"],
            [{"qubit": 0, "clbit": 0}, {"qubit": 1, "clbit": 1}],
        )
        self.assertEqual(report["candidate_measurements"], report["reference_measurements"])
        self.assertEqual(report["one_global_phase"]["consistent"], True)
        self.assertEqual(report["basis_columns_checked"], 4)
        self.assertEqual(report["amplitudes_checked"], 16)
        self.assertEqual(report["maximum_absolute_error"], 0.0)
        self.assertIsNone(report["operational_counterexample"])

        verified = verify_semantic_equivalence_certificate(bell, bell, report)
        self.assertTrue(verified["valid"])
        self.assertEqual(verified["reason"], "ok")

    def test_single_global_phase_is_accepted(self):
        reference = measured_circuit(1)
        candidate = measured_circuit(1, gates=(Gate("rz", (0,), 2 * math.pi),))

        report = compare_circuit_semantics(reference, candidate)

        self.assertTrue(report["verified"])
        self.assertTrue(report["one_global_phase"]["consistent"])
        self.assertAlmostEqual(report["one_global_phase"]["imag"], 0.0, delta=1e-12)
        self.assertAlmostEqual(abs(report["one_global_phase"]["real"]), 1.0, delta=1e-12)
        self.assertIsNone(report["operational_counterexample"])

    def test_relative_column_phase_rejection_reports_a_two_basis_counterexample(self):
        reference = measured_circuit(1)
        candidate = measured_circuit(1, gates=(Gate("s", (0,)), Gate("s", (0,))))

        report = compare_circuit_semantics(reference, candidate)

        self.assertFalse(report["verified"])
        self.assertTrue(report["identical_measurement_map"])
        self.assertFalse(report["one_global_phase"]["consistent"])
        self.assertGreater(report["maximum_absolute_error"], 0.0)
        self.assertEqual(report["failing_entry"], {"row": 1, "column": 1})
        self.assertEqual(report["operational_counterexample"]["state_family"], "plus")
        self.assertEqual(report["operational_counterexample"]["basis_pair"], [0, 1])
        self.assertGreater(report["operational_counterexample"]["state_distance"], 0.0)

    def test_measurement_map_rejection_is_reported_without_unitary_claims(self):
        reference = measured_circuit(2)
        candidate = measured_circuit(
            2,
            measurements=(Measurement(0, 1), Measurement(1, 0)),
        )

        report = compare_circuit_semantics(reference, candidate)

        self.assertFalse(report["verified"])
        self.assertFalse(report["identical_measurement_map"])
        self.assertEqual(report["reason"], "measurement mappings differ")
        self.assertEqual(report["basis_columns_checked"], 0)
        self.assertEqual(report["amplitudes_checked"], 0)
        self.assertIsNone(report["operational_counterexample"])

    def test_register_mismatch_returns_without_matrix_enumeration(self):
        reference = measured_circuit(1)
        candidate = measured_circuit(2)

        report = compare_circuit_semantics(reference, candidate)

        self.assertFalse(report["verified"])
        self.assertEqual(report["reason"], "register declarations differ")
        self.assertEqual(report["basis_columns_checked"], 0)
        self.assertEqual(report["amplitudes_checked"], 0)

    def test_gates_after_measurement_are_rejected(self):
        invalid = Circuit(1, 1, [Measurement(0, 0), Gate("x", (0,))])

        with self.assertRaisesRegex(ValueError, "mid-circuit measurement"):
            compare_circuit_semantics(invalid, measured_circuit(1))

    def test_default_bound_rejects_nine_qubit_circuits(self):
        large = measured_circuit(9)

        with self.assertRaisesRegex(ValueError, "at most 8 qubits"):
            compare_circuit_semantics(large, large)

    def test_max_qubits_parameter_cannot_widen_beyond_eight(self):
        bell = measured_circuit(2)

        with self.assertRaisesRegex(ValueError, "at most 8 qubits"):
            compare_circuit_semantics(bell, bell, max_qubits=9)

    def test_certificates_are_deterministic_and_hash_their_canonical_body(self):
        bell = measured_circuit(
            2,
            gates=(Gate("h", (0,)), Gate("cx", (0, 1))),
        )

        report = compare_circuit_semantics(bell, bell)
        repeated = compare_circuit_semantics(bell, bell)

        self.assertEqual(canonical_json(report), canonical_json(repeated))
        body = {key: value for key, value in report.items() if key != "integrity"}
        expected_hash = hashlib.sha256(canonical_json(body).encode("utf-8")).hexdigest()
        self.assertEqual(report["integrity"]["body_sha256"], expected_hash)

    def test_verifier_rejects_tampered_certificates_and_semantic_differences(self):
        reference = measured_circuit(1)
        certificate = compare_circuit_semantics(reference, reference)

        tampered = copy.deepcopy(certificate)
        tampered["maximum_absolute_error"] = 0.25
        result = verify_semantic_equivalence_certificate(reference, reference, tampered)
        self.assertFalse(result["valid"])
        self.assertIn("integrity", result["reason"])

        malformed = copy.deepcopy(certificate)
        malformed["scope"]["max_qubits"] = "8"
        result = verify_semantic_equivalence_certificate(reference, reference, malformed)
        self.assertFalse(result["valid"])
        self.assertIn("invalid schema", result["reason"])

        widened_scope = copy.deepcopy(certificate)
        widened_scope["scope"]["max_qubits"] = 9
        widened_scope["integrity"]["body_sha256"] = hashlib.sha256(
            canonical_json(
                {key: value for key, value in widened_scope.items() if key != "integrity"}
            ).encode("utf-8")
        ).hexdigest()
        result = verify_semantic_equivalence_certificate(reference, reference, widened_scope)
        self.assertFalse(result["valid"])
        self.assertIn("invalid schema", result["reason"])

        different_candidate = measured_circuit(1, gates=(Gate("x", (0,)),))
        result = verify_semantic_equivalence_certificate(
            reference,
            different_candidate,
            certificate,
        )
        self.assertFalse(result["valid"])
        self.assertIn("semantic mismatch", result["reason"])


if __name__ == "__main__":
    unittest.main()
