import itertools
import random
import unittest

import adapter
from bonus_evaluator import evaluate_bonus
from riscv_emulator import TinyRISCVEmulator


GATES = {
    "h": "h q[0]",
    "x": "x q[0]",
    "s": "s q[0]",
    "sdg": "sdg q[0]",
    "t": "t q[0]",
    "tdg": "tdg q[0]",
    "rz": "rz(pi/3) q[0]",
    "ry": "ry(-pi/4) q[1]",
    "cx": "cx q[0],q[1]",
    "cu1": "cu1(pi/8) q[0],q[1]",
    "swap": "swap q[0],q[1]",
    "ccx": "ccx q[0],q[1],q[2]",
}

NATIVE_NAMES = {
    "spinq": {
        "h": "h q[0];", "x": "x q[0];", "s": "s q[0];", "sdg": "sdg q[0];",
        "t": "t q[0];", "tdg": "tdg q[0];", "rz": "rz(1.0471975511965976)",
        "ry": "ry(-0.7853981633974483)", "cx": "cx q[0],q[1];",
        "cu1": "cu1(0.39269908169872414)", "swap": "swap q[0],q[1];",
        "ccx": "ccx q[0],q[1],q[2];",
    },
    "originq": {
        "h": "H q[0]", "x": "X q[0]", "s": "S q[0]", "sdg": "SDAG q[0]",
        "t": "T q[0]", "tdg": "TDAG q[0]", "rz": "RZ q[0],(1.0471975511965976)",
        "ry": "RY q[1],(-0.7853981633974483)", "cx": "CNOT q[0],q[1]",
        "cu1": "CR q[0],q[1],(0.39269908169872414)", "swap": "SWAP q[0],q[1]",
        "ccx": "TOFFOLI q[0],q[1],q[2]",
    },
    "braket": {
        "h": "h q[0];", "x": "x q[0];", "s": "s q[0];", "sdg": "sdg q[0];",
        "t": "t q[0];", "tdg": "tdg q[0];", "rz": "rz(1.0471975511965976)",
        "ry": "ry(-0.7853981633974483)", "cx": "cnot q[0],q[1];",
        "cu1": "cp(0.39269908169872414)", "swap": "swap q[0],q[1];",
        "ccx": "ccx q[0],q[1],q[2];",
    },
}


def circuit(gate: str) -> str:
    return f'''OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
{GATES[gate]};
measure q -> c;
'''


def emitter_test(gate: str, target: str):
    def test(self):
        source = circuit(gate)
        native = adapter.transpile(source, target)
        result = adapter.run(source, target, 97)

        self.assertIn(NATIVE_NAMES[target][gate], native)
        self.assertEqual(sum(result["counts"].values()), 97)
        self.assertEqual(result["shots"], 97)

    return test


class GateMatrixTests(unittest.TestCase):
    """Every official gate crosses every official target in its own regression."""


for _target, _gate in itertools.product(adapter.SUPPORTED_TARGETS, GATES):
    setattr(
        GateMatrixTests,
        f"test_{_target}_{_gate}",
        emitter_test(_gate, _target),
    )


class ArchivedDeepPathTests(unittest.TestCase):
    def test_seeded_hybrid_programs_match_an_independent_reference(self):
        generator = random.Random(20260824)
        for case in range(250):
            left = generator.randint(-50, 50)
            right = generator.randint(-50, 50)
            source = f'''OPENQASM 2.0; include "qelib1.inc";
qreg q[2]; creg c[2]; measure q -> c;
classical {{
  r1 = {left}; r2 = {right};
  if (c[0] == c[1]) {{ r3 = r1 + r2; }} else {{ r3 = r2 - r1; }}
}}
'''
            _, assembly = adapter.compile_hybrid(source)
            for c0, c1 in itertools.product((0, 1), repeat=2):
                emulator = TinyRISCVEmulator()
                emulator.load_program(assembly)
                emulator.set_register("x10", c0)
                emulator.set_register("x11", c1)
                state = emulator.execute()
                expected = left + right if c0 == c1 else right - left
                with self.subTest(case=case, c0=c0, c1=c1):
                    self.assertEqual(state.get("x3", 0), expected)

    def test_quantum_riscv_machine_code_executes_end_to_end(self):
        report = evaluate_bonus()

        self.assertTrue(report["passed"], report)
        self.assertEqual(report["counts"], {"00": 512, "11": 512})


if __name__ == "__main__":
    unittest.main()

