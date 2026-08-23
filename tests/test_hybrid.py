import itertools
import random
import unittest

from starter_kit import adapter
from starter_kit.riscv_emulator import TinyRISCVEmulator


def execute(assembly, **registers):
    emulator = TinyRISCVEmulator()
    emulator.load_program(assembly)
    for name, value in registers.items():
        emulator.set_register(name, value)
    return emulator.execute()


class HybridCompilerTests(unittest.TestCase):
    def test_seeded_random_programs_match_independent_reference(self):
        generator = random.Random(20260823)
        for case_index in range(1000):
            left = generator.randint(-20, 20)
            right = generator.randint(-20, 20)
            offset = generator.randint(-10, 10)
            sentinel = generator.randint(-20, 20)
            comparison = generator.choice(("==", "!="))
            source = f"""OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2]; measure q -> c;
classical {{
  r1 = {left}; r2 = {right};
  if (c[0] {comparison} c[1]) {{ r3 = r1 + r2; }} else {{ r3 = r2 - r1; }}
  if (r3 != {sentinel}) {{ r4 = r3 + {offset}; }} else {{ r4 = {sentinel}; }}
}}
"""
            _, assembly = adapter.compile_hybrid(source)
            for c0, c1 in itertools.product((0, 1), repeat=2):
                condition = c0 == c1
                if comparison == "!=":
                    condition = not condition
                r3 = left + right if condition else right - left
                expected = r3 + offset if r3 != sentinel else sentinel
                with self.subTest(case=case_index, c0=c0, c1=c1):
                    state = execute(assembly, x10=c0, x11=c1)
                    self.assertEqual(state.get("x4", 0), expected)

    def test_extracts_quantum_operations_before_and_after_classical_block(self):
        source = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0];
measure q[0] -> c[0];
classical { r1 = 3; }
cx q[0],q[1];
measure q[1] -> c[1];
"""

        quantum, _ = adapter.compile_hybrid(source)

        self.assertEqual(
            quantum,
            [
                "h q[0]",
                "measure q[0] -> c[0]",
                "cx q[0],q[1]",
                "measure q[1] -> c[1]",
            ],
        )

    def test_compiles_sequential_assignments_without_clobbering_rhs(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1]; measure q[0] -> c[0];
classical {
  r1 = 4;
  r2 = 9;
  r1 = r2 + r1 - 2;
}
"""

        _, assembly = adapter.compile_hybrid(source)
        state = execute(assembly)

        self.assertEqual(state["x1"], 11)
        self.assertEqual(state["x2"], 9)

    def test_compiles_nested_equality_and_inequality_branches(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2]; measure q -> c;
classical {
  if (c[0] == 1) {
    if (c[1] != 0) { r1 = 100; } else { r1 = 70; }
  } else {
    r1 = 10;
  }
  r1 = r1 + 5;
}
"""

        _, assembly = adapter.compile_hybrid(source)
        expected = {(0, 0): 15, (0, 1): 15, (1, 0): 75, (1, 1): 105}
        for c0, c1 in itertools.product((0, 1), repeat=2):
            with self.subTest(c0=c0, c1=c1):
                state = execute(assembly, x10=c0, x11=c1)
                self.assertEqual(state["x1"], expected[(c0, c1)])

    def test_measurement_c2_maps_to_x12(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[3]; creg c[3]; measure q -> c;
classical { if (c[2] == 1) { r3 = 8; } else { r3 = 2; } }
"""

        _, assembly = adapter.compile_hybrid(source)

        self.assertEqual(execute(assembly, x12=0)["x3"], 2)
        self.assertEqual(execute(assembly, x12=1)["x3"], 8)

    def test_rejects_measurement_reference_outside_declared_creg(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1]; measure q -> c;
classical { r1 = c[1]; }
"""

        with self.assertRaisesRegex(ValueError, "declared classical register"):
            adapter.compile_hybrid(source)

    def test_sums_all_measurement_registers_without_temporary_aliasing(self):
        terms = " + ".join(f"c[{index}]" for index in range(22))
        source = f"""OPENQASM 2.0; include "qelib1.inc";
qreg q[22]; creg c[22]; measure q -> c;
classical {{ r1 = {terms}; }}
"""

        _, assembly = adapter.compile_hybrid(source)
        registers = {f"x{10 + index}": index % 2 for index in range(22)}

        self.assertEqual(execute(assembly, **registers)["x1"], 11)

    def test_temporary_registers_do_not_clobber_high_measurement_bits(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[11]; creg c[11]; measure q -> c;
classical {
  r1 = c[10] + 1;
  r2 = c[10] + 2;
}
"""

        _, assembly = adapter.compile_hybrid(source)
        state = execute(assembly, x20=1)

        self.assertEqual(state["x1"], 2)
        self.assertEqual(state["x2"], 3)

    def test_rejects_assignment_to_measurement_bit(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1]; measure q -> c;
classical { c[0] = 2; }
"""

        with self.assertRaisesRegex(ValueError, "assignment target"):
            adapter.compile_hybrid(source)

    def test_braces_inside_comments_do_not_end_classical_block(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1]; measure q -> c;
classical {
  // A closing brace in prose must not terminate parsing: }
  r1 = 6;
  /* Nor should a nested-looking comment: { } */
  r1 = r1 + 1;
}
"""

        _, assembly = adapter.compile_hybrid(source)

        self.assertEqual(execute(assembly)["x1"], 7)

    def test_rejects_missing_classical_block(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1]; measure q -> c;
"""

        with self.assertRaisesRegex(ValueError, "classical block"):
            adapter.compile_hybrid(source)


if __name__ == "__main__":
    unittest.main()
