import json
import shutil
import tempfile
import unittest
from pathlib import Path

from scripts.validate_hardware_evidence import (
    analyze_evidence,
    decode_spinq_msgpack,
    validate_evidence,
    write_evidence_bundle,
)


EVIDENCE = Path(__file__).resolve().parents[1] / "evidence"


class HardwareEvidenceTests(unittest.TestCase):
    def test_provider_msgpack_decodes_to_committed_json_probabilities(self):
        decoded = decode_spinq_msgpack(EVIDENCE / "files" / "spinq-result.msgpack")
        committed = json.loads((EVIDENCE / "files" / "spinq-result.json").read_text())

        self.assertEqual(decoded, committed["probabilities"])
        self.assertAlmostEqual(sum(decoded.values()), 1.0, places=7)

    def test_analysis_reports_origin_confidence_and_spinq_distance(self):
        analysis = analyze_evidence(EVIDENCE)

        origin = analysis["platforms"]["originq"]
        self.assertEqual(origin["ideal_peak_shots"], 958)
        self.assertEqual(origin["shots"], 1000)
        self.assertLess(origin["wilson_95_interval"][0], 0.958)
        self.assertGreater(origin["wilson_95_interval"][1], 0.958)

        spinq = analysis["platforms"]["spinq"]
        self.assertEqual(spinq["dominant_state"], "00")
        self.assertAlmostEqual(spinq["ideal_peak_probability"], 0.66866048)
        self.assertAlmostEqual(spinq["total_variation_from_ideal_bell"], 0.331339515)
        self.assertEqual(spinq["uncertainty_note"], "provider returned projection probabilities, not shot counts")

    def test_committed_bundle_validates_hashes_and_derived_analysis(self):
        result = validate_evidence(EVIDENCE)

        self.assertEqual(result["platform_count"], 2)
        self.assertTrue(result["manifest_valid"])
        self.assertTrue(result["analysis_valid"])

    def test_manifest_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as temp:
            copied = Path(temp) / "evidence"
            shutil.copytree(EVIDENCE, copied)
            write_evidence_bundle(copied)
            with (copied / "files" / "originq-bell.qasm").open("a") as handle:
                handle.write("// changed\n")

            with self.assertRaisesRegex(ValueError, "manifest"):
                validate_evidence(copied)


if __name__ == "__main__":
    unittest.main()
