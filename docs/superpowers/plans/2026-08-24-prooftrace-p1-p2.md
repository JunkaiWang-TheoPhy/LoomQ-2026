# ProofTrace P1/P2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add machine-checkable statistical assertions, bounded first-divergence diagnostics, cautious hardware-deviation classification, and replayable Hybrid-QASM/RISC-V branch traces without changing the official adapter contracts.

**Architecture:** P1 lives in a dependency-free `loomq.assertions` module so it can later be consumed by the parallel ProofTrace certificate work without sharing implementation files. P2 adds trace capture to the existing RISC-V emulator and a separate `loomq.hybrid_trace` orchestration module; the official `compile_hybrid()` tuple remains unchanged while a new optional `adapter.trace_hybrid()` exposes the replay report. Web integration happens only after the parallel P0 branch is rebased, avoiding conflicting edits.

**Tech Stack:** Python 3.10 standard library, existing LoomQ QASM parser/state-vector simulator/Hybrid compiler/RISC-V emulator, `unittest`, vanilla JavaScript.

## Global Constraints

- Preserve `adapter.transpile`, `adapter.run`, `adapter.agent_chat`, and `adapter.compile_hybrid` signatures and return contracts.
- Add no third-party dependencies and keep imports valid both as `starter_kit.*` and from an extracted `starter_kit/` working root.
- Assertion reports must be deterministic and JSON-safe; exact local evidence and finite-shot statistical evidence must be labeled separately.
- Hardware diagnosis may say `execution-deviation-detected` but must never infer a specific physical noise mechanism.
- First-divergence diagnosis is exact only for circuits with at most 8 qubits and must compare relative amplitudes up to global phase.
- RISC-V trace capture must preserve existing emulator results, x0 semantics, step limits, and official assembly support.
- Follow red-green-refactor for every production behavior and use Lore-format commit messages.

---

### Task 1: Statistical Assertions and First-Divergence Diagnostics

**Files:**
- Modify: `starter_kit/loomq/simulator.py`
- Create: `starter_kit/loomq/assertions.py`
- Create: `starter_kit/tests/test_assertions.py`

**Interfaces:**
- Produces: `evaluate_assertions(circuit: Circuit, assertions: list[dict]) -> list[dict]`
- Produces: `evaluate_distribution_assertions(distribution: Mapping[str, float | int], assertions: list[dict], *, shots: int | None = None, confidence: float = 0.95) -> list[dict]`
- Produces: `diagnose_mutation(reference_qasm: str, candidate_qasm: str) -> dict`
- Produces: `diagnose_observed_execution(circuit: Circuit, observed: Mapping[str, float | int], assertions: list[dict], *, shots: int | None = None) -> dict`

- [ ] **Step 1: Write failing exact-assertion tests**

```python
def test_bell_support_parity_and_uniformity_are_machine_checkable():
    bell = parse_qasm(BELL)
    report = evaluate_assertions(bell, [
        {"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999},
        {"kind": "parity", "bits": [0, 1], "expected": "even", "minimum_probability": 0.999},
        {"kind": "uniformity", "states": ["00", "11"], "maximum_total_variation": 1e-12},
    ])
    self.assertEqual([item["status"] for item in report], ["pass", "pass", "pass"])
    self.assertTrue(all(item["evidence_mode"] == "exact-local" for item in report))
```

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd starter_kit && python3 -m unittest tests.test_assertions -v`

Expected: import failure for `loomq.assertions`.

- [ ] **Step 3: Implement schema validation and exact assertions**

Support computes probability mass inside an explicit state set. Parity interprets bit index 0 as the rightmost classical bit and computes even/odd event mass. Uniformity computes total-variation distance from a uniform distribution over the declared states. Reject duplicate/malformed states, mixed key widths, invalid bit indices, empty state sets, thresholds outside `[0, 1]`, unsupported kinds, booleans used as numbers, and non-normalizable distributions.

- [ ] **Step 4: Write failing finite-shot statistical tests**

```python
def test_counts_use_confidence_bounds_and_can_be_inconclusive():
    report = evaluate_distribution_assertions(
        {"00": 48, "11": 47, "01": 3, "10": 2},
        [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}],
        shots=100,
    )
    self.assertEqual(report[0]["evidence_mode"], "finite-shots")
    self.assertEqual(report[0]["status"], "inconclusive")
    self.assertIn("confidence_interval", report[0])
