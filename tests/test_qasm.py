import math
import unittest

from starter_kit.loomq.qasm import Gate, Measurement, QASMError, parse_qasm


class QASMParserTests(unittest.TestCase):
    def test_parses_comments_parameters_and_measurements(self):
        circuit = parse_qasm(
            """OPENQASM 2.0;
            include "qelib1.inc";
            // Registers may have different names.
            qreg data[3];
            creg readout[3];
            h data[0];
            rz(-pi/2) data[1];
            cx data[0], data[2];
            measure data -> readout;
            """
        )

        self.assertEqual(circuit.num_qubits, 3)
        self.assertEqual(circuit.num_clbits, 3)
        self.assertEqual(circuit.operations[0], Gate("h", (0,)))
        self.assertEqual(circuit.operations[1].name, "rz")
        self.assertAlmostEqual(circuit.operations[1].parameter, -math.pi / 2)
        self.assertEqual(circuit.operations[2], Gate("cx", (0, 2)))
        self.assertEqual(
            circuit.operations[3:],
            [Measurement(0, 0), Measurement(1, 1), Measurement(2, 2)],
        )

    def test_expands_register_wide_gate_operands(self):
        circuit = parse_qasm(
            """OPENQASM 2.0;
            include "qelib1.inc";
            qreg left[2]; qreg right[2]; creg c[4];
            h left;
            cx left,right;
            """
        )

        self.assertEqual(
            circuit.operations,
            [
                Gate("h", (0,)),
                Gate("h", (1,)),
                Gate("cx", (0, 2)),
                Gate("cx", (1, 3)),
            ],
        )

    def test_emits_canonical_qasm2_after_flattening_registers(self):
        circuit = parse_qasm(
            """OPENQASM 2.0; include "qelib1.inc";
            qreg a[1]; qreg b[1]; creg out[2];
            h a[0]; cu1(pi/4) a[0],b[0]; measure b[0] -> out[1];
            """
        )

        self.assertEqual(
            circuit.to_qasm2(),
            """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cu1(0.7853981633974483) q[0],q[1];
measure q[1] -> c[1];
""",
        )

    def test_rejects_unsupported_gate_instead_of_silently_dropping_it(self):
        with self.assertRaisesRegex(QASMError, "unsupported gate.*z"):
            parse_qasm(
                """OPENQASM 2.0; include "qelib1.inc";
                qreg q[1]; creg c[1]; z q[0];
                """
            )

    def test_rejects_out_of_range_operand(self):
        with self.assertRaisesRegex(QASMError, "out of range"):
            parse_qasm(
                """OPENQASM 2.0; include "qelib1.inc";
                qreg q[1]; creg c[1]; x q[1];
                """
            )

    def test_rejects_register_size_mismatch(self):
        with self.assertRaisesRegex(QASMError, "register sizes"):
            parse_qasm(
                """OPENQASM 2.0; include "qelib1.inc";
                qreg a[1]; qreg b[2]; creg c[1]; cx a,b;
                """
            )


if __name__ == "__main__":
    unittest.main()
