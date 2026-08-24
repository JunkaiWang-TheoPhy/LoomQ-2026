import copy
import hashlib
import json
import unittest

from loomq.agent import (
    _compatible_backends,
    _deterministic_backend_reply,
    _expected_distribution,
    _qasm_from_reply,
    _state_goal,
    _validate_state_goal,
    chat,
)
from loomq.prompt_contract import (
    build_prompt_contract,
    classify_task,
    extract_backend_constraints,
    verify_prompt_contract,
)


class PromptContractTests(unittest.TestCase):
    def test_contract_ignores_faulty_fenced_code_when_extracting_repair_goal(self):
        prompt = """Repair this program so it prepares a three-qubit GHZ state.
```qasm
OPENQASM 2.0;
// stale target: |101> Bell
```
"""

        contract = build_prompt_contract(prompt)

        self.assertEqual(contract["task_kind"], "repair")
        self.assertEqual(contract["state_goal"], {"family": "GHZ", "qubits": 3})
        self.assertEqual(contract["normalization"]["removed_code_blocks"], 1)
        self.assertEqual(_state_goal(prompt), ("GHZ", 3))

    def test_computational_basis_bits_come_from_instruction_not_faulty_code(self):
        prompt = """Repair this circuit so it prepares computational basis 000.
```qasm
OPENQASM 2.0;
// stale target: |101>
```
"""

        contract = build_prompt_contract(prompt)

        self.assertEqual(
            contract["state_goal"],
            {"family": "computational basis", "qubits": 3, "basis_bits": "000"},
        )
        self.assertEqual(
            _expected_distribution(prompt, "computational basis", 3), {"000": 1.0}
        )

    def test_semantic_digest_is_invariant_across_equivalent_paraphrases(self):
        prompts = (
            "Prepare a five-qubit GHZ state",
            "Create a 5‑qbit cat state",
            "生成五个量子位的 GHZ 猫态",
        )

        contracts = [build_prompt_contract(prompt) for prompt in prompts]

        self.assertEqual(
            {contract["integrity"]["semantic_sha256"] for contract in contracts},
            {contracts[0]["integrity"]["semantic_sha256"]},
        )
        self.assertTrue(
            all(
                contract["state_goal"] == {"family": "GHZ", "qubits": 5}
                for contract in contracts
            )
        )

    def test_originq_platform_and_account_constraints_exclude_other_simulators(self):
        prompt = "Which free 20-qubit simulator on OriginQ needs no account?"

        ids = [backend["id"] for backend in _compatible_backends(prompt)]

        self.assertEqual(ids, ["originq_local_simulator"])

    def test_braket_local_constraint_is_not_relaxed_to_another_platform(self):
        prompt = "Choose a no-account local Braket simulator for 25 q-bits"

        reply = _deterministic_backend_reply(prompt)

        self.assertIsNotNone(reply)
        self.assertIn("braket_local_simulator", reply)

    def test_impossible_no_account_qpu_request_fails_closed(self):
        prompt = "I need a 50-qubit QPU without an account"

        self.assertEqual(_compatible_backends(prompt), [])
        self.assertIsNone(_deterministic_backend_reply(prompt))

    def test_backend_classification_honors_direct_negation_without_only_keyword(self):
        self.assertEqual(
            classify_task("Do not repair anything; recommend a free local simulator."),
            "backend",
        )
        self.assertEqual(
            classify_task("I don't want a backend; generate a Bell circuit."),
            "generate",
        )

    def test_find_is_a_backend_selection_action(self):
        self.assertEqual(classify_task("Find a free local simulator."), "backend")

    def test_imperative_use_routes_backend_requests_to_backend_validation(self):
        prompts = (
            "Use Braket local simulator for 20 qubits.",
            "Use OriginQ simulator for 20 qubits.",
            "用 Braket 本地模拟器，20 比特。",
            "用一个 20 比特本地模拟器。",
            "用哪个模拟器跑 20 比特？",
        )

        self.assertEqual([classify_task(prompt) for prompt in prompts], ["backend"] * 5)
        self.assertEqual(
            classify_task("Use Braket to generate a Bell circuit."), "generate"
        )

    def test_backend_selection_wins_when_capability_mentions_a_target_state(self):
        prompts = (
            "I want a backend that can prepare Bell state.",
            "Need a backend to create a GHZ state.",
            "推荐一个能制备 GHZ 态的后端。",
            "我想要一个能生成 Bell 态的模拟器。",
        )

        self.assertEqual([classify_task(prompt) for prompt in prompts], ["backend"] * 4)

    def test_negated_optional_backend_properties_do_not_become_requirements(self):
        constraints = extract_backend_constraints(
            "Choose a simulator; it does not need to be free or local."
        )

        self.assertFalse(constraints["free"])
        self.assertFalse(constraints["local_only"])

    def test_negated_backend_kind_is_not_added_to_required_kinds(self):
        constraints = extract_backend_constraints("Choose a simulator, not a QPU")

        self.assertEqual(constraints["kinds"], ["simulator"])

    def test_model_receives_the_same_contract_used_by_backend_validation(self):
        calls = []

        def contract_aware_completion(messages):
            calls.append(messages)
            system = messages[0]["content"]
            backend_id = (
                "originq_local_simulator"
                if '"platforms":["originq"]' in system.replace(" ", "")
                else "spinq_taurus_simulator"
            )
            return {"choices": [{"message": {"content": f"Use `{backend_id}`."}}]}

        reply = chat(
            "Which free 20-qubit simulator on OriginQ needs no account?",
            contract_aware_completion,
        )

        self.assertIn("originq_local_simulator", reply)
        self.assertEqual(len(calls), 1)

    def test_repair_fallback_uses_requested_goal_not_stale_code_comment(self):
        prompt = """Fix this circuit so it prepares a three-qubit GHZ state.
```qasm
OPENQASM 2.0;
// old requirement: |101> Bell
qreg q[3];
```
"""

        def invalid_completion(_messages):
            return {"choices": [{"message": {"content": "invalid"}}]}

        reply = chat(prompt, invalid_completion)

        _validate_state_goal(prompt, _qasm_from_reply(reply))

    def test_verifier_rejects_tampering_even_after_checksum_replacement(self):
        prompt = "Prepare a five-qubit GHZ state"
        contract = build_prompt_contract(prompt)
        tampered = copy.deepcopy(contract)
        tampered["state_goal"]["qubits"] = 3
        payload = {key: value for key, value in tampered.items() if key != "integrity"}
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        tampered["integrity"]["contract_sha256"] = hashlib.sha256(encoded).hexdigest()

        report = verify_prompt_contract(tampered, prompt)

        self.assertFalse(report["valid"])
        self.assertEqual(report["reason"], "recomputed contract mismatch")


if __name__ == "__main__":
    unittest.main()
