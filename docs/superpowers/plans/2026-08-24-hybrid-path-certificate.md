# Hybrid Path Certificate Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn LoomQ's one-outcome Hybrid-QASM replay into a bounded exhaustive certificate that assigns exact quantum probability mass to every classical branch path, exposes unreachable outcomes and dead paths, and lets judges recompute the result.

**Architecture:** A new `loomq.hybrid_paths` module performs exact mid-circuit measurement branching, converts the resulting classical distribution into `c[0]..c[n-1]` replay inputs, reuses `trace_hybrid()` for every bounded assignment, and aggregates outcome-first evidence into path groups. A deterministic verifier recomputes the certificate rather than trusting its checksum. Web/API integration is additive and the final UX pass moves evidence conclusions ahead of internal terminology without changing existing evaluator contracts.

**Tech Stack:** Python 3.10 standard library, existing LoomQ QASM IR/state-vector gate engine/Hybrid compiler/RISC-V trace, `unittest`, vanilla HTML/CSS/JavaScript.

## Global Constraints

- Preserve every official adapter signature and return contract; all new APIs are optional and additive.
- Add no third-party dependency and keep both `starter_kit.*` and extracted `starter_kit/` import modes valid.
- Exact path claims apply only when all `2 ** num_clbits` assignments are replayed; fail closed when the requested bound is insufficient.
- Measurement keys use `c[n-1]...c[0]`; replay arrays use `[c[0], c[1], ...]`; convert in one tested function.
- Mid-circuit measurements are evaluated at their actual operation positions; gates after a measurement cannot retroactively change that classical bit.
- Group paths by source-level branch truth, not inverse RISC-V jump direction. Preserve outcome rows and distinct final-register fingerprints inside each group.
- A SHA-256 field is an integrity checksum, not an authorship signature. Verification must recompute the certificate from source.
- User-facing Chinese states the observable result first. Put schema names, witness IDs, machine fields, and literature terminology in expandable details.
- Remove self-awarded language such as “领先位置”, “系统性创新”, and “10/10”; public competitor facts and private-evaluation uncertainty remain explicit.
- Follow red-green-refactor and Lore commit format. Do not edit unrelated code while cleaning prose or layout.

---

### Task 1: Exact Mid-Circuit Path Certificate

**Files:**
- Modify: `starter_kit/loomq/simulator.py`
- Create: `starter_kit/loomq/hybrid_paths.py`
- Create: `starter_kit/tests/test_hybrid_paths.py`

**Interfaces:**
- Produces: `measurement_branch_probabilities(circuit: Circuit, *, max_branches: int = 256) -> dict[str, float]`
- Produces: `certify_hybrid_paths(source: str, *, max_outcomes: int = 256) -> dict[str, Any]`
- Produces: `verify_hybrid_path_certificate(source: str, certificate: Mapping[str, Any]) -> dict[str, Any]`
- Consumes: `parse_hybrid(source)` and `trace_hybrid(source, measurement_bits)`.

- [ ] **Step 1: Write the failing mid-circuit measurement tests**

Test a circuit that measures `|0>` into `c[0]` and then applies `x q[0]`; the result must remain `{"0": 1.0}`, proving later gates do not rewrite an earlier classical outcome. Add Bell terminal-measurement literals `{"00": 0.5, "11": 0.5}` and a branch-limit failure.

- [ ] **Step 2: Run the focused test and verify RED**

Run: `cd starter_kit && python3 -m unittest tests.test_hybrid_paths -v`

Expected: import failure for `loomq.hybrid_paths` or missing `measurement_branch_probabilities`.

- [ ] **Step 3: Implement bounded exact measurement branching**

Start from `|0...0>`. Apply each existing gate through the simulator's single gate engine. At every `Measurement`, split each live pure-state history into projective `0/1` outcomes, multiply branch weights, normalize the collapsed states, and write the measured value to its declared classical bit. Histories remain separate even if they currently share a classical key. At the end, sum weights by `c[n-1]...c[0]`, drop only exact numerical dust below `1e-15`, normalize within `1e-12`, sort keys, and reject non-positive bounds or more than `max_branches` live histories.

- [ ] **Step 4: Write failing exhaustive path and dead-path tests**

