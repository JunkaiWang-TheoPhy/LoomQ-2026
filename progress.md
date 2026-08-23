# Progress

## Goal

Deliver, push, and formally submit a verified LoomQ competition implementation before the deadline.

## Current Stage

L1 + L2 + L3 is accepted and archived in upstream Issue #68. Full-score hardening is in progress: L2 semantic validation, L3 register-pressure handling, and the quantum RISC-V bonus are implemented locally; final review, push, and replacement receipt remain.

## Verified Facts

- Official public L1 evaluator: 6/6 target/circuit combinations pass.
- Repository test discovery: 52 tests pass under system Python; 2 optional PyQuafu tests skip because the package is isolated.
- PyQuafu 0.4.5 oracle environment: both optional oracle tests pass under Python 3.10.
- Python bytecode compilation: passes.
- GitHub CLI is authenticated as `JunkaiWang-TheoPhy`.
- Docker/Colima Linux arm64 build and public L1 evaluator: passes all 6 cases.
- Upstream Issue #67: `submission:accepted`, Artifact ID `9487379029`.
- L3: 11 focused/randomized tests and the public evaluator pass; 1,000 fixed-seed programs are checked across all four measurement inputs.
- Full-score hardening: L2 semantic/backend guardrails, 1,000-program L3 fuzzing, and 32-bit custom-opcode Bell execution pass locally.

## Next Steps

1. Run the full test, Docker, privacy, and independent review gates.
2. Commit and push the hardening and Bonus evidence.
3. Run pushed-HEAD preflight and create a new L1+L2+L3 Issue.
4. Confirm the newer Issue receives `submission:accepted` and an archival receipt.
5. Add genuine hardware evidence only after an eligible platform task succeeds.

## Exit Conditions

- Final selected commit is pushed to the fork.
- Full local tests and public evaluators pass for every declared level.
- Submission preflight passes against pushed HEAD.
- Latest upstream submission Issue has `submission:accepted`, archive SHA-256, and Artifact ID.
- No credentials, machine-local paths, placeholders, or unverified evidence claims are present in the archived `starter_kit/`.
