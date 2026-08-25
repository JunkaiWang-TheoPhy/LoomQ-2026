import json
import threading
import unittest
import urllib.error
import urllib.request

from loomq.web import create_server


class StoryWorldWebTests(unittest.TestCase):
    def setUp(self):
        self.server = create_server("127.0.0.1", 0)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_story_world_endpoint_returns_mainline_and_five_cases(self):
        with urllib.request.urlopen(self.base + "/api/story-world", timeout=3) as response:
            payload = json.loads(response.read())

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["mainline"]["id"], "observer-zero")
        self.assertEqual(payload["cases"][0]["id"], "eightieth-year")
        self.assertEqual(len(payload["cases"]), 5)
        self.assertIn("body_sha256", payload["integrity"])

    def test_story_world_endpoint_recomputes_progress_from_query(self):
        url = self.base + "/api/story-world?completed=observer-zero,eightieth-year"
        with urllib.request.urlopen(url, timeout=3) as response:
            payload = json.loads(response.read())

        self.assertEqual(response.status, 200)
        self.assertEqual(payload["progress"]["mainline"], "complete")
        self.assertEqual(payload["progress"]["cases"]["eightieth-year"], "complete")
        self.assertEqual(payload["progress"]["cases"]["second-badge"], "current")

    def test_story_world_endpoint_rejects_unknown_completion(self):
        with self.assertRaises(urllib.error.HTTPError) as caught:
            urllib.request.urlopen(self.base + "/api/story-world?completed=unknown", timeout=3)
        self.assertEqual(caught.exception.code, 400)


if __name__ == "__main__":
    unittest.main()
