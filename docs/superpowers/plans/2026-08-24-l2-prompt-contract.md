# L2 Prompt Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Normalize each L2 request into a deterministic, tamper-evident task contract before asking the model or validating its answer, reducing private-case failures caused by paraphrases, fenced faulty code, platform restrictions, and account/local constraints.

**Architecture:** Add a dependency-free `loomq.prompt_contract` module that removes fenced code from semantic analysis, normalizes Unicode and number words, classifies the task, extracts a state target or backend constraints, and emits canonical SHA-256 fields. Keep the public `agent_chat()` return type unchanged. `loomq.agent` consumes the same contract for routing, target validation, backend filtering, and model grounding, so the model and validator cannot silently use different interpretations.

**Tech Stack:** Python 3.10 standard library, `unittest`, existing LoomQ adapter and capability table.

## Global Constraints

- Do not modify or depend on `hybrid_path_certificate.py` or its planned Web integration.
- Keep at least one real configured model call per official L2 case and retain the single bounded retry.
- Keep `adapter.agent_chat(prompt, history=None) -> str` unchanged.
- Use only the committed `backend_capabilities.json` as backend truth.
- Treat SHA-256 as content integrity, never authorship or a digital signature.
- Ignore fenced faulty code only for intent extraction; still send the complete original request to the model.
- Reject unsatisfiable backend constraints instead of relaxing them.
- Do not add dependencies.

---

### Task 1: Canonical Prompt Contract

**Files:**
- Create: `starter_kit/loomq/prompt_contract.py`
- Create: `starter_kit/tests/test_prompt_contract.py`

**Interfaces:**
- Produces: `build_prompt_contract(prompt: str) -> dict`
- Produces: `verify_prompt_contract(contract: dict, prompt: str) -> dict`
- Produces: `classify_task(prompt: str) -> str`
- Produces: `extract_state_goal(prompt: str) -> tuple[str, int] | None`
- Produces: `extract_backend_constraints(prompt: str) -> dict`
- Produces: `extract_qubit_count(prompt: str) -> int | None`

- [ ] **Step 1: Write failing contract tests**

```python
def test_contract_ignores_faulty_fenced_code_when_extracting_repair_goal():
    prompt = "Repair this program so it prepares a three-qubit GHZ state. ```qasm\n// |101> Bell\n```"
    contract = build_prompt_contract(prompt)
    self.assertEqual(contract["task_kind"], "repair")
    self.assertEqual(contract["state_goal"], {"family": "GHZ", "qubits": 3})
    self.assertEqual(contract["normalization"]["removed_code_blocks"], 1)

def test_semantic_digest_is_invariant_across_equivalent_paraphrases():
    prompts = [
        "Prepare a five-qubit GHZ state",
        "Create a 5‑qbit cat state",
        "生成五个量子位的 GHZ 猫态",
    ]
    digests = {build_prompt_contract(prompt)["integrity"]["semantic_sha256"] for prompt in prompts}
    self.assertEqual(len(digests), 1)

def test_verifier_rejects_semantic_tampering_even_after_digest_replacement():
    contract = build_prompt_contract("Prepare a five-qubit GHZ state")
    tampered = copy.deepcopy(contract)
    tampered["state_goal"]["qubits"] = 3
    self.assertFalse(verify_prompt_contract(tampered, "Prepare a five-qubit GHZ state")["valid"])
```

- [ ] **Step 2: Run the new tests and observe RED**

Run: `cd starter_kit && python3 -m unittest tests.test_prompt_contract -v`

Expected: import failure for `loomq.prompt_contract`, proving the production module does not yet exist.

- [ ] **Step 3: Implement canonical extraction and verification**

Implementation requirements: define `PROMPT_CONTRACT_SCHEMA = "loomq-prompt-contract-v1"`. `build_prompt_contract()` must reject empty/non-string input, normalize Unicode dashes and whitespace, remove fenced code for semantic parsing, classify backend/generate/repair, extract exactly one target or backend constraint set, and hash the original request and canonical semantic payload separately. `verify_prompt_contract()` must rebuild from the supplied original prompt and compare the complete object rather than trusting either declared digest.

Normalize English number words `two` through `nine`, Chinese `二/两` through `九`, `qbit/q-bit/quantum bit/量子位`, GHZ long-form/cat-state, Bell/EPR, W/single-excitation, and equal-weight/uniform superposition. Normalize backend platforms to `spinq`, `originq`, or `braket`; extract `requires_account=false` and `local_only=true` without guessing live availability.

- [ ] **Step 4: Run contract tests and observe GREEN**

Run: `cd starter_kit && python3 -m unittest tests.test_prompt_contract -v`

Expected: all contract tests pass with no warnings.

---

### Task 2: Use One Contract for Model Grounding and Validation

**Files:**
- Modify: `starter_kit/loomq/agent.py`
- Extend: `starter_kit/tests/test_prompt_contract.py`

**Interfaces:**
- Consumes: all Task 1 extraction functions.
- Preserves: `_expects_qasm(prompt) -> bool`, `_state_goal(prompt) -> tuple | None`, `_backend_constraints(prompt) -> tuple`, and `chat(...) -> str`.

- [ ] **Step 1: Add failing integration tests**

```python
def test_originq_platform_constraint_excludes_other_free_simulators():
    ids = [item["id"] for item in _compatible_backends(
        "Which free 20-qubit simulator on OriginQ needs no account?"
    )]
    self.assertEqual(ids, ["originq_local_simulator"])