```

- [ ] **Step 5: Implement finite-shot bounds**

Use a two-sided Wilson interval for support/parity event mass. For uniformity, use a conservative Hoeffding union-bound radius `k * sqrt(log(2*k/alpha)/(2*shots)) / 2` around empirical total variation. Return `pass` only when the entire confidence interval satisfies the assertion, `fail` only when it entirely violates it, otherwise `inconclusive`. Provider probabilities without `shots` are labeled `provider-probabilities` and receive no fabricated confidence interval.

- [ ] **Step 6: Write failing first-divergence and hardware-diagnosis tests**

```python
def test_mutated_bell_reports_first_divergent_gate():
    report = diagnose_mutation(BELL, BELL.replace("cx q[0],q[1];", "x q[1];"))
    self.assertFalse(report["equivalent_output_distribution"])
    self.assertEqual(report["first_divergent_gate"], 1)
    self.assertEqual(report["scope"], "exact-up-to-global-phase-at-zero-input")

def test_hardware_failure_is_not_mislabeled_as_a_noise_mechanism():
    report = diagnose_observed_execution(
        parse_qasm(BELL), {"00": 55, "01": 45},
        [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.90}],
        shots=100,
    )
    self.assertEqual(report["classification"], "execution-deviation-detected")
    self.assertNotIn("depolarizing", json.dumps(report).lower())
```

- [ ] **Step 7: Implement bounded diagnosis and run GREEN**

Extract one internal exact state-step iterator in `simulator.py`; make the existing rounded/truncated `trace_statevector()` presentation helper consume it so gate semantics are not duplicated. For declarations/measurement mapping differences, return a structural mismatch without simulation. For up to 8 qubits, compare complete, unrounded per-gate state snapshots after canonicalizing global phase; report the first differing gate, operations, maximum amplitude delta, and final distribution distance. Do not conflate pre-measurement quantum basis states with the simulator's final classical-bit distribution. Hardware diagnosis first verifies that the local reference satisfies the assertions, then classifies the observed report as `consistent-with-reference`, `execution-deviation-detected`, `inconclusive`, or `reference-program-fails` with an explicit non-attribution caveat.

Run: `cd starter_kit && python3 -m unittest tests.test_assertions tests.test_state_trace tests.test_hardware_evidence -v`

- [ ] **Step 8: Commit Task 1**

Use a Lore commit whose `Tested:` trailer names the focused suites.

---

### Task 2: Instruction-Level RISC-V Trace Capture

**Files:**
- Modify: `starter_kit/riscv_emulator.py`
- Create: `starter_kit/tests/test_riscv_trace.py`

**Interfaces:**
- Produces: `TinyRISCVEmulator.execute_with_trace() -> dict`
- Produces: `TinyRISCVEmulator.replay_trace(trace: Mapping) -> dict`
- Preserves: `TinyRISCVEmulator.execute() -> dict[str, int]`

- [ ] **Step 1: Write failing instruction-trace tests**

```python
def test_branch_trace_records_decision_register_delta_and_pc():
    emulator = TinyRISCVEmulator()
    emulator.load_program("li x1, 1\nli x2, 1\nbne x1, x2, ELSE\nli x3, 7\nj END\nELSE:\nli x3, 9\nEND:\n")
    report = emulator.execute_with_trace()
    branch = next(event for event in report["events"] if event["operation"] == "bne")
    self.assertFalse(branch["branch"]["taken"])
    self.assertEqual(branch["pc"], 2)
    self.assertEqual(report["final_registers"]["x3"], 7)
