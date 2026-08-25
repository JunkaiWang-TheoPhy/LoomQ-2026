import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class InquiryFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_atlas_progress_unlocks_locations_from_verified_actions(self):
        script = """
const inquiry = require(process.argv[1]);
process.stdout.write(JSON.stringify([
  inquiry.atlasProgress(false, false, null),
  inquiry.atlasProgress(true, false, null),
  inquiry.atlasProgress(true, true, null),
  inquiry.atlasProgress(true, true, "unsupported"),
]));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "inquiry.js"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        initial, briefed, experimented, audited = json.loads(completed.stdout)
        self.assertEqual(
            [location["state"] for location in initial["locations"]],
            ["current", "locked", "locked"],
        )
        self.assertEqual(
            [location["state"] for location in briefed["locations"]],
            ["complete", "current", "locked"],
        )
        self.assertEqual(
            [location["state"] for location in experimented["locations"]],
            ["complete", "complete", "current"],
        )
        self.assertEqual(
            [location["state"] for location in audited["locations"]],
            ["complete", "complete", "complete"],
        )
        self.assertIn("调查规则", initial["message"])
        self.assertIn("对照实验", briefed["message"])
        self.assertIn("审计结论", experimented["message"])
        self.assertIn("案件归档", audited["message"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_story_progress_marks_the_learners_next_chapter(self):
        script = """
const inquiry = require(process.argv[1]);
process.stdout.write(JSON.stringify([
  inquiry.journeyProgress(false, null),
  inquiry.journeyProgress(true, null),
  inquiry.journeyProgress(true, "unsupported"),
]));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "inquiry.js"),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        before, experimented, audited = json.loads(completed.stdout)
        self.assertEqual(
            [chapter["state"] for chapter in before["chapters"]],
            ["current", "upcoming", "upcoming"],
        )
        self.assertEqual(before["message"], "第一幕：先留下你的预测。")
        self.assertEqual(
            [chapter["state"] for chapter in experimented["chapters"]],
            ["complete", "complete", "current"],
        )
        self.assertEqual(experimented["message"], "第三幕：根据同一次实验形成结论。")
        self.assertEqual(
            [chapter["state"] for chapter in audited["chapters"]],
            ["complete", "complete", "complete"],
        )
        self.assertEqual(audited["message"], "旅程完成：护照记录了预测、实验与证据边界。")

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_view_model_turns_passport_evidence_into_beginner_observations(self):
        passport = {
            "prediction_review": {
                "status": "revised",
                "reason": "删掉 CX 后仍出现 00、01 两个分支。",
            },
            "experiment": {
                "control": {"probabilities": {"00": 0.5, "11": 0.5}},
                "variant": {"probabilities": {"00": 0.5, "01": 0.5}},
            },
            "comparison": {
                "first_divergent_gate": 1,
                "reference_operation": {"gate": "cx"},
            },
            "conclusion_audit": {
                "status": "unsupported",
                "claim": "CX 建立了最初的两个分支。",
                "reason": "删掉 CX 后仍观察到 00、01 两个分支。",
            },
            "scope_caveats": ["不能单独证明 Bell 非定域性"],
        }
        script = """
const inquiry = require(process.argv[1]);
const passport = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify({
  request: inquiry.requestPayload("cx-opens-branches", "cx-opens-branches", 128),
  headings: ["supported", "unsupported", "inconclusive"].map(inquiry.auditHeading),
  view: inquiry.viewModel(passport),
}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "inquiry.js"),
                json.dumps(passport, ensure_ascii=False),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(
            result["request"],
            {
                "mission": "bell-gates",
                "prediction": "cx-opens-branches",
                "conclusion": "cx-opens-branches",
                "shots": 128,
            },
        )
        self.assertEqual(
            result["headings"],
            [
                "证据支持这条结论",
                "证据不支持这条结论",
                "本次证据不足以判断",
            ],
        )
        view = result["view"]
        self.assertEqual(
            view["controlBars"],
            [
                {"state": "00", "probability": 0.5, "percent": "50.0%"},
                {"state": "11", "probability": 0.5, "percent": "50.0%"},
            ],
        )
        self.assertEqual(
            view["variantBars"],
            [
                {"state": "00", "probability": 0.5, "percent": "50.0%"},
                {"state": "01", "probability": 0.5, "percent": "50.0%"},
            ],
        )
        self.assertEqual(view["divergence"], "g2 · CX")
        self.assertEqual(view["predictionStatus"], "revised")
        self.assertEqual(view["auditStatus"], "unsupported")
        self.assertIn("00、01", view["variantObservation"])
        self.assertIn("不能单独证明", view["caveat"])

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_selecting_a_conclusion_reuses_the_existing_passport(self):
        passport = {
            "learner": {
                "prediction": "h-opens-branches",
                "conclusion": "h-opens-branches-cx-correlates",
            },
            "conclusion_audit": {"status": "supported"},
            "conclusion_audits": {
                "h-opens-branches-cx-correlates": {"status": "supported"},
                "cx-opens-branches": {"status": "unsupported"},
            },
            "experiment": {"stable": "same-counts"},
            "replay": {
                "endpoint": "/api/inquiry",
                "request": {
                    "mission": "bell-gates",
                    "prediction": "h-opens-branches",
                    "conclusion": "h-opens-branches-cx-correlates",
                    "shots": 128,
                },
            },
        }
        script = """
const inquiry = require(process.argv[1]);
const passport = JSON.parse(process.argv[2]);
process.stdout.write(JSON.stringify(
  inquiry.withConclusion(passport, "cx-opens-branches")
));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "inquiry.js"),
                json.dumps(passport),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        selected = json.loads(completed.stdout)
        self.assertEqual(selected["learner"]["conclusion"], "cx-opens-branches")
        self.assertEqual(selected["conclusion_audit"]["status"], "unsupported")
        self.assertEqual(selected["experiment"], passport["experiment"])
        self.assertEqual(
            selected["replay"]["request"]["conclusion"], "cx-opens-branches"
        )

    def test_audit_button_uses_the_current_passport_without_requesting_again(self):
        source = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
        handler = source.split('$("#audit-inquiry")', 1)[1].split(
            '$("#inquiry-prediction")', 1
        )[0]
        self.assertIn("currentInquiryPassport", handler)
        self.assertIn("withConclusion", handler)
        self.assertNotIn("requestInquiry()", handler)


if __name__ == "__main__":
    unittest.main()