def test_braket_local_constraint_is_not_relaxed_to_originq():
    reply = _deterministic_backend_reply(
        "Choose a no-account local Braket simulator for 25 q-bits"
    )
    self.assertIn("braket_local_simulator", reply)

def test_impossible_no_account_qpu_request_fails_closed():
    self.assertIsNone(_deterministic_backend_reply(
        "I need a 50-qubit QPU without an account"
    ))

def test_agent_validates_repair_goal_outside_faulty_code_block():
    reply = chat(prompt_with_faulty_fenced_basis_state, invalid_completion)
    _validate_state_goal(prompt_with_faulty_fenced_basis_state, _qasm_from_reply(reply))
```

- [ ] **Step 2: Run integration tests and observe RED**

Run: `cd starter_kit && python3 -m unittest tests.test_prompt_contract -v`

Expected: platform/account cases choose an incompatible earlier capability-table entry, and fenced code overrides or hides the requested goal.

- [ ] **Step 3: Route and validate from the shared contract**

Required changes:

- `_expects_qasm()` delegates to `classify_task()`.
- `_qubit_count()` delegates to `extract_qubit_count()`.
- `_state_goal()` delegates to `extract_state_goal()`.
- `_compatible_backends()` additionally filters `platforms`, `requires_account`, and `local_only` from `extract_backend_constraints()`.
- `_validate_backend_reply()` names those constraints in retry diagnostics.
- `chat()` appends a compact canonical semantic contract to the system instruction while retaining the original prompt verbatim as the user message.
- `_deterministic_backend_reply()` returns `None` for an empty compatible set; no constraint is relaxed.

- [ ] **Step 4: Run focused and existing L2 suites**

Run:

```bash
cd starter_kit
python3 -m unittest tests.test_prompt_contract tests.test_agent tests.test_agent_semantics tests.test_l2_qualification tests.test_l2_stress_campaign -v
```

Expected: new and existing tests pass; qualification requests still use `deepseek-v4-flash`, temperature `0`, disabled thinking, and one or two real HTTP calls as before.

---

### Task 3: Archive Evidence and Human-Written Documentation

**Files:**
- Modify: `starter_kit/verify_submission.py`
- Modify after Hybrid-path integration is reconciled: `starter_kit/README.md`, `starter_kit/JUDGE_GUIDE.md`, `starter_kit/CHANGELOG.md`, `starter_kit/SCIENTIFIC_CLAIMS_AUDIT.md`, `starter_kit/COMPETITIVE_COVERAGE.md`
- Create: `starter_kit/PROMPT_CONTRACT.md`

**Interfaces:**
- Consumes: `tests.test_prompt_contract` and the stable contract schema.
- Produces: one judge command and a precise non-claim boundary.

- [ ] **Step 1: Add the focused suite to the archive verifier**

Add `tests.test_prompt_contract` to the explicit Web/L2 integration phase without removing full archive discovery.

- [ ] **Step 2: Document the reproducible claim**

State only these claims:

- equivalent supported paraphrases normalize to one semantic SHA-256;
- fenced faulty code is excluded from intent extraction but remains in the model request;
- platform/account/local constraints are enforced against the committed capability table;
- rebuilding detects modified contract contents;
- the digest is not a signature and does not prove private DeepSeek accuracy.

- [ ] **Step 3: Remove AI-like prose patterns**

Run the repository prose through the selected anti-AI writing skill. Remove promotional superlatives, repeated “not X but Y” constructions, vague “systematic innovation” language, and redundant three-item slogans while preserving exact commands, test counts, caveats, and scientific claims.

- [ ] **Step 4: Run full verification**

Run:

```bash
python3 starter_kit/verify_submission.py
python3 -m unittest discover -s tests -v
git diff --check
```

Expected: all phases pass; root tests pass with only explicitly optional PyQuafu skips.

- [ ] **Step 5: Review, commit, push, and archive**

Request a read-only code review focused on intent ambiguity, constraint relaxation, digest scope, and overclaiming. After resolving findings, commit with Lore trailers, push `main`, run `prepare_submission.py --team-id JunkaiWang-TheoPhy`, create a new official Final Submission Issue, and retain the `submission:accepted` receipt with archive SHA-256 and Artifact ID.

## Self-Review

- Spec coverage: Task 1 covers deterministic normalization/integrity; Task 2 covers scoring-path behavior; Task 3 covers archive visibility and claim boundaries.
- Placeholder scan: the plan contains no deferred implementation placeholders; executable steps name exact behavior, files, and commands.
- Type consistency: all consumers use dictionary contracts and preserve the existing public string return type.
