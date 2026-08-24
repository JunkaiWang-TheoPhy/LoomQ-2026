# Final Judge Tour Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a judge reach six working, verifiable LoomQ capabilities from the first screen in under 90 seconds without hiding the beginner workflow.

**Architecture:** Add a sticky evidence rail to the existing single-page lab. Each rail item points to a real API-backed action and changes state only after semantic response validation succeeds. Add a read-only Prompt Contract endpoint and panel so the L2 interpretation is visible before a model response. Keep the current workbench, ProofTrace, counterfactual, statistical assertion, Witness Chain, and Hybrid panels as the underlying content.

**Tech Stack:** Python 3.10 standard library, `unittest`, vanilla HTML/CSS/JavaScript, existing LoomQ Web server and Browser QA.

## Global Constraints

- Start from the accepted mid-circuit Hybrid certificate integration commit, then replay Prompt Contract commits `149fbe8c9b5a4a6c591125c4de37a26950889de0` and `6c8d152cd69e6b57b20e1810da0270c1751b2e8c`.
- Accept only the audited `loomq.hybrid_paths` implementation for mid-circuit semantics. Remove the superseded terminal-state certificate module and do not preserve its projected-bit response shape.
- Consume canonical `/api/hybrid-paths` with `{certificate, verification}`, where `verification` is produced by server-side semantic recomputation against the submitted source. If the compatibility alias `/api/hybrid-path-certificate` remains, require the identical response. A client-side probability sum is not certificate verification.
- Do not copy a mascot, XP system, quiz, or full-screen intro from another submission.
- A tour step may show `完成` only after its corresponding local API returns a successful, schema-valid response.
- Do not show static provider status, queue state, job ID, or hardware availability.
- Keep every existing capability accessible without JavaScript-generated navigation.
- Preserve keyboard navigation, reduced-motion behavior, `aria-live` result regions, and 390 px layout without horizontal overflow.
- Add no dependencies.

---

### Task 1: Read-only Prompt Contract API

**Files:**
- Modify: `starter_kit/loomq/web.py`
- Test: `starter_kit/tests/test_web.py`

**Interfaces:**
- Consumes: `build_prompt_contract(prompt: str) -> dict` and `verify_prompt_contract(contract: dict, prompt: str) -> dict`.
- Produces: `POST /api/prompt-contract` with `{prompt: string}` and response `{contract: object, verification: object}`.

- [ ] **Step 1: Write the failing API test**

Add this behavior test to `WebLabTests`:

```python
def test_prompt_contract_endpoint_exposes_the_same_rebuild_verified_semantics(self):
    prompt = "Which free 20-qubit simulator on OriginQ needs no account?"
    status, _headers, body = self.request("/api/prompt-contract", {"prompt": prompt})

    payload = json.loads(body)
    self.assertEqual(status, 200)
    self.assertEqual(payload["contract"]["task_kind"], "backend")
    self.assertEqual(payload["contract"]["backend_constraints"]["platforms"], ["originq"])
    self.assertFalse(payload["contract"]["backend_constraints"]["requires_account"])
    self.assertTrue(payload["verification"]["valid"])
    self.assertFalse(payload["contract"]["integrity"]["is_signature"])
```

- [ ] **Step 2: Run the test and observe RED**

Run:

```bash
cd starter_kit
python3 -m unittest tests.test_web.WebLabTests.test_prompt_contract_endpoint_exposes_the_same_rebuild_verified_semantics -v
```

Expected: HTTP 404 because the route does not exist.

- [ ] **Step 3: Implement the endpoint**

Import both contract functions in `loomq/web.py`. In the POST dispatcher, require a non-empty string `prompt` with the same 20,000-character upper bound as `/api/agent`, then return:

```python
contract = build_prompt_contract(prompt)
return {
    "contract": contract,
    "verification": verify_prompt_contract(contract, prompt),
}
```

Map malformed input through the existing structured `invalid_request` response. The endpoint must not call the model or read credentials.

- [ ] **Step 4: Run focused Web and Prompt Contract tests**

Run:

```bash
cd starter_kit
python3 -m unittest tests.test_web tests.test_prompt_contract -v
```

Expected: all tests pass.

- [ ] **Step 5: Commit**

Commit the endpoint and test with a Lore message that records the no-model-call constraint.

---

### Task 2: Sticky Evidence Rail and Prompt Contract Panel

**Files:**
- Modify: `starter_kit/web/index.html`
- Modify: `starter_kit/web/app.js`
- Modify: `starter_kit/web/styles.css`
- Test: `starter_kit/tests/test_web.py`

**Interfaces:**
- Consumes: `/api/prompt-contract`, `/api/run`, `/api/compare`, `/api/assert`, `/api/causal-audit`, and `/api/hybrid-paths`.
- Produces: anchors `#workspace`, `#counterfactual-panel`, `#assert-panel`, `#witness-panel`, `#hybrid-path-panel`, and `#prompt-contract-panel`.
- Produces: `markTourStep(step: "run" | "compare" | "assert" | "witness" | "hybrid" | "contract", detail: string) -> void`.

