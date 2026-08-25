import json
import os
import threading
import unittest
import urllib.error
import urllib.request

from loomq.hardware import HardwareGateway, normalize_hardware_result
from loomq.web import create_server
from pathlib import Path


class HardwareGatewayTests(unittest.TestCase):
    WEB_ROOT = Path(__file__).resolve().parents[1] / "web"

    def test_discovery_never_calls_a_backend_ready_without_credentials(self):
        gateway = HardwareGateway(env={})
        statuses = {item["id"]: item for item in gateway.discover()}
        self.assertEqual(statuses["originq_wukong"]["status"], "configuration_required")
        self.assertEqual(statuses["spinq_cloud_qpu"]["status"], "configuration_required")
        self.assertEqual(statuses["originq_wukong"]["credential_env"], "LOOMQ_ORIGINQ_TOKEN")

    def test_fixture_job_has_explicit_non_hardware_provenance(self):
        gateway = HardwareGateway(env={"LOOMQ_HARDWARE_FIXTURE": "1"})
        job = gateway.submit("OPENQASM 2.0;", "originq_wukong", 128)
        self.assertEqual(job["status"], "queued")
        result = gateway.poll(job["job_id"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["provenance"]["kind"], "fixture")
        self.assertNotEqual(result["provenance"]["kind"], "hardware")

    def test_normalizer_preserves_job_and_rejects_incomplete_payload(self):
        payload = normalize_hardware_result(
            {
                "backend": "originq_wukong",
                "job_id": "job-123",
                "shots": 8,
                "counts": {"0": 5, "1": 3},
                "bit_order": "little",
                "timestamp": "2026-08-25T10:00:00Z",
                "provenance": {"kind": "hardware", "provider": "originq"},
            }
        )
        self.assertEqual(payload["counts"], {"0": 5, "1": 3})
        self.assertEqual(payload["provenance"]["kind"], "hardware")
        with self.assertRaises(ValueError):
            normalize_hardware_result({"backend": "originq_wukong", "counts": {"0": 1}})

    def test_web_exposes_readiness_and_fixture_job_lifecycle(self):
        old = os.environ.get("LOOMQ_HARDWARE_FIXTURE")
        os.environ["LOOMQ_HARDWARE_FIXTURE"] = "1"
        server = create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://{server.server_address[0]}:{server.server_port}"
        try:
            with urllib.request.urlopen(base + "/api/hardware/backends", timeout=3) as response:
                catalog = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertTrue(any(item["id"] == "originq_wukong" for item in catalog["backends"]))
            request = urllib.request.Request(
                base + "/api/hardware/submit",
                data=json.dumps({"backend": "originq_wukong", "qasm": "OPENQASM 2.0;", "shots": 64}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=3) as response:
                job = json.loads(response.read())
            self.assertEqual(response.status, 202)
            with urllib.request.urlopen(base + "/api/hardware/jobs/" + job["job_id"], timeout=3) as response:
                result = json.loads(response.read())
            self.assertEqual(result["provenance"]["kind"], "fixture")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
            if old is None:
                os.environ.pop("LOOMQ_HARDWARE_FIXTURE", None)
            else:
                os.environ["LOOMQ_HARDWARE_FIXTURE"] = old

    def test_web_reports_missing_provider_adapter_as_service_unavailable(self):
        server = create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://{server.server_address[0]}:{server.server_port}"
        try:
            request = urllib.request.Request(
                base + "/api/hardware/submit",
                data=json.dumps({"backend": "originq_wukong", "qasm": "OPENQASM 2.0;", "shots": 8}).encode(),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=3)
            self.assertEqual(raised.exception.code, 503)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_hardware_console_explains_live_provenance_before_submit(self):
        html = (self.WEB_ROOT / "index.html").read_text(encoding="utf-8")
        javascript = (self.WEB_ROOT / "hardware.js").read_text(encoding="utf-8")
        self.assertIn('id="hardware-console"', html)
        self.assertIn('id="hardware-submit"', html)
        self.assertIn("configuration_required", javascript)
        self.assertIn("provenance", javascript)


if __name__ == "__main__":
    unittest.main()
