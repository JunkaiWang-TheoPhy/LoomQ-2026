import unittest

import adapter
from loomq.qasm import Circuit, Gate, Measurement
from loomq.quantum_riscv import encode_circuit


HYBRID = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
classical {
  r1 = 10;
  if (c[1] == 1) { r3 = r1 + 2; } else { r3 = r1 - 8; }
}
"""

NESTED = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2]; measure q -> c;
classical {
  if (c[0] == 1) {
    if (c[1] != 0) { r4 = 100; } else { r4 = 70; }
  } else {
    r4 = 10;
  }
}
"""

TEMPORARY_PROVENANCE = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2]; measure q -> c;
classical {
  if ((c[0] + 1) == (c[1] + 1)) { r5 = 9; } else { r5 = 4; }
}
"""

COMPILE_FIXTURE = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2]; measure q -> c;
classical {
  r1 = 5;
  if (c[0] == c[1]) { r3 = r1 + 7; } else { r3 = r1 - 2; }
}
"""

EXPECTED_ASSEMBLY = """# LoomQ Hybrid-QASM classical control
li x1, 5
addi x31, x10, 0
addi x30, x11, 0
bne x31, x30, LOOMQ_ELSE_1
addi x3, x1, 0
addi x3, x3, 7
j LOOMQ_END_2
LOOMQ_ELSE_1:
addi x3, x1, 0
addi x3, x3, -2
LOOMQ_END_2:
"""

OVERFLOW_CLASSICAL_BITS = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[33];
measure q[0] -> c[0];
measure q[0] -> c[32];
classical {
  if (c[0] == 1) { r1 = 9; } else { r1 = 4; }
}
"""


class HybridTraceTests(unittest.TestCase):
    def test_hybrid_trace_replays_true_and_false_paths(self):
        true_report = adapter.trace_hybrid(HYBRID, [1, 1])
        false_report = adapter.trace_hybrid(HYBRID, [1, 0])

        self.assertEqual(true_report["final_registers"]["x3"], 12)
        self.assertEqual(false_report["final_registers"]["x3"], 2)
        self.assertNotEqual(true_report["branch_path"], false_report["branch_path"])
        self.assertTrue(
            all(item["word"].startswith("0x") for item in true_report["quantum_machine_trace"])
        )

    def test_hybrid_trace_reports_machine_and_source_branch_truth_separately(self):
        report = adapter.trace_hybrid(HYBRID, [1, 1])

        self.assertEqual(report["measurement_inputs"], [1, 1])
        self.assertEqual(report["branch_events"][0]["machine_jump_taken"], False)
        self.assertEqual(report["branch_events"][0]["source_condition_true"], True)
        self.assertEqual(report["branch_events"][0]["influencing_measurements"], ["c[1]"])

    def test_hybrid_trace_tracks_measurement_provenance_through_temporaries(self):
        report = adapter.trace_hybrid(TEMPORARY_PROVENANCE, [0, 1])
        branch = report["branch_events"][0]

        self.assertEqual(report["final_registers"]["x5"], 4)
        self.assertEqual(branch["operand_provenance"]["left"], ["c[0]"])
        self.assertEqual(branch["operand_provenance"]["right"], ["c[1]"])
        self.assertEqual(branch["influencing_measurements"], ["c[0]", "c[1]"])

    def test_hybrid_trace_handles_nested_paths_and_is_deterministic(self):
        false_outer = adapter.trace_hybrid(NESTED, [0, 1])
        true_false = adapter.trace_hybrid(NESTED, [1, 0])
        true_true = adapter.trace_hybrid(NESTED, [1, 1])

        self.assertEqual(false_outer["final_registers"]["x4"], 10)
        self.assertEqual(true_false["final_registers"]["x4"], 70)
        self.assertEqual(true_true["final_registers"]["x4"], 100)
        self.assertEqual(adapter.trace_hybrid(NESTED, [1, 0]), true_false)
        self.assertEqual(len(false_outer["branch_events"]), 1)
        self.assertEqual(len(true_false["branch_events"]), 2)
        self.assertNotEqual(false_outer["branch_path"], true_false["branch_path"])
        self.assertNotEqual(true_false["branch_path"], true_true["branch_path"])

    def test_hybrid_trace_rejects_invalid_measurement_inputs(self):
        with self.assertRaisesRegex(ValueError, "length"):
            adapter.trace_hybrid(HYBRID, [1])
        with self.assertRaisesRegex(ValueError, "0 or 1"):
            adapter.trace_hybrid(HYBRID, [1, 2])
        with self.assertRaisesRegex(ValueError, "booleans"):
            adapter.trace_hybrid(HYBRID, [True, 0])
        with self.assertRaisesRegex(ValueError, "sequence"):
            adapter.trace_hybrid(HYBRID, "10")

    def test_hybrid_trace_preserves_compile_contract_and_reports_exact_machine_words(self):
        quantum, assembly = adapter.compile_hybrid(COMPILE_FIXTURE)
        report = adapter.trace_hybrid(HYBRID, [1, 0])
        expected_words = [
            f"0x{word:08x}"
            for word in encode_circuit(
                Circuit(
                    2,
                    2,
                    [
                        Gate("h", (0,)),
                        Gate("cx", (0, 1)),
                        Measurement(0, 0),
                        Measurement(1, 1),
                    ],
                )
            ).words
        ]

        self.assertEqual(quantum, ["measure q[0] -> c[0]", "measure q[1] -> c[1]"])
        self.assertEqual(assembly, EXPECTED_ASSEMBLY)
        self.assertEqual(
            [item["word"] for item in report["quantum_machine_trace"]],
            expected_words,
        )
        self.assertEqual(
            [item["decoded_operation"] for item in report["quantum_machine_trace"]],
            ["h q[0]", "cx q[0],q[1]", "measure q[0] -> c[0]", "measure q[1] -> c[1]"],
        )

    def test_hybrid_trace_reports_partial_custom_0_coverage_for_large_creg(self):
        bits = [1] + [0] * 31 + [1]

        report = adapter.trace_hybrid(OVERFLOW_CLASSICAL_BITS, bits)

        self.assertEqual(report["final_registers"]["x1"], 9)
        self.assertEqual(report["branch_path"], "if1:T")
        self.assertEqual(
            report["loaded_measurement_inputs"][0],
            {"measurement": "c[0]", "register": "x10", "value": 1},
        )
        self.assertEqual(
            report["loaded_measurement_inputs"][-1],
            {"measurement": "c[21]", "register": "x31", "value": 0},
        )
        self.assertEqual(
            report["omitted_measurement_inputs"][0],
            {"measurement": "c[22]", "reason": "no representable RISC-V replay register"},
        )
        self.assertEqual(
            report["omitted_measurement_inputs"][-1],
            {"measurement": "c[32]", "reason": "no representable RISC-V replay register"},
        )
        self.assertEqual(
            [item["decoded_operation"] for item in report["quantum_machine_trace"]],
            ["measure q[0] -> c[0]"],
        )
        self.assertEqual(
            report["quantum_machine_coverage"],
            {
                "total_operations": 2,
                "encoded_operations": 1,
                "fully_encoded": False,
                "omitted_operations": [
                    {
                        "index": 1,
                        "operation": "measure q[0] -> c[32]",
                        "reason": "classical bit exceeds custom-0 5-bit operand field",
                    }
                ],
            },
        )
        self.assertEqual(adapter.trace_hybrid(OVERFLOW_CLASSICAL_BITS, bits), report)


if __name__ == "__main__":
    unittest.main()
