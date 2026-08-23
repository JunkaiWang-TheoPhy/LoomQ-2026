"""Optional numerical cross-check against the independently maintained PyQuafu engine."""

import cmath
import importlib.util
import math
import random
import unittest

from starter_kit.loomq.qasm import parse_qasm
from starter_kit.loomq.simulator import simulate_statevector


HAS_QUAFU = importlib.util.find_spec("quafu") is not None


@unittest.skipUnless(HAS_QUAFU, "pyquafu is an optional development oracle")
class QuafuOracleTests(unittest.TestCase):
    def test_quafu_accepts_the_published_controlled_phase_syntax(self):
        from quafu import simulate

        source = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2]; creg c[2];
h q[0]; h q[1]; cu1(pi/5) q[0],q[1];
h q[0]; h q[1]; measure q -> c;
"""
        result = list(simulate(source, shots=0).get_statevector())

        self.assertEqual(len(result), 4)
        self.assertAlmostEqual(sum(abs(value) ** 2 for value in result), 1.0, places=9)

    def test_seeded_random_circuits_match_up_to_global_phase(self):
        from quafu import simulate

        generator = random.Random(20260823)
        one_qubit = ["h", "x", "s", "sdg", "t", "tdg"]
        parameterized = ["ry", "rz"]
        angles = [math.pi / 7, -math.pi / 3, 0.271]

        for case_index in range(12):
            lines = [
                "OPENQASM 2.0;",
                'include "qelib1.inc";',
                "qreg q[3];",
                "creg c[3];",
            ]
            for _ in range(18):
                kind = generator.randrange(5)
                if kind == 0:
                    lines.append(f"{generator.choice(one_qubit)} q[{generator.randrange(3)}];")
                elif kind == 1:
                    lines.append(
                        f"{generator.choice(parameterized)}({generator.choice(angles)!r}) "
                        f"q[{generator.randrange(3)}];"
                    )
                elif kind == 2:
                    left, right = generator.sample(range(3), 2)
                    lines.append(f"cx q[{left}],q[{right}];")
                elif kind == 3:
                    left, right = generator.sample(range(3), 2)
                    lines.append(f"swap q[{left}],q[{right}];")
                else:
                    controls = generator.sample(range(3), 3)
                    lines.append(f"ccx q[{controls[0]}],q[{controls[1]}],q[{controls[2]}];")
            lines.append("measure q -> c;")
            source = "\n".join(lines)

            ours = simulate_statevector(parse_qasm(source))
            theirs = list(simulate(source, shots=0).get_statevector())
            pivot = next((index for index, value in enumerate(theirs) if abs(value) > 1e-10), None)
            self.assertIsNotNone(pivot)
            phase = ours[pivot] / theirs[pivot]
            if abs(phase) > 1e-12:
                phase /= abs(phase)
            with self.subTest(case=case_index):
                for ours_value, theirs_value in zip(ours, theirs):
                    self.assertAlmostEqual(ours_value.real, (phase * theirs_value).real, places=9)
                    self.assertAlmostEqual(ours_value.imag, (phase * theirs_value).imag, places=9)


if __name__ == "__main__":
    unittest.main()
