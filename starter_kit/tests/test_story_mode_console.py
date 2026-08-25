import unittest
from pathlib import Path


WEB = Path(__file__).resolve().parents[1] / "web"


class StoryModeConsoleTests(unittest.TestCase):
    def test_console_has_recoverable_backup(self):
        self.assertTrue((WEB / "console.backup.html").exists())
        self.assertTrue((WEB / "console.backup.css").exists())
        self.assertTrue((WEB / "console.backup.js").exists())

    def test_console_turns_experiment_steps_into_story_beats(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        for marker in ("story-mode", "她的第八十年", "先留下预测", "只改变一扇门", "带证据归来"):
            self.assertIn(marker, page)
        self.assertIn("assets/story/zero-point-station.png", page)
        self.assertIn("data-story-case", page)
        self.assertIn("零基础也能直接用", page)
        self.assertIn("data-beginner-demo-replay", page)

    def test_story_mode_explains_evidence_boundary_in_place(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("故事里的选择由实验留下证据", page)
        self.assertIn("插画与台词不参与量子判定", page)

    def test_zero_beginner_intro_has_a_moving_ball_and_three_steps(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        css = (WEB / "enhancements.css").read_text(encoding="utf-8")
        js = (WEB / "app.js").read_text(encoding="utf-8")
        for marker in ("beginner-intro", "qubit-demo-ball", "从一个小球开始", "看懂结果"):
            self.assertIn(marker, page)
        self.assertIn("@keyframes qubitTravel", css)
        self.assertIn("initBeginnerDemo", js)
        self.assertIn("data-beginner-demo-replay", page)
        self.assertIn("prefers-reduced-motion", js)


if __name__ == "__main__":
    unittest.main()
