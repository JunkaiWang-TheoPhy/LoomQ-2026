import unittest
import json
from unittest.mock import patch

import adapter
import loomq.prooftrace as prooftrace_module
from loomq.native_ir import parse_native_ir
from loomq.prooftrace import optimize_circuit
from loomq.qasm import Gate, Measurement, parse_qasm
from loomq.semantic_equivalence import verify_semantic_equivalence_certificate


REDUNDANT_BELL = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
h q[0];
h q[0];
cx q[0],q[1];
measure q -> c;
'''

PARAMETER_REDUNDANCY = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
rz(0.25) q[0];
rz(0.5) q[0];
ry(0.4) q[1];
ry(-0.4) q[1];
s q[0];
sdg q[0];
cu1(0.2) q[0],q[1];
cu1(0.3) q[0],q[1];
measure q -> c;
'''

PHASE_SENSITIVE_QASM = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
measure q[0] -> c[0];
'''


class ProofTraceTests(unittest.TestCase):
    def test_self_inverse_pair_is_removed_with_source_lineage(self):
        native, certificate = adapter.transpile_with_proof(REDUNDANT_BELL, "originq")

        optimized = parse_native_ir(native, "originq")
        gates = [operation for operation in optimized.operations if isinstance(operation, Gate)]
        self.assertEqual([gate.name for gate in gates], ["h", "cx"])
        self.assertEqual(certificate["schema_version"], "loomq-prooftrace-v1")
        self.assertEqual(certificate["equivalence"]["method"], "verified-local-rewrites-v1")
        self.assertTrue(certificate["equivalence"]["verified"])
        self.assertEqual(certificate["metrics"]["source"]["gate_count"], 4)
        self.assertEqual(certificate["metrics"]["optimized"]["gate_count"], 2)
        self.assertEqual(certificate["rewrites"][0]["rule"], "cancel-self-inverse")
        gate_lineage = [item for item in certificate["lineage"] if item["kind"] == "gate"]
        self.assertEqual(gate_lineage[0]["source_operation_indices"], [2])
        self.assertEqual(gate_lineage[1]["source_operation_indices"], [3])

    def test_inverse_and_parameter_rewrites_are_named_and_semantics_preserving(self):
        circuit = parse_qasm(PARAMETER_REDUNDANCY)

        optimized, rewrites, lineage = optimize_circuit(circuit)

        gates = [operation for operation in optimized.operations if isinstance(operation, Gate)]
        self.assertEqual([(gate.name, gate.parameter) for gate in gates], [("rz", 0.75), ("cu1", 0.5)])
        self.assertEqual(
            [rewrite["rule"] for rewrite in rewrites],
            ["merge-rotations", "cancel-zero-rotation", "cancel-inverse", "merge-rotations"],
        )
        self.assertEqual(lineage[0], [0, 1])
        self.assertEqual(lineage[1], [6, 7])
        self.assertEqual(lineage[2:], [[8], [9]])

    def test_optimizer_never_rewrites_across_a_measurement(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
x q[0];
measure q[0] -> c[0];
x q[0];
'''

        optimized, rewrites, lineage = optimize_circuit(parse_qasm(source))

        self.assertEqual(rewrites, [])
        self.assertEqual(lineage, [[0], [1], [2]])
        self.assertIsInstance(optimized.operations[1], Measurement)

    def test_tiny_nonzero_rotation_is_not_claimed_as_an_exact_identity(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1]; creg c[1];
