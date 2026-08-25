import copy
import hashlib
import json
import unittest

from loomq.qasm import parse_qasm
from loomq.story_world import (
    CASE_IDS,
    MAINLINE_ID,
    SCHEMA_VERSION,
    build_story_world,
    story_progress,
    verify_story_world,
)


class StoryWorldContractTests(unittest.TestCase):
    def test_zero_point_observer_is_the_only_root_and_five_cases_are_map_nodes(self):
        world = build_story_world()

        self.assertEqual(world["schema_version"], SCHEMA_VERSION)
        self.assertEqual(world["mainline"]["id"], MAINLINE_ID)
        self.assertEqual(len(world["cases"]), 5)
        self.assertEqual([case["id"] for case in world["cases"]], list(CASE_IDS))
        self.assertTrue(all(case["kind"] == "case" for case in world["cases"]))
        self.assertTrue(all(case["prerequisites"] == [MAINLINE_ID] for case in world["cases"]))

    def test_each_case_has_double_identity_evidence_action_and_scientific_boundary(self):
        world = build_story_world()

        required_identity_keys = {"public", "hidden"}
        required_evidence_keys = {"mode", "reference_qasm", "variant_qasm", "changed_variable"}
        for case in world["cases"]:
            self.assertEqual(set(case["identities"]), required_identity_keys)
            self.assertTrue(case["identities"]["public"])
            self.assertTrue(case["identities"]["hidden"])
            self.assertTrue(required_evidence_keys.issubset(case["evidence_contract"]))
            self.assertTrue(case["claim_boundary"])
            parse_qasm(case["evidence_contract"]["reference_qasm"])
            parse_qasm(case["evidence_contract"]["variant_qasm"])

    def test_progression_is_mainline_then_cases_then_archive(self):
        self.assertEqual(
            story_progress([]),
            {
                "mainline": "current",
                "cases": {case_id: "locked" for case_id in CASE_IDS},
                "archive": "locked",
            },
        )
        self.assertEqual(
            story_progress([MAINLINE_ID])["mainline"],
            "complete",
        )
        self.assertTrue(
            all(
                status == "current"
                for status in story_progress([MAINLINE_ID])["cases"].values()
            )
        )
        completed = [MAINLINE_ID, *CASE_IDS]
        progress = story_progress(completed)
        self.assertEqual(progress["archive"], "current")
        self.assertTrue(all(status == "complete" for status in progress["cases"].values()))

    def test_world_digest_is_deterministic_and_tamper_evident(self):
        first = build_story_world([MAINLINE_ID, CASE_IDS[0]])
        second = build_story_world([CASE_IDS[0], MAINLINE_ID])
        self.assertEqual(first, second)
        self.assertTrue(verify_story_world(first)["valid"])

        tampered = copy.deepcopy(first)
        tampered["cases"][0]["title"] = "伪造案件"
        result = verify_story_world(tampered)
        self.assertFalse(result["valid"])
        self.assertIn("integrity", result["reason"])

    def test_unknown_completion_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unknown story node"):
            story_progress(["not-a-real-case"])


if __name__ == "__main__":
    unittest.main()
