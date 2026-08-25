import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class StoryWorldFrontendContractTests(unittest.TestCase):
    def test_game_surface_exposes_a_case_board_without_duplicating_story_copy(self):
        page = (ROOT / "web" / "game.html").read_text()
        script = (ROOT / "web" / "game.js").read_text()

        self.assertIn('id="case-board"', page)
        self.assertIn('id="case-list"', page)
        self.assertIn("/api/story-world", script)
        self.assertIn("renderStoryBoard", script)
        self.assertIn("refreshStoryWorld(true)", script)
        self.assertIn("caseFile.title", script)
        self.assertNotIn("她的第八十年", script)
        self.assertNotIn("第二个工牌", script)

    def test_case_board_has_mobile_and_keyboard_contract(self):
        styles = (ROOT / "web" / "game.css").read_text()

        self.assertIn(".case-board", styles)
        self.assertIn(".case-list button:disabled", styles)
        self.assertIn("@media (max-width: 820px)", styles)
        self.assertIn(".case-board", styles.split("@media (max-width: 820px)", 1)[1])


if __name__ == "__main__":
    unittest.main()