rz(1e-13) q[0]; rz(0.0) q[0];
measure q -> c;
'''

        optimized, rewrites, _lineage = optimize_circuit(parse_qasm(source))

        gates = [operation for operation in optimized.operations if isinstance(operation, Gate)]
        self.assertEqual(len(gates), 1)
        self.assertEqual(gates[0].parameter, 1e-13)
        self.assertEqual(rewrites[0]["rule"], "merge-rotations")

    def test_rotation_merge_skips_non_finite_parameter_sums(self):
        source = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1]; creg c[1];
rz(1e308) q[0]; rz(1e308) q[0];
measure q -> c;
'''

        optimized, rewrites, lineage = optimize_circuit(parse_qasm(source))

        gates = [operation for operation in optimized.operations if isinstance(operation, Gate)]
        self.assertEqual(len(gates), 2)
        self.assertEqual(rewrites, [])
        self.assertEqual(lineage, [[0], [1], [2]])

    def test_certificate_is_deterministic_and_verifies_every_target(self):
        first = adapter.prooftrace(REDUNDANT_BELL, "spinq")
        second = adapter.prooftrace(REDUNDANT_BELL, "spinq")

        self.assertEqual(first, second)
        json.dumps(first, sort_keys=True)
        self.assertIn("whole_circuit_validation", first)
        self.assertTrue(first["whole_circuit_validation"]["verified"])
        self.assertTrue(first["whole_circuit_validation"]["one_global_phase"]["consistent"])
        self.assertEqual(first["whole_circuit_validation"]["basis_columns_checked"], 4)
        self.assertEqual(
            verify_semantic_equivalence_certificate(
                parse_qasm(REDUNDANT_BELL),
                optimize_circuit(parse_qasm(REDUNDANT_BELL))[0],
                first["whole_circuit_validation"],
            )["valid"],
            True,
        )
        self.assertEqual(set(first["portability"]), set(adapter.SUPPORTED_TARGETS))
        for target, report in first["portability"].items():
            with self.subTest(target=target):
                self.assertTrue(report["roundtrip_verified"])
                self.assertRegex(report["native_ir_sha256"], r"^[0-9a-f]{64}$")
                self.assertIn("whole_circuit_validation", report)
                self.assertTrue(report["whole_circuit_validation"]["verified"])
                self.assertTrue(report["whole_circuit_validation"]["one_global_phase"]["consistent"])
        self.assertRegex(first["source_sha256"], r"^[0-9a-f]{64}$")
        self.assertRegex(first["optimized_qasm_sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(first["selected_target"], "spinq")

    def test_plain_transpile_preserves_source_while_proof_api_returns_optimized_ir(self):
        for target in adapter.SUPPORTED_TARGETS:
            with self.subTest(target=target):
                native, certificate = adapter.transpile_with_proof(REDUNDANT_BELL, target)
                plain = adapter.transpile(REDUNDANT_BELL, target)
                plain_gates = [
                    operation
                    for operation in parse_native_ir(plain, target).operations
                    if isinstance(operation, Gate)
                ]
                proof_gates = [
                    operation
                    for operation in parse_native_ir(native, target).operations
                    if isinstance(operation, Gate)
                ]
                self.assertEqual([gate.name for gate in plain_gates], ["h", "h", "h", "cx"])
                self.assertEqual([gate.name for gate in proof_gates], ["h", "cx"])
                self.assertEqual(certificate["selected_target"], target)
                self.assertEqual(
                    certificate["portability"][target]["native_ir_sha256"],
                    __import__("hashlib").sha256(native.encode()).hexdigest(),
                )

    def test_plain_transpile_is_isolated_from_unrequested_backend_failures(self):
        real_emit = prooftrace_module.emit

        def fail_unrequested(circuit, target):
            if target == "originq":
                raise RuntimeError("unrequested backend failed")
            return real_emit(circuit, target)

        with patch("loomq.prooftrace.emit", side_effect=fail_unrequested):
            native = adapter.transpile(REDUNDANT_BELL, "spinq")

        self.assertIn("OPENQASM 2.0", native)

    def test_phase_mutation_is_rejected_even_when_z_basis_probabilities_match(self):
        source = parse_qasm(PHASE_SENSITIVE_QASM)
        optimized, _rewrites, _lineage = optimize_circuit(source)
        phase_mutated_native = '''OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
s q[0];
measure q[0] -> c[0];
'''

        report = prooftrace_module.assess_portability(optimized, phase_mutated_native, "spinq")

        self.assertFalse(report["roundtrip_verified"])
        self.assertFalse(report["whole_circuit_validation"]["verified"])
        self.assertFalse(report["whole_circuit_validation"]["one_global_phase"]["consistent"])
        self.assertEqual(
            report["whole_circuit_validation"]["reason"],
            "no single global phase aligns every matrix entry",
        )
        self.assertIsNotNone(report["whole_circuit_validation"]["operational_counterexample"])


if __name__ == "__main__":
    unittest.main()
