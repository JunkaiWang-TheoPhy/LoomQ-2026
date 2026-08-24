# L2 prompt contract

LoomQ parses each L2 request before it calls the configured model. The parser produces one small contract for task routing, target-state checks, backend filtering, and model instructions. The same interpretation therefore reaches both the model and the deterministic validator.

This closes a concrete class of private-case failures. A request such as `推荐一个能制备 GHZ 态的后端` is a backend-selection task, while `Use Braket to generate a Bell circuit` asks for circuit output. Fenced faulty QASM remains in the model request, but comments inside that block cannot replace the requested target during validation.

## Contract fields

| Field | Meaning | Used by |
| --- | --- | --- |
| `task_kind` | `generate`, `repair`, or `backend` | reply routing and validation |
| `state_goal` | state family, qubit count, and basis bits when applicable | semantic QASM validation and deterministic fallback |
| `backend_constraints` | minimum qubits, queue, cost, kind, platform, account, and local-execution requirements | capability-table filtering |
| `normalization.removed_code_blocks` | number of fenced blocks excluded from intent extraction | audit output |
| `request_sha256` | digest of the complete original request | change detection |
| `semantic_sha256` | digest of the normalized semantic fields | supported paraphrase comparison |
| `contract_sha256` | digest of the contract payload | change detection before rebuild |

The original prompt is still sent to the model. Only the deterministic intent parser omits fenced code.

## Example

For this request:

```text
Which free 20-qubit simulator on OriginQ needs no account?
```

the semantic part of the contract is:

```json
{
  "task_kind": "backend",
  "state_goal": null,
  "backend_constraints": {
    "minimum_qubits": 20,
    "no_queue": false,
    "free": true,
    "kinds": ["simulator"],
    "platforms": ["originq"],
    "requires_account": false,
    "local_only": false
  }
}
```

`_compatible_backends()` applies those fields to `backend_capabilities.json`. It returns `originq_local_simulator` for this request. If no row satisfies every requested field, the deterministic fallback returns no recommendation instead of dropping a constraint.

## Reproduce the evidence

Run the focused contract tests from the extracted starter kit:

```bash
python3 -m unittest tests.test_prompt_contract -v
```

The cases cover English and Chinese routing, mixed backend and state language, negation, Unicode qubit notation, code-block contamination, computational-basis bits, platform and account filters, unsatisfiable constraints, model grounding, and contract tampering.

To print a contract directly:

```bash
python3 - <<'PY'
import json
from loomq.prompt_contract import build_prompt_contract

prompt = "Which free 20-qubit simulator on OriginQ needs no account?"
print(json.dumps(build_prompt_contract(prompt), indent=2, ensure_ascii=False))
PY
```

`verify_prompt_contract(contract, prompt)` first checks the declared payload digest, then rebuilds the complete contract from the supplied prompt and compares the objects. Replacing a digest after changing a semantic field does not make the modified contract valid.

## Claim boundary

The SHA-256 fields detect changes. They are not signatures and do not establish authorship. The parser supports the vocabulary exercised by the committed tests; it is not a general natural-language proof system. Local qualification and stress tests do not reveal the organizer's private twelve prompts or establish their score. Backend filtering uses the committed capability table and makes no claim about a provider's current queue or hardware availability.
