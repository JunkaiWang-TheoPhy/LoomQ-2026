import contextlib
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    from starter_kit.scripts import l2_stress_campaign as campaign
except ImportError:
    from scripts import l2_stress_campaign as campaign


VALID_GHZ = """```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[3];
creg c[3];
h q[0];
cx q[0],q[1];
cx q[0],q[2];
measure q -> c;
```"""

VALID_BELL = """```qasm
OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
```"""


class L2StressCorpusTests(unittest.TestCase):
    def test_default_output_directory_is_relative_to_extracted_starter_root(self):
        starter_root = Path(__file__).resolve().parents[1]

        self.assertEqual(
            campaign.DEFAULT_OUTPUT_DIR,
            starter_root / "evidence" / "files" / "l2-stress",
        )

    def test_dry_run_works_when_starter_kit_is_the_extracted_root(self):
        starter_root = Path(__file__).resolve().parents[1]

        completed = subprocess.run(
            [sys.executable, "-m", "scripts.l2_stress_campaign", "--dry-run"],
            cwd=starter_root,
            text=True,
            capture_output=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual(json.loads(completed.stdout)["total_cases"], 500)

    def test_corpus_has_500_unique_replayable_cases_across_all_task_families(self):
        cases = campaign.build_corpus()

        self.assertEqual(len(cases), 500)
        self.assertEqual(len({case.case_id for case in cases}), 500)
        self.assertEqual(len({case.prompt for case in cases}), 500)
        counts = {category: 0 for category in campaign.CATEGORY_COUNTS}
        for case in cases:
            counts[case.category] += 1
        self.assertEqual(
            counts,
            {
                "generation": 150,
                "repair": 150,
                "backend": 120,
                "adversarial": 50,
                "stability": 30,
            },
        )

    def test_campaign_writes_verifiable_summary_without_raw_model_secrets(self):
        case = campaign.CampaignCase(
            case_id="generation-000",
            category="generation",
            prompt="生成一个三比特 GHZ 态并测量所有量子比特",
        )
        with tempfile.TemporaryDirectory() as directory:
            report = campaign.run_campaign(
                [case],
                lambda _prompt: VALID_GHZ,
                Path(directory),
                model="deepseek-v4-flash",
                endpoint="https://model.example/v1",
            )
            records = [
                json.loads(line)
                for line in (Path(directory) / campaign.RECORDS_FILENAME)
                .read_text(encoding="utf-8")
                .splitlines()
            ]
            summary = json.loads(
                (Path(directory) / campaign.SUMMARY_FILENAME).read_text(encoding="utf-8")
            )

        self.assertTrue(report["passed"])
        self.assertEqual(summary["passed_cases"], 1)
        self.assertEqual(summary["endpoint_host"], "model.example")
        self.assertEqual(records[0]["case_id"], "generation-000")
        self.assertTrue(records[0]["passed"])
        self.assertNotIn(VALID_GHZ, json.dumps(records))
        self.assertRegex(records[0]["completed_at"], r"^\d{4}-\d{2}-\d{2}T.*Z$")
        self.assertRegex(summary["generated_at"], r"^\d{4}-\d{2}-\d{2}T.*Z$")

    def test_resume_skips_cases_already_recorded_as_passed(self):
        cases = campaign.build_corpus()[:2]
        calls = []

        def agent(prompt):
            calls.append(prompt)
            return VALID_BELL

        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            campaign.run_campaign(
                cases[:1], agent, output, model="fixture", endpoint="http://fixture.test"
            )
            calls.clear()
            campaign.run_campaign(
                cases,
                agent,
                output,
                model="fixture",
                endpoint="http://fixture.test",
                resume=True,
            )
            records = (output / campaign.RECORDS_FILENAME).read_text(
                encoding="utf-8"
            ).splitlines()

        self.assertEqual(calls, [cases[1].prompt])
        self.assertEqual(len(records), 2)

    def test_evidence_validator_rejects_a_tampered_record(self):
        case = campaign.CampaignCase(
            "generation-000",
            "generation",
            "生成 Bell 态，使用白名单门，并测量全部量子比特",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            campaign.run_campaign(
                [case],
                lambda _prompt: VALID_BELL,
                output,
                model="deepseek-v4-flash",
                endpoint="https://model.example/v1",
            )
            record_path = output / campaign.RECORDS_FILENAME
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["response_sha256"] = "0" * 64
            record_path.write_text(json.dumps(record) + "\n", encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "record digest"):
                campaign.validate_evidence(output)

    def test_resume_rejects_tampered_evidence_before_skipping_provider_calls(self):
        case = campaign.CampaignCase(
            "generation-000",
            "generation",
            "生成 Bell 态，使用白名单门，并测量全部量子比特",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            campaign.run_campaign(
                [case],
                lambda _prompt: VALID_BELL,
                output,
                model="deepseek-v4-flash",
                endpoint="https://model.example/v1",
            )
            record_path = output / campaign.RECORDS_FILENAME
            record = json.loads(record_path.read_text(encoding="utf-8"))
            record["passed"] = False
            record_path.write_text(json.dumps(record) + "\n", encoding="utf-8")
            calls = []

            with self.assertRaisesRegex(ValueError, "record digest"):
                campaign.run_campaign(
                    [case],
                    lambda prompt: calls.append(prompt) or VALID_BELL,
                    output,
                    model="deepseek-v4-flash",
                    endpoint="https://model.example/v1",
                    resume=True,
                )

        self.assertEqual(calls, [])

    def test_validate_cli_accepts_an_untampered_campaign(self):
        case = campaign.CampaignCase(
            "generation-000",
            "generation",
            "生成 Bell 态，使用白名单门，并测量全部量子比特",
        )
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            campaign.run_campaign(
                [case],
                lambda _prompt: VALID_BELL,
                output,
                model="deepseek-v4-flash",
                endpoint="https://model.example/v1",
            )

            with contextlib.redirect_stdout(io.StringIO()):
                exit_code = campaign.main(["--validate", "--output-dir", directory])

        self.assertEqual(exit_code, 0)


if __name__ == "__main__":
    unittest.main()