- [ ] **Step 1: Add a failing home-page contract test**

Extend `test_home_exposes_learn_repair_backend_and_accessible_results` with these required controls:

```python
self.assertIn('aria-label="90 秒评委导览"', page)
self.assertIn('href="#workspace"', page)
self.assertIn('href="#counterfactual-panel"', page)
self.assertIn('href="#assert-panel"', page)
self.assertIn('href="#witness-panel"', page)
self.assertIn('href="#hybrid-path-panel"', page)
self.assertIn('href="#prompt-contract-panel"', page)
self.assertIn('id="inspect-prompt-contract"', page)
self.assertIn('id="prompt-contract-result"', page)
```

- [ ] **Step 2: Run the home-page test and observe RED**

Run:

```bash
cd starter_kit
python3 -m unittest tests.test_web.WebLabTests.test_home_exposes_learn_repair_backend_and_accessible_results -v
```

Expected: missing evidence-rail and Prompt Contract controls.

- [ ] **Step 3: Add the evidence rail**

Place a `<nav id="judge-tour" aria-label="90 秒评委导览">` after the hero. Add six anchor links. Each link contains a stable status span whose initial text is `未运行`:

```html
<a href="#workspace" data-tour-step="run">运行与 ProofTrace <span id="tour-run-status">未运行</span></a>
<a href="#counterfactual-panel" data-tour-step="compare">首个因果分歧 <span id="tour-compare-status">未运行</span></a>
<a href="#assert-panel" data-tour-step="assert">统计断言 <span id="tour-assert-status">未运行</span></a>
<a href="#witness-panel" data-tour-step="witness">Witness Chain <span id="tour-witness-status">未运行</span></a>
<a href="#hybrid-path-panel" data-tour-step="hybrid">Mid-circuit 路径证书 <span id="tour-hybrid-status">未运行</span></a>
<a href="#prompt-contract-panel" data-tour-step="contract">L2 Prompt Contract <span id="tour-contract-status">未运行</span></a>
```

Use `position: sticky` below the existing masthead. At widths up to 620 px, keep one horizontal row with `overflow-x: auto`, visible focus rings, and no page-level overflow.

- [ ] **Step 4: Add the Prompt Contract panel**

Place `#prompt-contract-panel` immediately before the existing Agent section. Reuse the Agent prompt through a dedicated text input `#contract-prompt` with the default value:

```text
Which free 20-qubit simulator on OriginQ needs no account?
```

Add `#inspect-prompt-contract`, a live status, and `#prompt-contract-result`. Render task kind, state goal, backend constraints, the first 12 characters of `semantic_sha256`, and the verification result. The panel copy must say that the digest detects changes and is not a signature.

- [ ] **Step 5: Implement success-backed tour state**

Add:

