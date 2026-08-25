import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


class DoubleLifeSceneContractTests(unittest.TestCase):
    def test_scene_registry_declares_paired_land_and_space_maps(self):
        source = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn("doubleLifeScenes", source)
        self.assertIn("double-life-village-earth-2d.png", source)
        self.assertIn("double-life-village-cosmos-2d.png", source)
        self.assertNotIn('/assets/story/double-life-village-earth-2d.png', source)
        self.assertTrue((WEB / "assets/story/double-life-village-earth-2d.png").exists())
        self.assertTrue((WEB / "assets/story/double-life-village-cosmos-2d.png").exists())

    def test_scene_stage_uses_full_frame_without_cover_crop(self):
        html = (WEB / "index.html").read_text(encoding="utf-8")
        css = (WEB / "enhancements.css").read_text(encoding="utf-8")
        self.assertIn('href="styles.css"', html)
        self.assertIn('src="assets/story/double-life-village-earth-2d.png"', html)
        self.assertNotIn('href="/styles.css"', html)
        self.assertIn('data-double-life-stage', html)
        self.assertIn('class="double-life-layer', html)
        self.assertIn("aspect-ratio: 3 / 2", css)
        self.assertIn("object-fit: fill", css)
        self.assertNotIn("object-fit: cover", css[css.index(".double-life-stage"):css.index(".double-life-stage") + 1800])

    def test_entering_scene_can_trigger_quantum_transition_notice(self):
        source = (WEB / "app.js").read_text(encoding="utf-8")
        self.assertIn("quantum-superposition", source)
        self.assertIn("quantum-entanglement", source)
        self.assertIn("Math.random()", source)
        self.assertIn("prefers-reduced-motion", source)
        self.assertIn("visibilitychange", source)


if __name__ == "__main__":
    unittest.main()
