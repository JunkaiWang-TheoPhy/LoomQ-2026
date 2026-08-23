import unittest

from starter_kit import adapter


ALL_GATES = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0]; x q[0]; s q[0]; sdg q[0]; t q[0]; tdg q[0];
rz(pi/2) q[0]; ry(-pi/4) q[1];
cx q[0],q[1]; cu1(pi/8) q[0],q[1]; swap q[0],q[1]; ccx q[0],q[1],q[2];
measure q -> c;
"""


class TargetEmitterTests(unittest.TestCase):
    def test_spinq_is_complete_canonical_qasm2(self):
        output = adapter.transpile(ALL_GATES, "spinq")

        self.assertTrue(output.startswith('OPENQASM 2.0;\ninclude "qelib1.inc";'))
        self.assertIn("cu1(0.39269908169872414) q[0],q[1];", output)
        self.assertIn("ccx q[0],q[1],q[2];", output)
        self.assertEqual(output.count("measure "), 3)

    def test_braket_is_complete_openqasm3_with_standard_gate_names(self):
        output = adapter.transpile(ALL_GATES, "braket")

        self.assertTrue(output.startswith('OPENQASM 3.0;\ninclude "stdgates.inc";'))
        self.assertIn("qubit[3] q;", output)
        self.assertIn("bit[3] c;", output)
        self.assertIn("cp(0.39269908169872414) q[0],q[1];", output)
        self.assertIn("c[2] = measure q[2];", output)
        self.assertNotIn("qreg", output)

    def test_originq_is_complete_originir(self):
        output = adapter.transpile(ALL_GATES, "originq")

        self.assertTrue(output.startswith("QINIT 3\nCREG 3\n"))
        self.assertIn("SDAG q[0]", output)
        self.assertIn("RZ q[0],(1.5707963267948966)", output)
        self.assertIn("CR q[0],q[1],(0.39269908169872414)", output)
        self.assertIn("TOFFOLI q[0],q[1],q[2]", output)
        self.assertIn("MEASURE q[2],c[2]", output)

    def test_unknown_target_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported target"):
            adapter.transpile(ALL_GATES, "quafu")


if __name__ == "__main__":
    unittest.main()