```javascript
function markTourStep(step, detail) {
  const status = $(`#tour-${step}-status`);
  status.textContent = `完成 · ${detail}`;
  status.closest("a").classList.add("complete");
}
```

Call it only after the corresponding semantic evidence gate succeeds:

- `/api/run`: require `proof.equivalence.verified === true`, exactly the three declared portability targets, and `roundtrip_verified === true` for every target before `markTourStep("run", "三后端回读")`.
- `/api/compare`: require a non-null `first_divergence` for the default counterexample before `markTourStep("compare", "首门已定位")`; an HTTP 200 response alone is insufficient.
- `/api/assert`: require `mode === "exact-local"`, a non-empty assertion list, recognized `pass | fail | inconclusive` statuses, `evidence_mode === "exact-local"` for each item, and the attribution caveat before `markTourStep("assert", statusSummary)`. A failing scientific assertion is still valid evidence; malformed or unscoped output is not.
- `/api/causal-audit`: require `verification.valid === true` before `markTourStep("witness", "本地重算通过")`.
- `/api/hybrid-paths`: require the response schema `{certificate, verification}`, `verification.valid === true`, and certificate schema `loomq-hybrid-path-certificate-v1` before `markTourStep("hybrid", "语义重算通过")`. Render exhaustive declared-clbit outcomes and dead paths from `certificate`; do not consume the removed projected-bit schema.
- `/api/prompt-contract`: require `verification.valid === true`, contract schema `loomq-prompt-contract-v1`, and `integrity.is_signature === false` before `markTourStep("contract", contract.task_kind)`.

Errors leave the step incomplete and continue through the existing error notice.

- [ ] **Step 6: Run Web tests and JavaScript syntax check**

Run:

```bash
cd starter_kit
python3 -m unittest tests.test_web -v
node --check web/app.js
```

Expected: all tests and syntax checks pass.

- [ ] **Step 7: Commit**

Commit the rail, panel, styles, and tests. Record that progress reflects successful APIs rather than client-side clicks.

---

### Task 3: Ninety-second Judge Script

**Files:**
- Modify: `starter_kit/JUDGE_GUIDE.md`
- Modify: `starter_kit/WEB_QA.md`
- Modify: `starter_kit/README.md`

**Interfaces:**
- Consumes: the six evidence-rail anchors and their real actions.
- Produces: one reproducible sequence requiring no credentials for any of its six steps.

- [ ] **Step 1: Write the judge sequence**

Add a `90 秒页面验收` section to `JUDGE_GUIDE.md` with this order:

1. Run the default Bell circuit and inspect ProofTrace portability plus the state trace.
2. Run the default Bell counterexample and read the first divergent gate.
3. Run the default exact-local support and parity assertions and read their evidence modes and statuses.
4. Generate Witness Chain and confirm local rebuild verification.
5. Generate the default mid-circuit Hybrid path certificate and inspect reachable and unreachable paths.
6. Inspect the default Prompt Contract and confirm that it records a backend task with OriginQ, at least 20 qubits, simulator, free, and no-account constraints, then passes deterministic rebuild verification.

State that all six steps need no API key, and that Prompt Contract inspection does not itself claim a uniquely compatible backend. Keep Agent generation and its separate backend-compatibility validator as an optional seventh step for environments with `LOOMQ_LLM_*` configured.

- [ ] **Step 2: Update Web QA facts**

In `WEB_QA.md`, record the actual viewport checks at 1440×900 and 390×844. Include horizontal-overflow, keyboard focus, console, page, and network error results only after running them. Do not copy historical test counts.

- [ ] **Step 3: Update the README entry point**

Link `JUDGE_GUIDE.md`, `PROMPT_CONTRACT.md`, and the Web start command from one short `评委入口` paragraph. Do not add award predictions or comparative superlatives.

- [ ] **Step 4: Run the anti-AI prose audit**

Use the docs/technical profile. Remove promotional language, rule-of-three slogans, vague claims of innovation, em-dash splices, and repeated contrast templates. Preserve commands, schema names, caveats, and measured results.

- [ ] **Step 5: Commit**

Commit documentation only after commands and viewport evidence are current.

---

### Task 4: Final Browser and Archive Verification

**Files:**
- Modify only if verification exposes a defect: `starter_kit/web/index.html`, `starter_kit/web/app.js`, `starter_kit/web/styles.css`, `starter_kit/tests/test_web.py`
- Modify after final counts are known: `starter_kit/verify_submission.py`

**Interfaces:**
- Consumes: all final APIs, DOM anchors, and archive tests.
- Produces: accepted submission receipt for the final commit.

- [ ] **Step 1: Run the complete local verifier**

Run:

```bash
python3 starter_kit/verify_submission.py
python3 -m unittest discover -s tests -v
cd starter_kit
python3 -m unittest discover -s tests -v
cd ..
node --check starter_kit/web/app.js
git diff --check
```

Expected: every required verifier phase passes; root PyQuafu skips, if any, remain explicitly optional.

- [ ] **Step 2: Run desktop Browser QA**

At 1440×900, execute all six evidence-rail actions. Verify that each semantically valid API changes exactly one rail item to `完成`, the target panel receives focus or scroll position, and console/page/network errors remain empty.

- [ ] **Step 3: Run mobile Browser QA**

At 390×844, verify no horizontal overflow, the rail scrolls horizontally without trapping the page, all buttons retain visible labels and focus, evidence digests wrap, and every target panel remains readable.

- [ ] **Step 4: Request final read-only review**

Review scientific wording, Prompt Contract routing, mid-circuit measurement semantics, API error handling, accessibility, mobile layout, and all judge-guide claims. Resolve every HIGH or MEDIUM finding with a failing test first.

- [ ] **Step 5: Merge, push, and obtain a new receipt**

Merge the verified branch into `main`, push the final commit, run:

```bash
python3 starter_kit/prepare_submission.py --team-id JunkaiWang-TheoPhy
```

Create a new official Final Submission Issue through the repository form. Completion requires `submission:accepted`, the archived commit SHA, archive SHA-256, and Artifact ID. Keep the previous accepted Issue #106 as the fallback until the new receipt exists.

## Self-Review

- Spec coverage: the plan covers discoverability, semantic-evidence-backed progress, exact/statistical assertion visibility, Prompt Contract inspection, server-recomputed mid-circuit evidence, documentation, responsive QA, and official archive acceptance.
- Placeholder scan: no deferred implementation placeholders or unspecified error handling remain.
- Type consistency: tour step names, DOM IDs, routes, and response fields match across tasks.
- Scope: all Web edits wait for the Hybrid integration commit; this plan does not modify the concurrently owned Hybrid worktree.
