import copy
import unittest

from loomq.eighty_year_quest import (
    CASE_ID,
    CHAPTER_IDS,
    CHOICE_IDS,
    create_state,
    current_scene,
    available_actions,
    restore_state,
    transition,
)


class EightiethYearQuestTests(unittest.TestCase):
    def test_case_has_a_seven_chapter_lifecycle(self):
        state = create_state()

        self.assertEqual(state["quest_id"], CASE_ID)
        self.assertEqual(CHAPTER_IDS, (
            "arrival", "memory-room", "divergence-probe", "copy-request",
            "family-hearing", "signature", "return-visit",
        ))
        self.assertEqual(current_scene(state)["chapter"], "arrival")
        self.assertEqual(available_actions(state), ["meet-shen-yao"])

    def test_three_memory_clues_unlock_the_replayable_probe(self):
        state = create_state()
        state = transition(state, "meet-shen-yao")
        for clue in ("paper-diary", "copy-summary", "daughter-letter"):
            state = transition(state, f"collect-{clue}")

        self.assertEqual(state["chapter"], "divergence-probe")
        self.assertIn("run-memory-probe", available_actions(state))
        self.assertEqual(len(state["clues"]), 3)

    def test_probe_and_hearing_lead_to_three_persistent_endings(self):
        for choice in CHOICE_IDS:
            state = create_state()
            state = transition(state, "meet-shen-yao")
            for clue in ("paper-diary", "copy-summary", "daughter-letter"):
                state = transition(state, f"collect-{clue}")
            state = transition(state, "run-memory-probe", {"first_divergent_gate": 1})
            state = transition(state, "hear-copy-request")
            state = transition(state, "hold-family-hearing")
            state = transition(state, f"choose-{choice}")
            self.assertEqual(state["chapter"], "return-visit")
            state = transition(state, "return-to-care-home")

            self.assertEqual(state["status"], "complete")
            self.assertEqual(state["ending"], choice)
            self.assertIn("memory-dual-signature", state["evidence"])
            self.assertIn("second-badge", state["unlocks"])
            self.assertGreaterEqual(len(state["consequences"]), 2)

    def test_invalid_order_and_invalid_choice_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "cannot collect memory clue"):
            transition(create_state(), "collect-paper-diary")

        state = create_state()
        state = transition(state, "meet-shen-yao")
        for clue in ("paper-diary", "copy-summary", "daughter-letter"):
            state = transition(state, f"collect-{clue}")
        with self.assertRaisesRegex(ValueError, "probe requires evidence"):
            transition(state, "run-memory-probe")

        with self.assertRaisesRegex(ValueError, "unknown choice"):
            transition(create_state(), "choose-undecided")

    def test_restore_rejects_tampering_and_preserves_progress(self):
        state = create_state()
        state = transition(state, "meet-shen-yao")
        restored = restore_state(copy.deepcopy(state))
        self.assertEqual(restored, state)

        tampered = copy.deepcopy(state)
        tampered["chapter"] = "signature"
        with self.assertRaisesRegex(ValueError, "state invariant"):
            restore_state(tampered)


if __name__ == "__main__":
    unittest.main()