Use a deterministic `|0>` measurement with `if (c[0] == 1)`: outcome `0` has mass `1.0`, outcome `1` has mass `0.0`, and the false source branch is the only reachable path. Add a 2-bit uniform-superposition nested branch, a case where two outcomes share one branch path but produce different final registers, and the literal conversion `"10" -> [0, 1]`.

- [ ] **Step 5: Implement the deterministic certificate**

Require `2 ** num_clbits <= max_outcomes`. Replay every assignment, including zero-probability ones. Emit schema `loomq-hybrid-path-certificate-v1`, source SHA-256, scope and limits, bit-order explanation, sorted `outcomes`, sorted `path_groups`, `unreachable_outcomes`, `dead_path_ids`, and `integrity`. Each outcome includes probability, reachability, source-level branch signature/path, branch events, sparse final registers, and final-register SHA-256. Each path group includes total probability, all outcome keys, reachable outcome keys, and distinct final-register fingerprints. Use canonical JSON (`sort_keys=True`, compact separators, `ensure_ascii=True`) for all digests.

- [ ] **Step 6: Write failing verification/tamper tests**

Repeated certificates must be byte-identical. Verification passes the original, then fails after changing one outcome probability, one branch truth value, or one final register. A source change must fail even if the embedded checksum is copied.

- [ ] **Step 7: Implement recomputation verification and run GREEN**

Validate the schema and stored bound, recompute from the supplied source, compare canonical certificate bodies and checksums, and return JSON-safe fields `valid`, `reason`, `certificate_sha256`, and `recomputed_sha256`. Never accept checksum equality without semantic recomputation.

Run: `cd starter_kit && python3 -m unittest tests.test_hybrid_paths tests.test_hybrid_trace tests.test_state_trace -v`

- [ ] **Step 8: Commit Task 1**

Use a Lore commit whose `Constraint:` records bounded exhaustive enumeration and whose `Not-tested:` excludes loops/recursion and unbounded hybrid programs.

---

### Task 2: Adapter, Web Evidence, and One-Command Verification

**Files:**
- Modify: `starter_kit/adapter.py`
- Modify: `starter_kit/loomq/web.py`
- Modify: `starter_kit/web/index.html`
- Modify: `starter_kit/web/app.js`
- Modify: `starter_kit/web/enhancements.css`
- Modify: `starter_kit/tests/test_web.py`
- Create: `starter_kit/scripts/hybrid_path_benchmark.py`
- Create: `starter_kit/tests/test_hybrid_path_benchmark.py`
- Modify: `starter_kit/verify_submission.py`

**Interfaces:**
- Produces: `adapter.certify_hybrid_paths(hybrid_qasm_str: str, max_outcomes: int = 256) -> dict`
- Produces: bounded `POST /api/hybrid-paths` with `source` and optional integer `max_outcomes`.
- Preserves: `/api/run`, `/api/causal-audit`, `/api/assert`, `/api/hybrid-trace`, and every existing Web workflow.

- [ ] **Step 1: Write failing adapter/API tests**

Assert adapter dual-import behavior, a successful deterministic-program certificate, request-size enforcement, boolean/non-positive/oversized bound rejection, and a `400` response when exhaustive enumeration exceeds the bound.

- [ ] **Step 2: Run focused tests and verify RED**

Run: `python3 -m unittest starter_kit.tests.test_hybrid_paths starter_kit.tests.test_web -v`

- [ ] **Step 3: Implement additive adapter and bounded route**

Use existing JSON/body-size/error response helpers. Do not persist reports. The route returns the certificate plus a verification result produced by recomputation.

- [ ] **Step 4: Write failing browser-contract tests**

The page must offer a plain-language control “列出所有可能分支”, render path probability, reachable/unreachable status, dead paths, and provide a JSON download. Technical branch events and hashes belong inside `details`. Static tests must also lock an early-page anchor to this evidence.

- [ ] **Step 5: Implement the judge-facing path view**

Add one compact evidence card, not another full product section. Default to the existing Hybrid example. Show “这条路径会发生 / 在当前量子态下不会发生”, a probability bar, referenced outcome keys, and distinct final results. Keep source truth separate from machine jumps in the technical disclosure. Preserve 390px no-horizontal-overflow behavior.

- [ ] **Step 6: Add a deterministic benchmark phase**

