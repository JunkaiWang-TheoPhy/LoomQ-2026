"""Validate LoomQ hardware evidence, derived statistics, and file integrity."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import struct
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Mapping


SCHEMA = "loomq-hardware-analysis-v1"
MANIFEST_SCHEMA = "loomq-evidence-manifest-v1"
COMPETITION_START = datetime.fromisoformat("2026-08-01T00:00:00+08:00")
COMPETITION_DEADLINE = datetime.fromisoformat("2026-08-25T12:00:00+08:00")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _json(path: Path) -> Dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return payload


def decode_spinq_msgpack(path: Path) -> Dict[str, float]:
    """Decode the provider's constrained map<string,float64> result without dependencies."""
    data = path.read_bytes()
    if not data or not 0x80 <= data[0] <= 0x8F:
        raise ValueError("SpinQ raw result is not a MessagePack fixmap")
    size = data[0] & 0x0F
    offset = 1
    result: Dict[str, float] = {}
    for _ in range(size):
        if offset >= len(data) or not 0xA0 <= data[offset] <= 0xBF:
            raise ValueError("SpinQ MessagePack key is not a fixstr")
        length = data[offset] & 0x1F
        offset += 1
        end = offset + length
        try:
            key = data[offset:end].decode("utf-8")
        except UnicodeDecodeError as exc:
            raise ValueError("SpinQ MessagePack key is not UTF-8") from exc
        offset = end
        if offset + 9 > len(data) or data[offset] != 0xCB:
            raise ValueError("SpinQ MessagePack value is not float64")
        value = struct.unpack(">d", data[offset + 1 : offset + 9])[0]
        offset += 9
        if not math.isfinite(value):
            raise ValueError("SpinQ MessagePack contains a non-finite probability")
        result[key] = value
    if offset != len(data):
        raise ValueError("SpinQ MessagePack has trailing bytes")
    return result


def _wilson_interval(successes: int, trials: int, z: float = 1.959963984540054) -> list[float]:
    if not 0 <= successes <= trials or trials <= 0:
        raise ValueError("invalid binomial observation")
    proportion = successes / trials
    denominator = 1 + z * z / trials
    center = (proportion + z * z / (2 * trials)) / denominator
    radius = z * math.sqrt(proportion * (1 - proportion) / trials + z * z / (4 * trials * trials)) / denominator
    return [center - radius, center + radius]


def _validate_timestamp(value: Any, label: str) -> None:
    if not isinstance(value, str):
        raise ValueError(f"{label} is missing")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None or not COMPETITION_START <= parsed <= COMPETITION_DEADLINE:
        raise ValueError(f"{label} is outside the competition window")


def _validate_bell_qasm(path: Path, require_measurement: bool) -> None:
    compact = " ".join(path.read_text(encoding="utf-8").lower().split())
    required = ("openqasm 2.0;", "qreg q[2];", "h q[0];", "cx q[0],q[1];")
    normalized = compact.replace(" ", "")
    for token in required:
        if token.replace(" ", "") not in normalized:
            raise ValueError(f"{path.name} is not the documented Bell circuit")
    if require_measurement and "measureq->c;" not in normalized:
        raise ValueError(f"{path.name} does not measure the Bell circuit")


