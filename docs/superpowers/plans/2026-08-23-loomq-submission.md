# LoomQ Competition Submission Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build, verify, push, and formally submit a competitive LoomQ implementation covering the required L1 contract, the L2 agent, a usable beginner interface, and—after the safe submission baseline—the deterministic L3 compiler.

**Architecture:** Parse the bounded OpenQASM 2.0 subset into a typed intermediate representation, emit each official target IR from that representation, and execute circuits with a deterministic local state-vector engine so every target has identical normalized semantics. The L2 adapter calls the organizer-provided OpenAI-compatible model through environment configuration, supplies the official backend capability table, validates generated QASM, and retries once with concrete diagnostics. A small standard-library CLI exposes generation, repair, backend recommendation, transpilation, execution, and beginner-facing explanations without introducing a web dependency.

**Tech Stack:** Python 3.10 standard library, `unittest`, official LoomQ evaluator, Docker; optional pinned platform SDKs only after the dependency-free contract is green.

## Global Constraints

- Preserve contract version `1.0` and Starter Kit version `1.1.0`.
- Keep `starter_kit/` as the build and evaluation root.
- Support only the official 12-gate L1 whitelist: `h x s sdg t tdg rz ry cx cu1 swap ccx`.
- `transpile()` targets remain exactly `spinq`, `originq`, and `braket`.
- Normalize counts to `bit_order: little`, with the rightmost bit representing `c[0]`.
- Read L2 service configuration only from `LOOMQ_LLM_*`; never commit or print credentials.
- Pin every third-party dependency exactly; prefer no dependency for the scored baseline.
- Keep the archived submission below 100 MiB.
- Submit from GitHub account and fork owner `JunkaiWang-TheoPhy` before `2026-08-25 12:00 UTC+8`.

## Pre-Implementation Reference Review (2026-08-23)

| Project | Stack and approach | Maintenance evidence | Reusable design | Do not copy |
|---|---|---|---|---|
| `ScQ-Cloud/pyquafu` | Python SDK; circuit model, OpenQASM import, local simulator, Quafu hardware task API | pushed 2025-12-22, repository updated 2026-07-25 | explicit circuit model and a separate task/backend boundary | persistent token handling and Quafu-specific backend semantics cannot replace the official targets |
| `pnnl/qasmtrans` | dependency-free C++ QASM parser/transpiler with target device emitters | pushed 2025-12-03, updated 2026-03-27 | parser → IR → target-emitter separation | its full topology/routing system is unnecessary for the bounded contest grammar |
| `openqasm/openqasm` | language specification and implementation registry | pushed 2026-08-17, updated 2026-08-21 | follow language grammar and explicit measurement/register semantics | OpenQASM 3's complete grammar would add risk beyond the contest subset |

Sources: <https://github.com/ScQ-Cloud/pyquafu>, <https://github.com/pnnl/qasmtrans>, <https://github.com/openqasm/openqasm>.

---

### Task 1: Lock the QASM Parser and IR Contract

**Files:**
- Create: `starter_kit/loomq/qasm.py`
- Create: `starter_kit/loomq/__init__.py`
- Create: `tests/test_qasm.py`

**Interfaces:**
- Consumes: OpenQASM 2.0 source strings using the official gate subset.
- Produces: `parse_qasm(source: str) -> Circuit`, `Circuit.to_qasm2() -> str`, typed `Gate` and `Measurement` records.

- [ ] Write failing tests for declarations, comments, parameter expressions, register-wide operands, measurements, unsupported statements, and invalid indices.
- [ ] Run `python3 -m unittest tests.test_qasm -v` and confirm failures are caused by the missing module.
- [ ] Implement the tokenizer, bounded parser, validation, and canonical QASM 2 emitter.
- [ ] Run `python3 -m unittest tests.test_qasm -v` and confirm all parser tests pass.
- [ ] Commit the parser slice with Lore trailers and exact test evidence.

### Task 2: Implement Target Emitters

**Files:**
- Create: `starter_kit/loomq/emitters.py`
- Create: `tests/test_emitters.py`
- Modify: `starter_kit/adapter.py`

**Interfaces:**
- Consumes: `Circuit` from Task 1 and target string.
- Produces: `emit(circuit: Circuit, target: str) -> str` and working `adapter.transpile()`.

- [ ] Write failing tests for complete SpinQ QASM 2, Braket QASM 3, and OriginIR output across every gate and measurement.
- [ ] Run `python3 -m unittest tests.test_emitters -v` and confirm expected failures.
- [ ] Implement table-driven emitters and target validation.
- [ ] Wire `adapter.transpile()` to parser and emitters.
- [ ] Run emitter tests and the official L1 transpile checks.
- [ ] Commit the emitter slice with Lore trailers.

### Task 3: Implement the State-Vector Runtime and Result Normalization

**Files:**
- Create: `starter_kit/loomq/simulator.py`
- Create: `starter_kit/loomq/runtime.py`
- Create: `tests/test_simulator.py`
- Modify: `starter_kit/adapter.py`

**Interfaces:**
- Consumes: `Circuit`, target, and positive shot count.
- Produces: exact probabilities and deterministic integer counts summing to shots; official result schema from `adapter.run()`.

