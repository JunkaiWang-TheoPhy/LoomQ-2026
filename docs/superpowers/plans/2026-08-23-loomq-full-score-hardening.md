# LoomQ Full-Score Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Raise the accepted LoomQ submission's hidden-test reliability and add the complete custom quantum RISC-V bonus evidence without depending on unavailable platform credentials.

**Architecture:** Keep the accepted parser/IR/runtime boundaries intact. Add deterministic L2 post-validation around model replies, reduce L3 register pressure through direct instruction selection, and implement a separate 32-bit custom-opcode encoder/decoder whose decoded operations execute through the existing state-vector engine. Expose the complete beginner flow and verification suite through standard-library CLIs.

**Tech Stack:** Python 3.10 standard library, `unittest`, existing LoomQ state-vector engine and public evaluator, optional PyQuafu development oracle, Docker.

## Global Constraints

- Preserve the four official adapter signatures and Starter Kit contract version `1.0`.
- L2 must perform at least one real organizer-injected model call per case and output only the 12 official gates.
- L2 service configuration remains environment-only through `LOOMQ_LLM_*`; never expose credentials.
- L3 scored output remains limited to `li, add, sub, addi, beq, bne, j` and must remain independent of the bonus extension.
- Quantum RISC-V bonus words use an actual 32-bit RISC-V custom opcode and must pass encode → decode → execute tests.
- Add no third-party runtime dependencies.
- Preserve accepted Issue #68 as a fallback until a newer exact commit is archived successfully.
- Real-hardware evidence is deferred until the user authenticates to an eligible platform; no synthetic job IDs may be submitted as hardware evidence.

---

### Task 1: Deterministic L2 Semantic Guardrails

**Files:**
- Modify: `starter_kit/loomq/agent.py`
- Modify: `tests/test_agent.py`

**Interfaces:**
- Consumes: natural-language prompt and model reply text.
- Produces: one accepted QASM/backend reply or one bounded diagnostic retry through `chat(prompt, completion)`.

- [ ] Add a failing test where syntactically valid two-qubit QASM is returned for a three-qubit GHZ request; assert that a second model call receives a qubit-count/target diagnostic.
- [ ] Run `python3 -m unittest tests.test_agent.AgentTests.test_semantically_wrong_ghz_is_retried -v` and confirm it fails because the first reply is currently accepted.
- [ ] Implement prompt intent extraction for Bell/GHZ bit count plus deterministic distribution validation with `parse_qasm()` and `probabilities()`.
- [ ] Run the focused test and confirm it passes.
- [ ] Add a failing test where a zero-queue 15-qubit request receives an incompatible backend ID; assert a retry and final compatible ID.
- [ ] Run the focused backend test and confirm it fails because backend replies are currently returned without validation.
- [ ] Implement capability-table constraint extraction and backend-ID validation; reuse the existing JSON table and permit only IDs satisfying qubits, queue, cost, and hardware-kind constraints stated by the prompt.
- [ ] Run `python3 -m unittest tests.test_agent -v` and the L2 contract tests.

### Task 2: L3 Bounds and Register-Pressure Hardening

**Files:**
- Modify: `starter_kit/loomq/hybrid.py`
- Modify: `tests/test_hybrid.py`

**Interfaces:**
- Consumes: declared classical-register size and parsed classical AST.
- Produces: bounds-checked RISC-V assembly that avoids temporary registers for direct reference/immediate arithmetic when safe.

- [ ] Add a failing test proving `c[k]` at or beyond the declared `creg` size is rejected before code generation.
- [ ] Run the focused test and confirm the current parser accepts the invalid reference.
- [ ] Pass `Circuit.num_clbits` into the classical parser and reject out-of-declaration measurement references.
- [ ] Add a failing test for an assignment summing `c[0]..c[21]`; inject all measurement registers and assert the correct final value instead of a temporary-register error.
- [ ] Run the focused test and confirm the current compiler raises register pressure.
- [ ] Implement direct assignment instruction selection: references copy directly, constants load directly, reference/reference operations emit one `add/sub`, reference/immediate operations use `addi`, and target-safe arithmetic accumulates into the destination without reserving measurement registers.
- [ ] Expand deterministic random tests to at least 1,000 generated programs with independent literal expectations and exhaustive small measurement inputs.
- [ ] Run `python3 -m unittest tests.test_hybrid -v` and `python3 starter_kit/evaluator.py --level l3`.

### Task 3: 32-bit Quantum RISC-V Bonus Closed Loop

**Files:**
- Create: `starter_kit/loomq/quantum_riscv.py`
- Modify: `starter_kit/riscv_emulator.py`
- Create: `tests/test_quantum_riscv.py`
- Create: `starter_kit/QUANTUM_RISCV_SPEC.md`

