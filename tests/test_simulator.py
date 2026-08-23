import cmath
import math
import unittest

from starter_kit import adapter
from starter_kit.evaluator import validate_schema
from starter_kit.loomq.qasm import parse_qasm
from starter_kit.loomq.simulator import probabilities, simulate_statevector


def circuit(body: str, qubits: int = 1) -> str:
    return f"""OPENQASM 2.0;
include "qelib1.inc";
qreg q[{qubits}];
creg c[{qubits}];
{body}
"""


class StateVectorTests(unittest.TestCase):
    def assertVectorAlmostEqual(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for left, right in zip(actual, expected):
            self.assertAlmostEqual(left.real, right.real, places=12)
            self.assertAlmostEqual(left.imag, right.imag, places=12)

    def test_single_qubit_gate_matrices_match_qasm_semantics(self):
        root = 1 / math.sqrt(2)
        cases = {
            "h q[0];": [root, root],
            "x q[0];": [0, 1],
            "x q[0]; s q[0];": [0, 1j],
            "x q[0]; sdg q[0];": [0, -1j],
            "x q[0]; t q[0];": [0, cmath.exp(1j * math.pi / 4)],
            "x q[0]; tdg q[0];": [0, cmath.exp(-1j * math.pi / 4)],
            "rz(pi) q[0];": [-1j, 0],
            "ry(pi) q[0];": [0, 1],
        }
        for body, expected in cases.items():
            with self.subTest(body=body):
                state = simulate_statevector(parse_qasm(circuit(body)))
                self.assertVectorAlmostEqual(state, expected)

    def test_multi_qubit_gate_semantics(self):
        cases = {
            "x q[0]; cx q[0],q[1];": (2, 3, 1),
            "x q[0]; x q[1]; cu1(pi/2) q[0],q[1];": (2, 3, 1j),
            "x q[0]; swap q[0],q[1];": (2, 2, 1),
            "x q[0]; x q[1]; ccx q[0],q[1],q[2];": (3, 7, 1),
        }
        for body, (qubits, expected_index, expected_value) in cases.items():
            with self.subTest(body=body):
                state = simulate_statevector(parse_qasm(circuit(body, qubits)))
                nonzero = [(index, value) for index, value in enumerate(state) if abs(value) > 1e-12]
                self.assertEqual([index for index, _ in nonzero], [expected_index])
                self.assertAlmostEqual(nonzero[0][1].real, complex(expected_value).real, places=12)
                self.assertAlmostEqual(nonzero[0][1].imag, complex(expected_value).imag, places=12)

    def test_measurements_map_to_little_endian_classical_keys(self):
        source = circuit(
            "x q[0]; measure q[0] -> c[1]; measure q[1] -> c[0];", qubits=2
        )
        observed = probabilities(parse_qasm(source))

        self.assertEqual(observed, {"10": 1.0})


class AdapterRunTests(unittest.TestCase):
    BELL = circuit(
        "h q[0]; cx q[0],q[1]; measure q[0] -> c[0]; measure q[1] -> c[1];",
        qubits=2,
    )

    def test_each_official_target_returns_valid_exact_counts(self):
        for target in adapter.SUPPORTED_TARGETS:
            with self.subTest(target=target):
                result = adapter.run(self.BELL, target, 8192)
                valid, reason = validate_schema(result)
                self.assertTrue(valid, reason)
                self.assertEqual(result["counts"], {"00": 4096, "11": 4096})
                self.assertNotIn("mock", result["job_id"].lower())
                self.assertEqual(result["meta"]["engine"], "loomq-statevector")

    def test_counts_always_sum_to_non_divisible_shot_count(self):
        result = adapter.run(self.BELL, "braket", 7)

        self.assertEqual(sum(result["counts"].values()), 7)
        self.assertEqual(result["counts"], {"00": 4, "11": 3})

    def test_rejects_non_positive_shots(self):
        with self.assertRaisesRegex(ValueError, "positive integer"):
            adapter.run(self.BELL, "spinq", 0)


if __name__ == "__main__":
    unittest.main()
