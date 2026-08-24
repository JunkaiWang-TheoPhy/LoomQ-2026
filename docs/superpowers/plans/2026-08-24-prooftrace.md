# ProofTrace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn LoomQ into a proof-carrying multi-backend compiler that safely optimizes circuits, records gate lineage, exposes a deterministic certificate, and quantifies defect detection with a mutation benchmark.

**Architecture:** A new dependency-free `loomq.prooftrace` module owns annotated rewrite rules, deterministic circuit metrics, native-IR portability checks, and JSON-safe certificates. `adapter.transpile()` delegates to this compiler without changing its return contract; a new `adapter.prooftrace()` exposes the certificate. The Web API returns the same certificate, and a deterministic benchmark validates that corrupted native outputs and semantic circuit mutations are rejected.

**Tech Stack:** Python 3.10 standard library, existing LoomQ Circuit IR/simulator/native parsers, `unittest`, vanilla JavaScript.

## Global Constraints

- Preserve the official `adapter.transpile(qasm_str, target) -> str` and `adapter.run(qasm_str, target, shots) -> dict` contracts.
- Generated OpenQASM 2.0 may use only `h, x, s, sdg, t, tdg, rz, ry, cx, cu1, swap, ccx`.
- Add no third-party dependency and keep formal execution valid from an extracted `starter_kit/` root.
- Every optimization must be justified by a named, semantics-preserving rewrite; measurements and their order may never be changed.
- Certificates must distinguish universal rewrite equivalence from target-state or sampled-distribution evidence.
- Certificate output must be deterministic and JSON-safe; do not include wall-clock timestamps, credentials, or fabricated provider metadata.
- Follow red-green-refactor for every new production behavior.

## Coordination Boundary

This thread implements Tasks 1, 3, and 4 only. Task 2 (statistical assertions and first-divergence diagnostics), hardware-deviation diagnosis, and Hybrid-QASM/RISC-V branch tracing are owned by a separate coordinated task and must not be modified here.

---

### Task 1: Safe Rewrites, Gate Lineage, and Certificates

**Files:**
- Create: `starter_kit/loomq/prooftrace.py`
- Create: `starter_kit/tests/test_prooftrace.py`
- Modify: `starter_kit/adapter.py`
- Modify: `starter_kit/loomq/runtime.py`

**Interfaces:**
- Produces: `compile_with_proof(qasm_str: str, target: str) -> tuple[str, dict]`
- Produces: `optimize_circuit(circuit: Circuit) -> tuple[Circuit, list[dict], list[list[int]]]`
- Produces: `adapter.prooftrace(qasm_str: str, target: str) -> dict`
- Preserves: `adapter.transpile(...) -> str`

- [ ] **Step 1: Write failing optimizer tests**

```python
def test_inverse_pairs_are_removed_with_source_lineage():
    native, certificate = adapter.transpile_with_proof(REDUNDANT_BELL, "originq")
    self.assertNotIn("H q[0]\nH q[0]", native)
    self.assertEqual(certificate["equivalence"]["method"], "verified-local-rewrites-v1")
    self.assertEqual(certificate["metrics"]["source"]["gate_count"], 4)
    self.assertEqual(certificate["metrics"]["optimized"]["gate_count"], 2)
    self.assertEqual(certificate["rewrites"][0]["rule"], "cancel-self-inverse")
```

- [ ] **Step 2: Run the focused test and confirm it fails because the API is absent**

Run: `cd starter_kit && python3 -m unittest tests.test_prooftrace -v`

- [ ] **Step 3: Implement annotated adjacent rewrites**

Implement cancellation for adjacent `h/h`, `x/x`, `cx/cx`, `swap/swap`, and `ccx/ccx`; inverse cancellation for `s/sdg` and `t/tdg`; and angle merging for adjacent equal `rz`, `ry`, or `cu1` operands. Record source operation indices in every rewrite and every surviving operation. Never rewrite across a measurement.

- [ ] **Step 4: Implement deterministic metrics and certificates**

Certificate schema must include `schema_version`, source/optimized SHA-256, `equivalence`, source/optimized metrics, rewrites, final gate lineage, and a `portability` entry for each of `spinq`, `originq`, and `braket`. Each portability entry must contain the native SHA-256 and a successful independent parse flag.

- [ ] **Step 5: Route public transpilation through ProofTrace**

`adapter.transpile()` returns only the selected native IR; `adapter.transpile_with_proof()` returns `(native_ir, certificate)`; `adapter.prooftrace()` returns only the certificate. The runtime metadata reports optimized gate count without changing counts semantics.

- [ ] **Step 6: Run focused and existing native-IR tests**

Run: `cd starter_kit && python3 -m unittest tests.test_prooftrace tests.test_native_ir_verifier tests.test_algorithm_gallery -v`

---

### Task 2: First-Divergence Diagnostics and Statistical Assertions

**Files:**
- Modify: `starter_kit/loomq/prooftrace.py`
- Modify: `starter_kit/tests/test_prooftrace.py`

**Interfaces:**
- Produces: `evaluate_assertions(circuit: Circuit, assertions: list[dict]) -> list[dict]`
- Produces: `diagnose_mutation(reference_qasm: str, candidate_qasm: str) -> dict`

