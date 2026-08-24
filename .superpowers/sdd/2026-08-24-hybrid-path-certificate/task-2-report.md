# Task 2 Report

## Scope

Implemented Task 2 on top of Task 1's canonical `loomq.hybrid_paths` API. Kept changes inside the Task 2 ownership list plus this required report. Did not touch Task 1 core files.

## RED Evidence

Focused red run:

```bash
python3 -m unittest tests.test_hybrid_path_certificate starter_kit.tests.test_hybrid_path_benchmark starter_kit.tests.test_web -v
```

Observed failures before implementation:

- `starter_kit.adapter` had no `certify_hybrid_paths`
- old certificate shape still returned from `hybrid_path_certificate()`
- `/api/hybrid-paths` returned `404`
- `scripts.hybrid_path_benchmark` was missing
- frontend static contracts for `列出所有可能分支`, JSON download, and shrink-safe path evidence were absent

## GREEN Evidence

Focused Task 2 suite:

```bash
python3 -m unittest tests.test_hybrid_path_certificate starter_kit.tests.test_hybrid_path_benchmark starter_kit.tests.test_web -v
```

Result: `Ran 30 tests in 13.230s` -> `OK`

Broader regression pass including the owned verifier changes:

```bash
python3 -m unittest tests.test_hybrid_path_certificate starter_kit.tests.test_hybrid_paths starter_kit.tests.test_hybrid_path_benchmark starter_kit.tests.test_web tests.test_verify_submission starter_kit.tests.test_verify_submission -v
```

Result: `Ran 46 tests in 44.011s` -> `OK`

Benchmark command:

```bash
cd starter_kit && python3 -m scripts.hybrid_path_benchmark --json
```

Result:

- `passed: true`
- `fixture_count: 4`
- `tamper_rejections: 4`
- `corpus_sha256: f452982ce91335709cc63911312a8bd1b73f48886dcea2e174b6b4d3396cc7f0`

Additional gates:

```bash
node --check starter_kit/web/app.js
git diff --check
```

Both exited cleanly.

## Key Changes

- Rewired `starter_kit/adapter.py` to expose canonical `certify_hybrid_paths()` and recomputation verification, while keeping `hybrid_path_certificate()` as a compatibility alias.
- Added bounded `/api/hybrid-paths` in `starter_kit/loomq/web.py` and made `/api/hybrid-path-certificate` a compatibility alias returning the same `{certificate, verification}` shape.
- Reworked the Hybrid evidence card in the web UI to show observable conclusions first, added `max_outcomes`, and enabled JSON download of the recomputable report.
- Added `starter_kit/scripts/hybrid_path_benchmark.py` and wired required verifier phase `hybrid-path-certificate` into `starter_kit/verify_submission.py`.
- Removed the redundant tracked duplicate `starter_kit/loomq/hybrid_path_certificate.py` after migrating consumers and tests.
- Corrected the Hybrid path semantics wording in `starter_kit/evidence/README.md` and `starter_kit/SCIENTIFIC_CLAIMS_AUDIT.md`.

## Remaining Risks

- The frontend evidence layout is covered by static contract tests only in this task; no real browser QA was performed here.
- The benchmark corpus is intentionally small and deterministic. It guards the required semantics but is not a substitute for larger exploratory fixture coverage.