The benchmark runs at least four hand-derived fixtures: deterministic dead branch, Bell two-path mass, nested full-support paths, and same-path/different-final-register outcomes. It verifies total probability `1.0 ± 1e-12`, recomputation validity, fixed expected live/dead counts, and rejects at least one tampered certificate per fixture. Print one JSON summary with fixed corpus SHA-256. Add it as required phase `hybrid-path-certificate` in the one-command verifier.

- [ ] **Step 7: Run GREEN and commit Task 2**

Run: `python3 -m unittest starter_kit.tests.test_hybrid_paths starter_kit.tests.test_hybrid_path_benchmark starter_kit.tests.test_web -v`

Run: `node --check starter_kit/web/app.js`

Use a Lore commit whose `Directive:` says path mass is exact only under the recorded exhaustive bound.

---

### Task 3: Evidence-First UX and Anti-AI Cleanup

**Files:**
- Modify: `starter_kit/web/index.html`
- Modify: `starter_kit/web/enhancements.css`
- Modify: `starter_kit/web/app.js` only if anchor/focus behavior requires it
- Modify: `starter_kit/tests/test_web.py`
- Modify: `starter_kit/JUDGE_GUIDE.md`
- Modify: `starter_kit/README.md`
- Modify: `starter_kit/evidence/README.md`
- Modify: `starter_kit/COMPETITIVE_COVERAGE.md`
- Modify: `starter_kit/WITNESS_CHAIN.md`
- Modify: `starter_kit/WEB_QA.md`

**Interfaces:**
- Consumes all existing P0/P1/P2/Witness/path evidence without changing schemas.
- Produces a first-screen evidence navigator and a natural-language judge walkthrough.

- [ ] **Step 1: Lock existing Web behavior before cleanup**

Run the complete Web suite. Add behavior tests only for missing navigation/focus contracts: first-screen links reach evidence, runnable example, and raw technical details; existing controls remain present and usable.

- [ ] **Step 2: Write the cleanup plan in the Task 3 report before editing**

Categorize exact smells: evidence below the fold, internal terminology before conclusions, repeated three-part templates, self-awarded score/leadership language, duplicated explanation, and generic SaaS-card hierarchy. Bound changes to the listed files. Order passes: evidence navigation, terminology, promotional copy deletion, duplication, mobile/browser verification.

- [ ] **Step 3: Make evidence discoverable before feature inventory**

Under the hero, add three direct choices: “1 分钟看证据”, “3 分钟跑示例”, “查看原始材料”. Follow with three short questions rather than capability names: “编译有没有改坏电路?”, “测量后程序会走哪条路?”, “不会 QASM 能不能用?”. Each links to the existing proof, new path certificate, or Agent workflow. Do not duplicate full reports.

- [ ] **Step 4: Replace internal-first copy**

Use these exact user-facing labels where applicable: `量子电路实验台`, `ProofTrace：这次结果为什么可信`, `删掉一扇门，结果从哪一步开始变?`, `用同一组证据编号串起源门、测量和经典分支`, `断言与分支证据`, `列出所有可能分支`. Keep `machine_jump_taken`, witness IDs, schema versions, and hashes inside expandable technical details.

- [ ] **Step 5: Remove promotional and AI-template prose**

Delete or replace unsupported/self-awarded phrases including `领先位置`, `系统性创新`, `10/10`, `不仅…而且…`, repeated `生成、修复、选择` triads, and generic conclusions. State concrete counts, commands, hashes, public commit SHAs, and limitations. Preserve competitor facts but do not make winning claims.

- [ ] **Step 6: Run visual and prose gates**

Run the Web suite and `node --check`. Launch the real server and test 1440px and 390px: `scrollWidth === innerWidth`, no console/page/network errors, keyboard focus reaches the three navigator links, and the full proof/path/Agent flows still run. Save screenshots under `/tmp` only. Apply the humanizer scorecard to changed Chinese prose and require at least 45/50 for directness, rhythm, trust, authenticity, and concision.

- [ ] **Step 7: Run all gates and commit Task 3**

Run: `python3 starter_kit/verify_submission.py`

Run: `python3 -m unittest discover -s tests`

Run: `cd starter_kit && python3 -m unittest discover -s tests`

Run: `git diff --check`

Use a Lore commit that lists the browser viewports and explicitly states that screenshots are QA artifacts, not scoring proof.
