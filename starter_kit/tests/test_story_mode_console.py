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

    def test_quantum_basics_are_told_as_shenyaos_lesson(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        for marker in ("quantum-basics", "沈遥给新观察员", "状态", "叠加", "测量", "纠缠", "干涉"):
            self.assertIn(marker, page)

    def test_case_cards_open_the_interactive_case_page(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        case_page = (WEB / "case.html").read_text(encoding="utf-8")
        for case_id in ("eightieth-year", "second-badge", "inside-tide-line", "night-grid", "testimony-checker"):
            self.assertIn(f"case.html?case={case_id}", page)
        for marker in ("case-intro", "case-interaction", "case-summary", "进行一次小实验", "你学会了"):
            self.assertIn(marker, case_page)

    def test_home_story_introduction_uses_researcher_daily_life_language(self):
        page = (WEB / "index.html").read_text(encoding="utf-8")
        self.assertIn("researcher-diary", page)
        for phrase in ("清晨", "午后", "夜里", "沈遥", "研究员"):
            self.assertIn(phrase, page)
        opening = page[: page.index('<section class="story-hero"')]
        self.assertNotIn("CX", opening)
        self.assertNotIn("QASM", opening)
        case_js = (WEB / "case.js").read_text(encoding="utf-8")
        self.assertGreaterEqual(case_js.count("question:"), 5)
        self.assertGreaterEqual(case_js.count("lesson:"), 5)
        self.assertIn("location.protocol === \"file:\"", case_js)
        self.assertIn("文件预览演示", case_js)


if __name__ == "__main__":
    unittest.main()