```

- [ ] **Step 2: Run and verify RED**

Run: `cd starter_kit && python3 -m unittest tests.test_riscv_trace -v`

Expected: `execute_with_trace` is absent.

- [ ] **Step 3: Refactor execution through one private engine**

Create `_execute(capture_trace: bool)`. Each event contains `step`, `pc` (explicitly documented as an instruction index, not an RV32 byte address), `operation`, `args`, `register_changes`, `branch`, and `next_pc`. Conditional branches record compared register names/values, target label/PC, and `taken`; `j` records an unconditional taken jump. `execute()` returns exactly its old non-zero-register dictionary, while `execute_with_trace()` returns `schema_version`, a deterministic `program_digest`, `initial_registers`, `events`, `branches`, `final_registers`, `steps`, and `terminated=True`.

- [ ] **Step 4: Test error and state-reset compatibility**

Add cases for a taken branch, undefined labels, step limit, x0 immutability, equality between `execute()` and `execute_with_trace()["final_registers"]` on separate emulators loaded with the same program, deterministic replay, and explicit rejection when the loaded program or supplied trace was changed. Loading a new program must clear stale program-associated state.

- [ ] **Step 5: Run focused and existing emulator tests**

Run: `python3 -m unittest starter_kit.tests.test_archive_core tests.test_hybrid tests.test_quantum_riscv starter_kit.tests.test_riscv_trace -v`

- [ ] **Step 6: Commit Task 2**

Use a Lore commit whose `Directive:` says execution and trace must continue sharing one instruction engine.

---

### Task 3: Hybrid-QASM Replay Report

**Files:**
- Modify: `starter_kit/loomq/hybrid.py`
- Create: `starter_kit/loomq/hybrid_trace.py`
- Modify: `starter_kit/adapter.py`
- Create: `starter_kit/tests/test_hybrid_trace.py`

**Interfaces:**
- Produces: `parse_hybrid(source: str) -> tuple[Circuit, list[Statement]]`
- Produces: `trace_hybrid(source: str, measurement_bits: Sequence[int]) -> dict`
- Produces: `adapter.trace_hybrid(hybrid_qasm_str: str, measurement_bits: Sequence[int]) -> dict`
- Preserves: `adapter.compile_hybrid(...) -> tuple[list[str], str]`

- [ ] **Step 1: Write failing replay tests**

```python
def test_hybrid_trace_replays_true_and_false_paths():
    true_report = adapter.trace_hybrid(HYBRID, [1, 1])
    false_report = adapter.trace_hybrid(HYBRID, [1, 0])
    self.assertEqual(true_report["final_registers"]["x3"], 12)
    self.assertEqual(false_report["final_registers"]["x3"], 2)
    self.assertNotEqual(true_report["branch_path"], false_report["branch_path"])
    self.assertTrue(all(item["word"].startswith("0x") for item in true_report["quantum_machine_trace"]))
