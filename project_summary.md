# Project Summary

## Purpose

LoomQ is a public competition fork whose scored submission root is `starter_kit/`. The implementation must translate the official OpenQASM 2.0 subset to SpinQ QASM 2, OriginIR, and Braket QASM 3; normalize execution results; optionally expose an L2 model-backed agent and L3 Hybrid-QASM compiler; and submit an immutable Git commit through an upstream Issue.

## Repository Map

- `problem_statement.md`: authoritative problem statement and scoring rubric.
- `starter_kit/adapter.py`: four organizer-facing entry points.
- `starter_kit/submission.yaml`: declared levels and runtime/network contract.
- `starter_kit/loomq/`: participant implementation modules.
- `starter_kit/loomq_cli.py`: beginner-facing command line interface.
- `starter_kit/evaluator.py`: public contract checker, not the formal scorer.
- `starter_kit/evidence/README.md`: manual scoring claims and evidence index.
- `competition/`: organizer submission intake/archive tooling.
- `tests/`: organizer tests plus participant regression and integration tests.
- `docs/superpowers/plans/`: implementation plan and research record.

## Runtime and Dependencies

- Formal base: Linux, Python 3.10.
- Scored L1/L2 implementation: Python standard library only.
- Optional development oracle: PyQuafu 0.4.5 in ignored `.venv/`; not part of the formal runtime.
- L2 external service: OpenAI-compatible Chat Completions configured only through `LOOMQ_LLM_*`.

## Verification Commands

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q starter_kit competition tests
python3 starter_kit/evaluator.py --level l1 --target spinq,originq,braket
.venv/bin/python -m unittest tests.test_quafu_oracle -v
python3 starter_kit/prepare_submission.py --team-id JunkaiWang-TheoPhy
```

Docker verification command, when a Docker daemon is available:

```bash
docker build -t loomq-submission starter_kit
docker run --rm loomq-submission
```

## Git and External State

- Remote: `https://github.com/JunkaiWang-TheoPhy/LoomQ-2026.git`
- Default branch: `main`
- Upstream source: `QAIDAO/LoomQ-2026`
- GitHub submission identity: `JunkaiWang-TheoPhy`
- Deadline: `2026-08-25 12:00 UTC+8`, determined by upstream Issue creation time.

## Current Risks

- Docker verification requires the local Colima runtime; the baseline image has been built and run successfully on Linux/arm64.
- Quafu is not one of the three official L1 target identifiers; it is only a development oracle or optional extension unless organizers explicitly accept it as hardware evidence.
- Formal L2 correctness depends on hidden prompt variants and the organizer-injected `deepseek-v4-flash` service.
- L3 compiler correctness is protected by deterministic branch tests and 30 seeded random programs with exhaustive two-bit measurement inputs.
