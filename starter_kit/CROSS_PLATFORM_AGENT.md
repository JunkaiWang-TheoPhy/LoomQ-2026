# Cross-platform Agent

The cross-platform entry point is `adapter.cross_platform_agent()`.  It keeps
one natural-language request and one validated OpenQASM program as the source of
truth, then previews native IR and runs the same circuit through the three local
adapter targets:

```text
natural language
  -> grounded Agent + deterministic QASM validation
  -> one OpenQASM 2.0 program
  -> SpinQ / OriginQ / Braket native IR previews
  -> local execution through each adapter
  -> unified counts and cross-platform consistency report
```

The credential-free Web endpoint is `POST /api/cross-platform-agent`:

```json
{"prompt": "生成一个两比特 Bell 态并测量，比较三个平台", "shots": 128}
```

The response schema is `loomq-cross-platform-agent-plan-v1`.  It records the
canonical backend candidates from `backend_capabilities.json`, a recommended
backend, all native IR previews, unified result schemas, and
`consistency.all_counts_equal`.  The endpoint previews local adapters; it does
not claim that a cloud QPU job was submitted.  Real hardware execution remains
an explicit follow-up through the existing credential-injected backend paths.
