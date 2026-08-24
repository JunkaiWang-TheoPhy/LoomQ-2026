# Task 2 Report

## Scope

- Added whole-circuit semantic validation to the ProofTrace certificate for source -> optimized circuits.
- Added whole-circuit semantic validation to each portability target for optimized -> parsed native IR circuits.
- Extended the deterministic deletion-mutation benchmark so every native-IR deletion mutant must also be rejected by the semantic layer.

## RED Evidence

- `python3 -m unittest starter_kit.tests.test_prooftrace starter_kit.tests.test_prooftrace_benchmark -v`
- Initial failures:
  - missing certificate field `whole_circuit_validation`
  - missing `loomq.prooftrace.assess_portability`
  - missing benchmark fields `semantic_checks`, `semantic_rejections`, `semantic_false_accepts`, `semantic_scope_skips`

## GREEN Evidence

- `python3 -m unittest starter_kit.tests.test_native_ir_verifier starter_kit.tests.test_prooftrace starter_kit.tests.test_prooftrace_benchmark -v`
  - Result: `Ran 15 tests in 3.314s` / `OK`
- `python3 -m py_compile starter_kit/loomq/prooftrace.py starter_kit/scripts/prooftrace_benchmark.py starter_kit/tests/test_prooftrace.py starter_kit/tests/test_prooftrace_benchmark.py`
  - Result: success
- `git diff --check`
  - Result: success
- `PYTHONPATH=starter_kit python3 starter_kit/scripts/prooftrace_benchmark.py --json`
  - Result summary:
    - `total_mutants = 225`
    - `detected_mutants = 225`
    - `false_accepts = 0`
    - `semantic_checks = 225`
    - `semantic_rejections = 225`
    - `semantic_false_accepts = 0`
    - `semantic_scope_skips = []`
    - `portability_checks = 15`
    - `rewrite_checks = 132`
    - `corpus_sha256 = 2f8dedadd11c815acb89ef7e5dfc85292420c5a5df81b76bbb4c95ee9d4c8f49`

## Changed Files

- `starter_kit/loomq/prooftrace.py`
- `starter_kit/scripts/prooftrace_benchmark.py`
- `starter_kit/tests/test_prooftrace.py`
- `starter_kit/tests/test_prooftrace_benchmark.py`

## Notes

- `starter_kit/loomq/native_ir.py` was not changed; the strict structural verifier remains mandatory and unchanged.
- The new phase-mutation test uses `h` followed by `s`, which preserves terminal Z-basis probabilities for the prepared output but is rejected by whole-circuit semantic validation.

## Remaining Risks

- Whole-circuit semantic validation still inherits the Task 1 bound of at most 8 qubits. Current committed benchmark fixtures stay within scope, so no scoped skips were needed in this task.
