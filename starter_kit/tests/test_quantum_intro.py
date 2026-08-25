import json
import threading
import unittest
import urllib.request
from pathlib import Path

from loomq.quantum_intro import (
    GUIDE_LESSONS,
    WORLD_FACES,
    build_quantum_intro,
    measure_quantum_coin,
)
from loomq.web import create_server


class QuantumIntroTests(unittest.TestCase):
    WEB_ROOT = Path(__file__).resolve().parents[1] / "web"

    def test_guide_teaches_bell_inequality_before_game_mechanics(self):
        guide = build_quantum_intro()
        topics = [lesson["id"] for lesson in guide["lessons"]]
        self.assertEqual(topics[:3], ["bit-and-measurement", "superposition", "entanglement"])
        bell = next(lesson for lesson in guide["lessons"] if lesson["id"] == "bell-inequality")
        self.assertIn("Bell", bell["title"])
        self.assertIn("局部", bell["concept"])
        self.assertEqual(guide["mechanic"]["outcome_faces"], ["village", "cosmos"])

    def test_coin_faces_are_world_textures_and_measurement_is_local_simulation(self):
        self.assertEqual(set(WORLD_FACES), {"village", "cosmos"})
        village = measure_quantum_coin(outcome=0)
        cosmos = measure_quantum_coin(outcome=1)
        self.assertEqual(village["face"], "village")
        self.assertEqual(cosmos["face"], "cosmos")
        self.assertEqual(village["source"], "local-exact-simulator")
        self.assertEqual(village["qasm"], cosmos["qasm"])
        self.assertEqual(village["probabilities"], {"0": 0.5, "1": 0.5})

    def test_web_exposes_intro_and_measurement_without_model_credentials(self):
        server = create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://{server.server_address[0]}:{server.server_port}"
        try:
            with urllib.request.urlopen(base + "/api/quantum-intro", timeout=3) as response:
                intro = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(intro["mechanic"]["outcome_faces"], ["village", "cosmos"])
            request = urllib.request.Request(
                base + "/api/quantum-intro/measure",
                data=b'{"outcome":1}',
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(request, timeout=3) as response:
                measured = json.loads(response.read())
            self.assertEqual(response.status, 200)
            self.assertEqual(measured["face"], "cosmos")
            self.assertEqual(measured["source"], "local-exact-simulator")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_web_presents_guide_before_the_rpg_and_keeps_agent_optional(self):
        html = (self.WEB_ROOT / "index.html").read_text(encoding="utf-8")
        javascript = (self.WEB_ROOT / "quantum-guide.js").read_text(encoding="utf-8")
        self.assertIn('id="quantum-guide"', html)
        self.assertIn('id="quantum-guide-measure"', html)
        self.assertIn('src="/quantum-guide.js"', html)
        self.assertIn("/api/quantum-intro/measure", javascript)
        self.assertIn("local-exact-simulator", javascript)


if __name__ == "__main__":
    unittest.main()
