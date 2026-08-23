# Progress

## Goal

Deliver, push, and formally submit a verified LoomQ competition implementation before the deadline.

## Current Stage

Early L1 + L2 submission baseline: implementation and local verification complete; independent review, commit, push, preflight, and accepted upstream archival receipt pending.

## Verified Facts

- Official public L1 evaluator: 6/6 target/circuit combinations pass.
- Repository test discovery: 52 tests pass under system Python; 2 optional PyQuafu tests skip because the package is isolated.
- PyQuafu 0.4.5 oracle environment: both optional oracle tests pass under Python 3.10.
- Python bytecode compilation: passes.
- GitHub CLI is authenticated as `JunkaiWang-TheoPhy`.
- Docker/Colima Linux arm64 build and public L1 evaluator: passes all 6 cases.

## Next Steps

1. Resolve independent code-review findings.
2. Commit and push the early L1 + L2 baseline.
3. Run pushed-HEAD submission preflight and create the upstream final-submission Issue.
4. Confirm the accepted label and archive receipt.
5. Implement and verify L3, then create a newer accepted Issue before the deadline.

## Exit Conditions

- Final selected commit is pushed to the fork.
- Full local tests and public evaluators pass for every declared level.
- Submission preflight passes against pushed HEAD.
- Latest upstream submission Issue has `submission:accepted`, archive SHA-256, and Artifact ID.
- No credentials, machine-local paths, placeholders, or unverified evidence claims are present in the archived `starter_kit/`.