- [ ] **Step 1: Write failing assertion and mutation tests**

```python
def test_bell_support_and_parity_assertions_are_machine_checkable():
    report = evaluate_assertions(parse_qasm(BELL), [
        {"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999},
        {"kind": "parity", "qubits": [0, 1], "expected": "even", "minimum_probability": 0.999},
    ])
    self.assertTrue(all(item["passed"] for item in report))

def test_mutated_bell_reports_first_divergent_gate():
    report = diagnose_mutation(BELL, BELL.replace("cx q[0],q[1];", "x q[1];"))
    self.assertFalse(report["equivalent_output_distribution"])
    self.assertEqual(report["first_divergent_gate"], 1)
```

- [ ] **Step 2: Run and observe the expected missing-function failures**

Run: `cd starter_kit && python3 -m unittest tests.test_prooftrace -v`

- [ ] **Step 3: Implement support, parity, and uniformity assertions**

All reports include `kind`, `passed`, `observed`, `threshold`, and a plain-language explanation. Assertions operate on exact local probabilities and must reject malformed bit strings, invalid qubits, or thresholds outside `[0, 1]`.

- [ ] **Step 4: Implement bounded first-divergence diagnosis**

For circuits up to eight qubits, compare exact per-gate state snapshots after aligning operations by index. Report the first gate whose basis probabilities or relative amplitudes differ. If declarations or measurements differ, return that structural mismatch before simulating. Do not label a hardware deviation as a specific noise mechanism.

- [ ] **Step 5: Run focused tests**

Run: `cd starter_kit && python3 -m unittest tests.test_prooftrace tests.test_state_trace -v`

---

### Task 3: Web Proof Panel and Evidence Export

**Files:**
- Modify: `starter_kit/loomq/web.py`
- Modify: `starter_kit/web/index.html`
- Modify: `starter_kit/web/app.js`
- Modify: `starter_kit/web/styles.css`
- Modify: `starter_kit/tests/test_web.py`

**Interfaces:**
- Consumes: `adapter.transpile_with_proof(...)`
- Produces: `/api/run` response field `proof`

- [ ] **Step 1: Write failing Web API and asset tests**

Assert that `/api/run` returns a proof with verified three-target portability, and that the page contains `id="proof-panel"`, a certificate download control, rewrite count, metric deltas, and semantic-scope text.

- [ ] **Step 2: Run Web tests and confirm the new contract is absent**

Run: `cd starter_kit && python3 -m unittest tests.test_web -v`

- [ ] **Step 3: Return the proof from the existing run endpoint**

Use one `transpile_with_proof()` call so the selected native IR and certificate cannot diverge.

- [ ] **Step 4: Render the proof panel**

Show verified targets, gate/depth/two-qubit deltas, named rewrites, and the exact equivalence scope. Add a JSON download built from the response object; do not persist it server-side.

- [ ] **Step 5: Run Web tests and JavaScript syntax check**

Run: `cd starter_kit && python3 -m unittest tests.test_web -v`

Run: `node --check starter_kit/web/app.js`

---

### Task 4: Mutation Benchmark and Judge-Facing Evidence

**Files:**
- Create: `starter_kit/scripts/prooftrace_benchmark.py`
- Create: `starter_kit/tests/test_prooftrace_benchmark.py`
- Create: `starter_kit/PROOFTRACE.md`
- Modify: `starter_kit/JUDGE_GUIDE.md`
- Modify: `starter_kit/ARCHITECTURE.md`
- Modify: `starter_kit/evidence/README.md`
- Modify: `starter_kit/verify_submission.py`

**Interfaces:**
- Produces: `python3 -m scripts.prooftrace_benchmark --json`
- Produces JSON fields: `total_mutants`, `detected_mutants`, `false_accepts`, `portability_checks`, `rewrite_checks`, and `passed`

- [ ] **Step 1: Write a failing benchmark contract test**

Generate deterministic deletion, replacement, operand, and angle mutations from the archived Bell/GHZ/Deutsch/Grover/QFT circuits. Assert at least 200 unique mutants, zero false accepts against their declared reference behavior, and successful certificates for every unmodified circuit across all targets.

- [ ] **Step 2: Run and confirm the benchmark module is absent**

Run: `cd starter_kit && python3 -m unittest tests.test_prooftrace_benchmark -v`

- [ ] **Step 3: Implement deterministic mutation generation and reporting**

Bind the corpus to a fixed SHA-256 and record each failure with circuit, mutation kind, and diagnostic. The benchmark must execute assertions rather than count loop iterations.

- [ ] **Step 4: Document claims and limitations**

State that rewrite certificates prove only the named local identities and unchanged measurement mapping; mutation detection rates apply only to the committed corpus; real DeepSeek repair rates remain unclaimed without credentials.

- [ ] **Step 5: Add the benchmark to one-command verification**

Run it as a credential-free phase in `verify_submission.py`.

- [ ] **Step 6: Run complete verification**

Run: `python3 starter_kit/verify_submission.py`

Run: `python3 -m unittest discover -s tests -v`

Run: `git diff --check`