- [ ] Write failing tests for all 12 gates, Bell/GHZ/QFT behavior, measurement mapping, little-endian keys, deterministic apportionment, and invalid shots.
- [ ] Run `python3 -m unittest tests.test_simulator -v` and confirm failures are caused by missing runtime behavior.
- [ ] Implement gate application and exact state-vector simulation without third-party dependencies.
- [ ] Implement largest-remainder conversion from probabilities to integer counts.
- [ ] Wire `adapter.run()` with target-specific backend names, non-mock local job IDs, UTC timestamps, and metadata.
- [ ] Run unit tests and `python3 starter_kit/evaluator.py --level l1 --target spinq,originq,braket`.
- [ ] Commit the runtime slice with Lore trailers.

### Task 4: Implement the L2 Agent and Output Guardrails

**Files:**
- Create: `starter_kit/loomq/agent.py`
- Create: `tests/test_agent.py`
- Modify: `starter_kit/adapter.py`
- Modify: `starter_kit/submission.yaml`

**Interfaces:**
- Consumes: natural-language prompt and `LOOMQ_LLM_*` environment.
- Produces: `agent_chat(prompt: str) -> str` containing valid QASM or a canonical backend identifier.

- [ ] Write failing local HTTP-server tests proving an actual model call, capability-table grounding, QASM validation, one diagnostic retry, and credential-safe errors.
- [ ] Run `python3 -m unittest tests.test_agent -v` and confirm expected failures.
- [ ] Implement system instructions, capability-table loading, response extraction, validation, and bounded retry.
- [ ] Enable L2 and its formal network flag in `submission.yaml`.
- [ ] Run agent tests, `tests/test_l2_contract.py`, and the official L2 evaluator against a local compatible server.
- [ ] Commit the L2 slice with Lore trailers.

### Task 5: Add a Beginner-Facing CLI and Evidence

**Files:**
- Create: `starter_kit/loomq_cli.py`
- Create: `tests/test_cli.py`
- Create: `starter_kit/ARCHITECTURE.md`
- Modify: `starter_kit/README.md`
- Modify: `starter_kit/evidence/README.md`

**Interfaces:**
- Consumes: QASM files or natural-language prompts.
- Produces: CLI commands `transpile`, `run`, and `chat`, plus readable count bars and next-step explanations.

- [ ] Write failing subprocess tests for help, transpilation, execution, invalid input, and secret-free errors.
- [ ] Run `python3 -m unittest tests.test_cli -v` and confirm expected failures.
- [ ] Implement the standard-library CLI and text visualization.
- [ ] Document one-command setup, architecture, target user, complete flow, and three concrete experience tasks.
- [ ] Fill the L2 interaction, engineering/product, and beginner-guidance evidence sections truthfully.
- [ ] Run CLI tests and manually execute the three documented tasks.
- [ ] Commit the interface/documentation slice with Lore trailers.

### Task 6: Secure an Early Formal Submission Baseline

**Files:**
- Modify: `starter_kit/requirements.txt` only if a dependency is proven necessary.
- Modify: `starter_kit/Dockerfile` only if the verified build requires it.

**Interfaces:**
- Consumes: completed L1/L2 tree.
- Produces: a pushed commit and accepted upstream submission receipt.

- [ ] Run all unit tests and official public evaluators.
- [ ] Build and run the submission Docker image on Linux/Python 3.10.
- [ ] Scan the tracked tree for credentials, absolute local paths, mock flags, placeholders, and oversized files.
- [ ] Run `python3 starter_kit/prepare_submission.py --team-id JunkaiWang-TheoPhy`.
- [ ] Commit with Lore trailers, push `main`, and rerun preflight against the pushed HEAD.
- [ ] Create the upstream final-submission Issue for the exact 40-character SHA.
- [ ] Confirm `submission:accepted`, archive SHA-256, and Artifact ID before treating the baseline as valid.

### Task 7: Implement L3 After the Accepted Baseline

**Files:**
- Create: `starter_kit/loomq/hybrid.py`
- Create: `tests/test_hybrid.py`
- Modify: `starter_kit/adapter.py`
- Modify: `starter_kit/submission.yaml`

**Interfaces:**
- Consumes: bounded Hybrid-QASM grammar from the official statement.
- Produces: quantum-operation list and RISC-V assembly accepted by `TinyRISCVEmulator`.

- [ ] Write failing tests for assignments, arithmetic, equality/inequality, nested sequential branches, measurement mapping, and malformed programs.
- [ ] Run `python3 -m unittest tests.test_hybrid -v` and confirm expected failures.
- [ ] Implement tokenizer, AST, branch-label allocator, and RISC-V code generator.
- [ ] Enable L3 only after randomized/property-style tests and the official public evaluator pass.
- [ ] Run the full verification suite, commit, push, and create a new final-submission Issue.
- [ ] Confirm the newer Issue receives an accepted archival receipt before the deadline.

## Self-Review

- Spec coverage: L1 parser/transpile/run, all official targets, result schema, L2 formal runtime and three task families, executable experience surface, engineering evidence, reproducibility, early accepted submission, and deterministic L3 are all assigned to explicit tasks.
- Deliberate exclusions: Quafu does not replace the three official L1 targets. It may be added later as a documented extension or evidence only if the organizers confirm eligibility and a credential-safe live job succeeds.
- Placeholder scan: no implementation step relies on `TBD`, unscoped error handling, or unspecified tests.
- Type consistency: Tasks 2–5 consume the `Circuit` contract from Task 1; `adapter.py` retains the four official function signatures exactly.
