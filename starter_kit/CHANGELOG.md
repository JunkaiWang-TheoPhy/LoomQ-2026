# Starter Kit Changelog

## Unreleased

- Use the importable `starter_kit/` name for the submission root.
- Add `__init__.py` so tests can use `from starter_kit import adapter` directly.
- Add a zero-dependency responsive Web lab backed by the public adapter API.
- Validate W states, explicit computational basis states, and uniform superpositions in L2.
- Fall back to a deterministically validated target-state circuit after two invalid model replies.
- Archive traceable OriginQ and SpinQ real-hardware evidence, including SpinQ's provider-native MessagePack result.
- Add a fixed 500-case L2 campaign with resume support, credential-safe records, and tamper-evident validation.
- Ship a 158-test regression suite inside the formally archived `starter_kit/` directory.
- Archive a reproducible PyQuafu 0.4.5 cross-validation corpus and 120/120 target-check summary without adding a core dependency.
- Archive a deterministic 40,000-check offline campaign with per-lane assertions, failure diagnostics, and a bound corpus hash.
- Add four guided Web paths, accessible tabular results, recoverable Agent errors, responsive browser QA evidence, and stricter HTTP boundaries.
- Add deterministic dual-hardware evidence validation, Wilson statistics, provider MessagePack cross-checking, and a SHA-256 manifest.
- Add exact per-gate probability/amplitude/phase traces to Web and CLI, with a bounded state-space guard.
- Add bounded multi-turn Agent context with strict role validation and a user-visible reset control.
- Add executable Deutsch–Jozsa, two-iteration Grover, and QFT-4 examples to the Web and all-target regression suite.
- Parse every emitted target IR back independently and reject semantic round-trip mismatches before returning from `transpile()`.
- Bound QASM size/register/operation counts, dense and sparse local-state growth, target-specific local qubits, and Hybrid-QASM tokens/statements/nesting.
- Remove fabricated success results from optional vendor SDK examples; missing packages now fail explicitly, unavailable provider job IDs remain null, and locally observed timestamps are labeled as such.
- Add ProofTrace safe rewrites, per-operation source lineage, deterministic three-target certificates, a Web proof/download panel, and a 225-mutant integrity benchmark.
- Add exact/finite-shot assertion reports with bounded first-divergence diagnosis, without attributing hardware deviations to unmeasured physical causes.
- Add replayable Hybrid-QASM → RISC-V branch traces with source conditions, machine jumps, measurement provenance, machine words, and register deltas.
- Archive independent fixed-word, literal Bell execution, lossless-parameter, malformed-word, and randomized all-gate quantum RISC-V tests at the documented judge command.
- Archive a 12-case L2 qualification chain that observes 20 real local Chat Completions requests and independently checks state distributions or canonical backend IDs without claiming real DeepSeek accuracy.
- Add a Counterfactual Circuit Lab that exposes bounded first-divergence diagnosis as an interactive beginner lesson, with structural-mismatch safeguards and desktop/mobile browser evidence.
- Close the L2 backend-selection chain with a capability-table constraint solver after two invalid model replies; all 500 campaign prompts survive an injected-completion forced-invalid path after exactly 1000 callbacks, while the separate qualification suite checks the HTTP service-call contract.

## 1.1.0 - 2026-07-27

- Publish the environment-only OpenAI-compatible L2 runtime contract.
- Fix the formal L2 scoring model to DeepSeek `deepseek-v4-flash`.
- Publish per-case call, token, and timeout budgets in `l2_policy.json`.
- Add a dependency-free `llm_client.py` transport helper without prompts or scoring logic.
- Clarify that the organizer provides no API endpoint, key, or credit before formal scoring.

## 1.0.1 - 2026-07-27

- Add the read-only local final-submission preflight.
- Define `starter_kit/` as the build and evaluation root in official forks.
- Document commit-SHA submission, server-side cutoff time, receipts, and resubmission rules.

## 1.0.0 - 2026-07-11

- Freeze submission contract v1.0.
- Add `submission.yaml`, version metadata, and machine-readable public reports.
- Remove mock scoring paths, prompt-specific answers, and the L3 reference solution.
- Clarify that formal scoring runs in an organizer-owned isolated environment.