**Interfaces:**
- Produces: `encode_circuit(circuit) -> EncodedQuantumProgram`, `decode_program(program) -> Circuit`, and `TinyRISCVEmulator.load_quantum_program(program)` / `execute_quantum(shots)`.
- Encoding: 32-bit little-endian words with RISC-V `custom-0` opcode `0x0B`; fixed operand fields plus a seven-bit gate/parameter-table payload.

- [ ] Add failing round-trip tests covering all 12 gates, measurement, maximum qubit indices, and parameter-table values.
- [ ] Run `python3 -m unittest tests.test_quantum_riscv -v` and confirm module/import failure.
- [ ] Implement immutable encoded-program/instruction records, field-range validation, little-endian byte serialization, opcode validation, circuit encoding, and circuit decoding.
- [ ] Run round-trip tests and confirm exact Gate/Measurement equality.
- [ ] Add a failing end-to-end Bell test that loads encoded words through `TinyRISCVEmulator`, executes them, and expects `{'00': 512, '11': 512}` for 1024 shots.
- [ ] Extend the official lightweight emulator with the smallest machine-code load/decode/execute path, delegating quantum semantics to the existing deterministic runtime.
- [ ] Add malformed opcode, truncated bytes, parameter-index, and duplicate-measurement mapping tests.
- [ ] Document the bit layout, gate IDs, parameter table, byte order, validation rules, and exact end-to-end test command.
- [ ] Run the bonus tests and the existing L3 tests together to prove isolation.

### Task 4: Beginner One-Command Flow and Evidence

**Files:**
- Modify: `starter_kit/loomq_cli.py`
- Modify: `tests/test_cli.py`
- Create: `starter_kit/verify_submission.py`
- Create: `starter_kit/bonus_evaluator.py`
- Create: `tests/test_verify_submission.py`
- Modify: `starter_kit/README.md`
- Modify: `starter_kit/ARCHITECTURE.md`
- Modify: `starter_kit/evidence/README.md`
- Modify: `project_summary.md`
- Modify: `progress.md`

**Interfaces:**
- Produces: `loomq ask <prompt>` for generate → validate → execute, and `python3 starter_kit/verify_submission.py` for credential-free L1/L3/bonus verification.

- [ ] Add a failing CLI test for `ask` using dependency injection at the command boundary; assert QASM, normalized counts, and beginner explanation appear in one response.
- [ ] Implement `ask` by extracting validated QASM from `agent_chat`, running the selected local backend, and rendering existing count bars.
- [ ] Add a failing subprocess test for `verify_submission.py`; assert nonzero on a controlled failing command and zero with a complete JSON summary on the real repository.
- [ ] Implement the standard-library verification orchestrator with explicit compile, unit, L1, L3, and quantum-RISC-V phases.
- [ ] Update documentation and evidence to claim only runnable features; check the custom RISC-V Bonus only after its complete suite passes.
- [ ] Run CLI and verification-script tests.

### Task 5: Full Verification, Review, and Safe Replacement Submission

**Files:**
- Modify only files required by verified review findings.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: clean pushed commit and, if all evidence is truthful, a newer accepted submission receipt.

- [ ] Run `python3 -m unittest discover -s tests -v`.
- [ ] Run `.venv/bin/python -m unittest tests.test_quafu_oracle -v`.
- [ ] Run `python3 -m compileall -q starter_kit competition tests`.
- [ ] Run public L1 and L3 evaluators and the new bonus end-to-end suite.
- [ ] Build and run the `starter_kit/` Docker image.
- [ ] Request independent code review and fix every Critical/High/Medium issue.
- [ ] Scan tracked files for credentials, personal data, local paths, mock claims, and archive size.
- [ ] Commit with Lore trailers, push `main`, run `prepare_submission.py`, and create a newer Issue only after the pushed SHA is verified.
- [ ] Confirm the replacement Issue is `submission:accepted` before treating it as effective.

## Self-Review

- Spec coverage: the plan directly addresses L2 objective reliability, L3 hidden-case reliability, all three required custom-RISC-V bonus artifacts, one-command product delivery, evidence, verification, and archival submission.
- Deliberate boundary: true-hardware execution remains outside code changes until platform authentication exists; the plan never fabricates evidence or makes `adapter.run()` depend on credentials.
- Placeholder scan: no task contains an unspecified implementation or deferred test.
- Type consistency: L2 continues to return text; L3 continues to return `(list, str)`; quantum bonus types are isolated and consumed by the extended emulator; CLI and verification commands depend only on these stable public boundaries.
