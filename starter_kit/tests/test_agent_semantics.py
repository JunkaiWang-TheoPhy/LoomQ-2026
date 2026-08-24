import unittest

from loomq.agent import (
    _deterministic_backend_reply,
    _deterministic_state_reply,
    _expects_qasm,
    _qasm_from_reply,
    _state_goal,
    _validate_backend_reply,
    _validate_state_goal,
    chat,
)
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
    def test_state_goal_normalizes_private_shape_synonyms_and_qubit_units(self):
        cases = [
            ("Create a 5-qubit cat state and measure it", ("GHZ", 5)),
            ("Prepare an EPR pair and measure both qbits", ("Bell", 2)),
            ("生成 5 个量子位的最大纠缠态并全测量", ("GHZ", 5)),
        ]

        for prompt, expected in cases:
            with self.subTest(prompt=prompt):
                self.assertEqual(_state_goal(prompt), expected)

    def test_private_shape_synonyms_recover_after_two_invalid_completions(self):
        calls = 0

        def invalid_model(_messages):
            nonlocal calls
            calls += 1
            return {"choices": [{"message": {"content": "invalid"}}]}

        for prompt in (
            "Create a 5-qubit cat state and measure it",
            "Prepare an EPR pair and measure both qbits",
            "生成 5 个量子位的最大纠缠态并全测量",
        ):
            with self.subTest(prompt=prompt):
                reply = chat(prompt, invalid_model)
                _validate_state_goal(prompt, _qasm_from_reply(reply))

        self.assertEqual(calls, 6)

    def test_circuit_selection_verbs_do_not_override_state_generation_cues(self):
        self.assertTrue(_expects_qasm("选择一个 Bell 态电路并测量"))
        self.assertTrue(_expects_qasm("Select a Bell circuit and measure it"))
        self.assertFalse(_expects_qasm("选择一个至少 28 比特的模拟器"))
        self.assertFalse(_expects_qasm("Which simulator should I use for 28 qubits?"))

    def test_backend_fallback_solves_constraints_from_the_capability_table(self):
        cases = [
            ("推荐一个免费、零排队、至少 15 比特的后端", "spinq_taurus_simulator"),
            ("Which 50-qubit QPU backend is compatible?", "originq_wukong"),
            ("选择一个至少 28 比特的模拟器", "originq_local_simulator"),
        ]

        for prompt, expected_id in cases:
            with self.subTest(prompt=prompt):
                reply = _deterministic_backend_reply(prompt)
                self.assertIsNotNone(reply)
                self.assertIn(expected_id, reply)
                _validate_backend_reply(prompt, reply)

    def test_backend_fallback_refuses_unsatisfiable_constraints(self):
        self.assertIsNone(_deterministic_backend_reply("推荐 80 比特真机后端"))
        self.assertIsNone(
            _deterministic_backend_reply(
                "Which 50-qbit QPU is available without waiting?"
            )
        )
        self.assertIsNone(
            _deterministic_backend_reply("推荐 34 量子位、无需排队且零费用的平台")
        )

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