def analyze_evidence(evidence_dir: Path) -> Dict[str, Any]:
    files = evidence_dir / "files"
    origin = _json(files / "originq-result.json")
    spinq = _json(files / "spinq-result.json")

    if origin.get("status") != "success" or not origin.get("job_id"):
        raise ValueError("OriginQ evidence is not a traceable successful job")
    _validate_timestamp(origin.get("created_at"), "OriginQ created_at")
    _validate_timestamp(origin.get("completed_at"), "OriginQ completed_at")
    _validate_bell_qasm(files / "originq-bell.qasm", require_measurement=True)
    counts = origin.get("counts")
    if not isinstance(counts, dict) or set(counts) != {"00", "01", "10", "11"}:
        raise ValueError("OriginQ counts must contain all two-bit states")
    shots = origin.get("shots")
    if not isinstance(shots, int) or isinstance(shots, bool) or sum(counts.values()) != shots:
        raise ValueError("OriginQ counts do not sum to shots")
    for state, count in counts.items():
        if origin.get("probabilities", {}).get(state) != count / shots:
            raise ValueError("OriginQ probabilities do not match counts")
    origin_peak = counts["00"] + counts["11"]

    if spinq.get("status") != "success" or not spinq.get("job_id"):
        raise ValueError("SpinQ evidence is not a traceable successful job")
    _validate_timestamp(spinq.get("created_at"), "SpinQ created_at")
    _validate_timestamp(spinq.get("completed_at"), "SpinQ completed_at")
    _validate_bell_qasm(files / "spinq-bell.qasm", require_measurement=False)
    raw_probabilities = decode_spinq_msgpack(files / "spinq-result.msgpack")
    if raw_probabilities != spinq.get("probabilities"):
        raise ValueError("SpinQ JSON does not losslessly match the provider MessagePack")
    if set(raw_probabilities) != {"00", "01", "10", "11"}:
        raise ValueError("SpinQ probabilities must contain all two-bit states")
    if not math.isclose(sum(raw_probabilities.values()), 1.0, abs_tol=1e-7):
        raise ValueError("SpinQ probabilities do not sum to one")
    dominant = max(raw_probabilities, key=raw_probabilities.get)
    ideal_peak = raw_probabilities["00"] + raw_probabilities["11"]
    ideal_bell = {"00": 0.5, "01": 0.0, "10": 0.0, "11": 0.5}
    total_variation = 0.5 * sum(abs(raw_probabilities[state] - ideal_bell[state]) for state in ideal_bell)

    return {
        "schema_version": SCHEMA,
        "method": "deterministic recomputation from committed provider evidence",
        "platforms": {
            "originq": {
                "job_id": origin["job_id"],
                "shots": shots,
                "ideal_peak_shots": origin_peak,
                "ideal_peak_probability": origin_peak / shots,
                "wilson_95_interval": _wilson_interval(origin_peak, shots),
                "interpretation": "00 and 11 are the Bell ideal-support states",
            },
            "spinq": {
                "job_id": spinq["job_id"],
                "result_type": spinq.get("result_type"),
                "dominant_state": dominant,
                "ideal_peak_probability": ideal_peak,
                "total_variation_from_ideal_bell": total_variation,
                "uncertainty_note": "provider returned projection probabilities, not shot counts",
                "interpretation": "00 is an ideal-support state; noise prevents an ideal two-peak claim",
            },
        },
    }


def _manifest_entries(evidence_dir: Path) -> list[Dict[str, Any]]:
    candidates = [evidence_dir / "hardware-analysis.json"]
    candidates.extend(sorted(path for path in (evidence_dir / "files").rglob("*") if path.is_file()))
    return [
        {
            "path": path.relative_to(evidence_dir).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in candidates
    ]


def write_evidence_bundle(evidence_dir: Path) -> Dict[str, Any]:
    analysis = analyze_evidence(evidence_dir)
    (evidence_dir / "hardware-analysis.json").write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    manifest = {"schema_version": MANIFEST_SCHEMA, "files": _manifest_entries(evidence_dir)}
    (evidence_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return manifest


def validate_evidence(evidence_dir: Path) -> Dict[str, Any]:
    expected_analysis = analyze_evidence(evidence_dir)
    if _json(evidence_dir / "hardware-analysis.json") != expected_analysis:
        raise ValueError("committed hardware analysis is stale or inconsistent")
    manifest = _json(evidence_dir / "manifest.json")
    if manifest.get("schema_version") != MANIFEST_SCHEMA or not isinstance(manifest.get("files"), list):
        raise ValueError("manifest schema is invalid")
    expected_paths = {entry["path"] for entry in _manifest_entries(evidence_dir)}
    actual_paths = set()
    for entry in manifest["files"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
            raise ValueError("manifest entry is invalid")
        relative = Path(entry["path"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("manifest path escapes evidence directory")
        path = evidence_dir / relative
        actual_paths.add(entry["path"])
        if not path.is_file() or entry.get("bytes") != path.stat().st_size or entry.get("sha256") != _sha256(path):
            raise ValueError(f"manifest mismatch for {entry['path']}")
    if actual_paths != expected_paths:
        raise ValueError("manifest file set is incomplete")
    return {
        "platform_count": 2,
        "analysis_valid": True,
        "manifest_valid": True,
        "manifest_files": len(actual_paths),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate LoomQ hardware evidence")
    parser.add_argument("--evidence-dir", type=Path, default=Path(__file__).resolve().parents[1] / "evidence")
    parser.add_argument("--write", action="store_true", help="recompute analysis and integrity manifest")
    args = parser.parse_args()
    if args.write:
        write_evidence_bundle(args.evidence_dir)
    print(json.dumps(validate_evidence(args.evidence_dir), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
