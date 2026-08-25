"""Credential-safe gateway for live quantum backends and replayable fixtures.

The web layer talks to this module instead of knowing provider SDK details. A
provider integration registers submit/poll callables at process startup; no
token is ever returned to the browser. The built-in fixture is intentionally
labelled as such and can never be reported as hardware evidence.
"""

from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping


_CAPABILITIES = Path(__file__).resolve().parents[1] / "backend_capabilities.json"
_PROVIDER_ENV = {"originq": "LOOMQ_ORIGINQ_TOKEN", "spinq": "LOOMQ_SPINQ_TOKEN"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _catalog() -> list[dict[str, Any]]:
    return json.loads(_CAPABILITIES.read_text(encoding="utf-8"))["backends"]


def normalize_hardware_result(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = ("backend", "job_id", "shots", "counts", "bit_order", "timestamp", "provenance")
    missing = [field for field in required if field not in payload]
    if missing:
        raise ValueError(f"hardware result missing fields: {', '.join(missing)}")
    if not isinstance(payload["job_id"], str) or not payload["job_id"]:
        raise ValueError("job_id must be a non-empty string")
    if not isinstance(payload["shots"], int) or isinstance(payload["shots"], bool) or payload["shots"] <= 0:
        raise ValueError("shots must be a positive integer")
    counts = payload["counts"]
    if not isinstance(counts, dict) or not counts or any(
        not isinstance(key, str) or not isinstance(value, int) or isinstance(value, bool) or value < 0
        for key, value in counts.items()
    ):
        raise ValueError("counts must be a non-empty map of non-negative integers")
    if sum(counts.values()) != payload["shots"]:
        raise ValueError("counts must sum to shots")
    if payload["bit_order"] != "little":
        raise ValueError("bit_order must be little")
    provenance = payload["provenance"]
    if not isinstance(provenance, dict) or provenance.get("kind") not in {"hardware", "fixture", "replay"}:
        raise ValueError("provenance.kind must be hardware, fixture, or replay")
    return dict(payload)


Submitter = Callable[[str, str, int], Mapping[str, Any]]
Poller = Callable[[str], Mapping[str, Any]]


class HardwareGateway:
    def __init__(self, env: Mapping[str, str] | None = None) -> None:
        self.env = dict(os.environ if env is None else env)
        self._submitters: dict[str, Submitter] = {}
        self._pollers: dict[str, Poller] = {}
        self._jobs: dict[str, dict[str, Any]] = {}

    def register_provider(self, platform: str, submitter: Submitter, poller: Poller) -> None:
        self._submitters[platform] = submitter
        self._pollers[platform] = poller

    def discover(self) -> list[dict[str, Any]]:
        fixture = self.env.get("LOOMQ_HARDWARE_FIXTURE") == "1"
        result = []
        for backend in _catalog():
            item = dict(backend)
            platform = str(backend["platform"])
            if backend["kind"] == "simulator":
                item.update(status="ready", readiness="local")
            elif fixture:
                item.update(status="fixture_available", readiness="fixture")
            elif platform not in self._submitters:
                item.update(
                    status="configuration_required" if not self.env.get(_PROVIDER_ENV.get(platform, "")) else "adapter_required",
                    readiness="credential" if not self.env.get(_PROVIDER_ENV.get(platform, "")) else "adapter",
                )
            else:
                item.update(status="ready", readiness="provider")
            item["credential_env"] = _PROVIDER_ENV.get(platform)
            result.append(item)
        return result

    def _backend(self, backend_id: str) -> dict[str, Any]:
        try:
            return next(item for item in _catalog() if item["id"] == backend_id)
        except StopIteration as exc:
            raise ValueError(f"unknown backend: {backend_id}") from exc

    def submit(self, qasm: str, backend_id: str, shots: int) -> dict[str, Any]:
        if not isinstance(qasm, str) or not qasm.strip():
            raise ValueError("qasm must be a non-empty string")
        if not isinstance(shots, int) or isinstance(shots, bool) or shots <= 0:
            raise ValueError("shots must be a positive integer")
        backend = self._backend(backend_id)
        platform = str(backend["platform"])
        job_id = f"loomq-{platform}-{uuid.uuid4().hex}"
        if self.env.get("LOOMQ_HARDWARE_FIXTURE") == "1" and backend["kind"] != "simulator":
            self._jobs[job_id] = {
                "backend": backend_id,
                "status": "completed",
                "result": normalize_hardware_result({
                    "backend": backend_id,
                    "job_id": job_id,
                    "shots": shots,
                    "counts": {"0": shots},
                    "bit_order": "little",
                    "timestamp": _now(),
                    "provenance": {"kind": "fixture", "provider": platform, "reason": "local QA only"},
                }),
            }
            return {"job_id": job_id, "backend": backend_id, "status": "queued", "provenance_kind": "fixture"}
        submitter = self._submitters.get(platform)
        if submitter is None:
            env_name = _PROVIDER_ENV.get(platform, "provider token")
            raise RuntimeError(f"provider adapter unavailable; configure {env_name} and register an adapter")
        raw = dict(submitter(qasm, backend_id, shots))
        raw.setdefault("backend", backend_id)
        raw.setdefault("job_id", job_id)
        self._jobs[job_id] = {"backend": backend_id, "status": "queued", "provider_job": raw}
        return {"job_id": job_id, "backend": backend_id, "status": "queued", "provenance_kind": "hardware"}

    def poll(self, job_id: str) -> dict[str, Any]:
        if job_id not in self._jobs:
            raise ValueError("unknown job_id")
        job = self._jobs[job_id]
        if job["status"] == "completed":
            return {"job_id": job_id, "status": "completed", **job["result"]}
        backend = self._backend(job["backend"])
        poller = self._pollers.get(str(backend["platform"]))
        if poller is None:
            raise RuntimeError("provider poller unavailable")
        result = normalize_hardware_result(poller(str(job["provider_job"].get("job_id", job_id))))
        job.update(status="completed", result=result)
        return {"job_id": job_id, "status": "completed", **result}
