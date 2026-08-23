import unittest

from loomq.qasm import parse_qasm
from loomq.simulator import trace_statevector


BELL = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""


def probabilities(event):
    return {state["basis"]: state["probability"] for state in event["states"]}


class StateTraceTests(unittest.TestCase):
    def test_bell_trace_exposes_hand_derived_state_after_every_gate(self):
        trace = trace_statevector(parse_qasm(BELL))

        self.assertEqual([event["operation"]["kind"] for event in trace], ["initial", "gate", "gate", "measure"])
        self.assertEqual(probabilities(trace[0]), {"00": 1.0})
        self.assertEqual(probabilities(trace[1]), {"00": 0.5, "01": 0.5})
        self.assertEqual(probabilities(trace[2]), {"00": 0.5, "11": 0.5})
        self.assertEqual(probabilities(trace[3]), {"00": 0.5, "11": 0.5})
        self.assertEqual(trace[1]["operation"]["gate"], "h")
        self.assertEqual(trace[2]["operation"]["qubits"], [0, 1])
        self.assertEqual(
            trace[3]["operation"]["mappings"],
            [{"qubit": 0, "clbit": 0}, {"qubit": 1, "clbit": 1}],
        )

    def test_phase_trace_preserves_interference_not_just_probabilities(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1];
h q[0]; s q[0]; s q[0]; h q[0]; measure q -> c;
"""

        trace = trace_statevector(parse_qasm(source))

        self.assertAlmostEqual(trace[2]["states"][1]["phase_radians"], 1.5707963267948966)
        self.assertEqual(probabilities(trace[-2]), {"1": 1.0})

    def test_trace_rejects_state_explosion_instead_of_hanging_the_web(self):
        source = """OPENQASM 2.0; include "qelib1.inc";
qreg q[9]; creg c[9]; h q[0]; measure q -> c;
"""

        with self.assertRaisesRegex(ValueError, "at most 8 qubits"):
            trace_statevector(parse_qasm(source))


if __name__ == "__main__":
    unittest.main()
