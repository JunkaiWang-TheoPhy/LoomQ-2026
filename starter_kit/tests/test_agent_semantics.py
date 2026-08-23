import unittest

from loomq.agent import _deterministic_state_reply, _qasm_from_reply, _state_goal, _validate_state_goal
from loomq.qasm import QASMError


def measured(body: str, qubits: int) -> str:
    return f"""OPENQASM 2.0;
include "qelib1.inc";
qreg q[{qubits}];
creg c[{qubits}];
{body}
measure q -> c;
"""


class AgentSemanticTests(unittest.TestCase):
    def test_w_state_positive_case_is_accepted(self):
        prompt = "生成四比特 W 态并测量"
        reply = _deterministic_state_reply(prompt)

        self.assertIsNotNone(reply)
        _validate_state_goal(prompt, _qasm_from_reply(reply))

    def test_computational_basis_positive_case_is_accepted(self):
        prompt = "制备计算基态 |101> 并测量"
        reply = _deterministic_state_reply(prompt)

        self.assertIsNotNone(reply)
        _validate_state_goal(prompt, _qasm_from_reply(reply))

    def test_uniform_superposition_positive_case_is_accepted(self):
        prompt = "生成四比特均匀叠加态并测量"
        reply = _deterministic_state_reply(prompt)

        self.assertIsNotNone(reply)
        _validate_state_goal(prompt, _qasm_from_reply(reply))

    def test_computational_basis_request_rejects_the_wrong_basis_state(self):
        wrong = measured("x q[0];", 3)

        with self.assertRaisesRegex(QASMError, "computational basis"):
            _validate_state_goal("制备计算基态 |101> 并测量", wrong)

    def test_uniform_superposition_rejects_a_nonuniform_distribution(self):
        nonuniform = measured("h q[0];", 3)

        with self.assertRaisesRegex(QASMError, "uniform superposition"):
            _validate_state_goal("生成 3 比特均匀叠加态并测量", nonuniform)

    def test_w_state_request_rejects_a_ghz_distribution(self):
        ghz = measured("h q[0];\ncx q[0],q[1];\ncx q[0],q[2];", 3)

        with self.assertRaisesRegex(QASMError, "W target state"):
            _validate_state_goal("生成三比特 W 态并测量", ghz)

    def test_state_goal_recognizes_english_and_chinese_goal_families(self):
        self.assertEqual(_state_goal("prepare a 4-qubit W state"), ("W", 4))
        self.assertEqual(_state_goal("制备计算基态 |101>"), ("computational basis", 3))
        self.assertEqual(
            _state_goal("生成四比特均匀叠加态"), ("uniform superposition", 4)
        )


if __name__ == "__main__":
    unittest.main()