```

- [ ] **Step 2: Run and verify RED**

Run: `cd starter_kit && python3 -m unittest tests.test_hybrid_trace -v`

- [ ] **Step 3: Expose parsed Hybrid program without duplicating parsing**

Move the existing validation/parsing sequence into `parse_hybrid`; make `compile_hybrid` consume it. Preserve assembly and quantum-operation text byte-for-byte for existing inputs.

- [ ] **Step 4: Implement replay orchestration**

Validate that `measurement_bits` is a non-string sequence whose length equals `num_clbits` and values are integer `0`/`1` but not booleans. Load `c[i]` into `x10+i` only for representable measurement registers; never infer a single replay input from aggregate quantum counts. Execute the shared RISC-V trace engine and return `schema_version`, measurement inputs, quantum operations, quantum custom-0 machine words with decoded operations, assembly, instruction events, compact branch path, and final registers. Track lightweight register provenance through `addi`, `add`, and `sub` so each conditional branch identifies the `c[i]` measurements that influenced it. Keep machine-level `branch.taken` distinct from whether the source-level `if` condition was true, because the compiler lowers source conditions as an inverse jump to the else label.

- [ ] **Step 5: Add nested-branch, validation, and determinism tests**

Assert nested true/false paths, repeated-call equality, incorrect input length/value rejection, unchanged `compile_hybrid` output, exact custom-0 word round-trip, measurement provenance through compiler temporaries, and distinct source-condition versus machine-jump truth labels.

- [ ] **Step 6: Run focused and all L3/Bonus tests**

Run: `cd starter_kit && python3 -m unittest tests.test_hybrid_trace tests.test_riscv_trace tests.test_archive_core -v`

Run: `python3 -m unittest tests.test_hybrid tests.test_quantum_riscv -v`

- [ ] **Step 7: Commit Task 3**

Use a Lore commit that records the optional nature of `trace_hybrid` and the unchanged official tuple contract.

---

### Task 4: P0 Integration, Web Replay, and Judge Evidence

**Files:**
- Modify after rebasing P0: `starter_kit/loomq/web.py`
- Modify after rebasing P0: `starter_kit/web/index.html`
- Modify after rebasing P0: `starter_kit/web/app.js`
- Modify after rebasing P0: `starter_kit/web/styles.css`
- Modify: `starter_kit/tests/test_web.py`
- Modify: `starter_kit/JUDGE_GUIDE.md`
- Modify: `starter_kit/ARCHITECTURE.md`
- Modify: `starter_kit/SCIENTIFIC_CLAIMS_AUDIT.md`
- Modify: `starter_kit/COMPETITIVE_COVERAGE.md`
- Modify: `starter_kit/evidence/README.md`
- Modify: `starter_kit/verify_submission.py`

**Interfaces:**
- Consumes the P0 ProofTrace certificate API after rebase.
- Produces `/api/assert` and `/api/hybrid-trace` or equivalent bounded POST routes.

- [ ] **Step 1: Rebase onto the referenced task's completed P0 commit**

Resolve only genuine integration overlap; preserve the independently reviewed P1/P2 modules and tests.

- [ ] **Step 2: Write failing API and static-asset tests**

Assert a Bell assertion request returns exact-local reports; a Hybrid replay request returns branch events; the page includes an assertion report panel and branch timeline with explicit “不归因具体噪声机制” copy.

- [ ] **Step 3: Implement bounded JSON routes and UI**

Enforce existing request-size limits. Render pass/fail/inconclusive distinctly, show finite-shot confidence bounds only when available, and display PC/operation/branch/register deltas for Hybrid replay. Do not add server-side persistence.

- [ ] **Step 4: Document evidence and limitations**

Document exact vs finite-shot vs provider-probability evidence, the 8-qubit first-divergence bound, bit ordering, optional `trace_hybrid`, and non-attribution of hardware deviations. Update archived test counts only after discovery provides the exact number. Expand competitive coverage to at least six audited teams: Huxingyu #85 (`d6cc922`) is the highest-priority public competitor, alongside Duanice #89 (`e306067`), UokyI #82, orange-city #77, and the previously audited entries. Record ProofTrace's verified rewrite-check count as 132 and the evidence quick-index engineering/product score as 10/10. Claim only leadership in publicly auditable capability coverage; explicitly state that the private 12-case DeepSeek evaluation and unpublished entrants remain unknown.

- [ ] **Step 5: Add focused suites to one-command verification and run all gates**

Run: `python3 starter_kit/verify_submission.py`

Run: `python3 -m unittest discover -s tests -v`

Run: `node --check starter_kit/web/app.js`

Run: `git diff --check`

- [ ] **Step 6: Final review and integration commit**

Require a broad code review with no Critical/Important findings, a clean worktree, and a Lore commit listing every verification command and external-evidence limitation.
