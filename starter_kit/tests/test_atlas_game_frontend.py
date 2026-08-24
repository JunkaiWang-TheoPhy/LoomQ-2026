import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class AtlasGameFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_investigation_actions_unlock_the_world_and_build_a_score(self):
        passport = {
            "schema_version": "loomq-inquiry-passport-v1",
            "conclusion_audits": {
                "h-opens-branches-cx-correlates": {
                    "status": "supported",
                    "claim": "H creates branches and CX changes correlation.",
                    "reason": "The controlled experiment changes at g2.",
                }
            },
        }
        script = """
const game = require(process.argv[1]);
let state = game.createGame();
const initial = game.locationProgress(state);
for (const clue of ["state", "possibility", "repeat", "control"]) {
  state = game.collectClue(state, clue);
}
const briefed = game.locationProgress(state);
state = game.recordPrediction(state, "h-opens-branches");
state = game.attachPassport(state, JSON.parse(process.argv[2]));
const experimented = game.locationProgress(state);
state = game.auditConclusion(state, "h-opens-branches-cx-correlates");
process.stdout.write(JSON.stringify({
  initial,
  briefed,
  experimented,
  final: game.locationProgress(state),
  state,
}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "atlas_game_engine.js"),
                json.dumps(passport),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(
            [item["state"] for item in result["initial"]],
            ["current", "locked", "locked"],
        )
        self.assertEqual(
            [item["state"] for item in result["briefed"]],
            ["complete", "current", "locked"],
        )
        self.assertEqual(
            [item["state"] for item in result["experimented"]],
            ["complete", "complete", "current"],
        )
        self.assertEqual(
            [item["state"] for item in result["final"]],
            ["complete", "complete", "complete"],
        )
        self.assertEqual(result["state"]["score"], 100)
        self.assertEqual(result["state"]["audit"]["status"], "supported")

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_locked_travel_and_unknown_clues_fail_closed(self):
        script = """
const game = require(process.argv[1]);
const state = game.createGame();
const errors = [];
for (const action of [
  () => game.travel(state, "field"),
  () => game.collectClue(state, "invented"),
  () => game.attachPassport(state, {}),
]) {
  try { action(); } catch (error) { errors.push(error.message); }
}
process.stdout.write(JSON.stringify(errors));
"""
        completed = subprocess.run(
            [shutil.which("node"), "-e", script, str(ROOT / "web" / "atlas_game_engine.js")],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        errors = json.loads(completed.stdout)
        self.assertEqual(len(errors), 3)
        self.assertIn("尚未解锁", errors[0])
        self.assertIn("未知调查线索", errors[1])
        self.assertIn("实验护照", errors[2])

    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_rerunning_the_experiment_requires_a_fresh_audit(self):
        passport = {
            "schema_version": "loomq-inquiry-passport-v1",
            "conclusion_audits": {
                "supported": {
                    "status": "supported",
                    "claim": "claim",
                    "reason": "reason",
                }
            },
        }
        script = """
const game = require(process.argv[1]);
const passport = JSON.parse(process.argv[2]);
let state = game.createGame();
for (const clue of game.CLUES) state = game.collectClue(state, clue);
state = game.recordPrediction(state, "prediction");
state = game.attachPassport(state, passport);
state = game.auditConclusion(state, "supported");
state = game.attachPassport(state, passport);
process.stdout.write(JSON.stringify({state, progress: game.locationProgress(state)}));
"""
        completed = subprocess.run(
            [
                shutil.which("node"),
                "-e",
                script,
                str(ROOT / "web" / "atlas_game_engine.js"),
                json.dumps(passport),
            ],
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertIsNone(result["state"]["audit"])
        self.assertEqual(result["state"]["score"], 50)
        self.assertEqual(
            [item["state"] for item in result["progress"]],
            ["complete", "complete", "current"],
        )
