import json
import shutil
import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EightiethYearFrontendTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"), "Node.js is optional")
    def test_browser_quest_engine_preserves_choice_and_unlocks_next_case(self):
        script = """
const quest = require(process.argv[1]);
let state = quest.createState();
for (const action of [
  "meet-shen-yao",
  "collect-paper-diary",
  "collect-copy-summary",
  "collect-daughter-letter",
]) state = quest.transition(state, action);
state = quest.transition(state, "run-memory-probe", {first_divergent_gate: 1});
state = quest.transition(state, "hear-copy-request");
state = quest.transition(state, "hold-family-hearing");
state = quest.transition(state, "choose-dual-signature");
state = quest.transition(state, "return-to-care-home");
process.stdout.write(JSON.stringify({chapter: state.chapter, status: state.status, ending: state.ending, unlocks: state.unlocks, consequences: state.consequences}));
"""
        completed = subprocess.run(
            [shutil.which("node"), "-e", script, str(ROOT / "web" / "eighty_year_quest.js")],
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "complete")
        self.assertEqual(result["ending"], "dual-signature")
        self.assertIn("second-badge", result["unlocks"])
        self.assertEqual(len(result["consequences"]), 2)

    def test_game_loads_the_quest_engine_without_copying_case_prose(self):
        page = (ROOT / "web" / "game.html").read_text()
        script = (ROOT / "web" / "game.js").read_text()
        self.assertIn('/eighty-year-quest.js', page)
        self.assertIn('openEightyYearQuest', script)
        self.assertIn('questEngine', script)
        self.assertIn('eightyQuest.status === "complete"', script)
        self.assertNotIn('一个人的数字记忆比本人更容易被照护时', script)
        self.assertNotIn('青年副本请求删除一段记忆', script)


if __name__ == "__main__":
    unittest.main()
