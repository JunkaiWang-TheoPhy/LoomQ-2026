# LoomQ hardware gateway

The web console uses `loomq.hardware.HardwareGateway` for backend discovery,
submission, polling, and result normalization. Provider SDKs are optional and
never imported by the browser process. A deployment registers a provider
adapter at startup:

```python
from loomq.hardware import HardwareGateway

gateway = HardwareGateway()
gateway.register_provider("originq", submit_originq, poll_originq)
```

Both callables receive or return provider data through the gateway boundary.
The returned result must contain `backend`, `job_id`, `shots`, `counts`,
`bit_order: "little"`, `timestamp`, and a provenance object. `provenance.kind`
must be `hardware`, `fixture`, or `replay`.

Credentials are read only from process environment variables:

| Provider | Environment variable |
| --- | --- |
| OriginQ | `LOOMQ_ORIGINQ_TOKEN` |
| SpinQ | `LOOMQ_SPINQ_TOKEN` |

The browser receives the variable name and readiness state, never its value.
Without a registered adapter and credential, a QPU is shown as
`configuration_required` or `adapter_required`; it is never presented as
ready. For local QA, `LOOMQ_HARDWARE_FIXTURE=1` enables an explicitly labelled
fixture job. Fixture output is never valid hardware evidence.

Web endpoints:

- `GET /api/hardware/backends` — capabilities plus readiness state.
- `POST /api/hardware/submit` — submit `{backend, qasm, shots}` and receive a job ID.
- `GET /api/hardware/jobs/{job_id}` — poll a normalized result with provenance.

The gateway deliberately does not hide provider queue delays or convert a
local simulation into a hardware claim. A live adapter can be added without
changing the UI or the result schema.
