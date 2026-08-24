import copy
import unittest

from riscv_emulator import TinyRISCVEmulator


NOT_TAKEN_BRANCH_PROGRAM = """\
li x1, 1
li x2, 1
bne x1, x2, ELSE
li x3, 7
j END
ELSE:
li x3, 9
END:
"""

TAKEN_BRANCH_PROGRAM = """\
li x1, 1
li x2, 1
beq x1, x2, ELSE
li x3, 7
j END
ELSE:
li x3, 9
END:
"""

LOOP_PROGRAM = """\
addi x1, x1, 1
j LOOP
LOOP:
j LOOP
"""


class RiscvTraceTests(unittest.TestCase):
    def test_branch_trace_records_decision_register_delta_and_pc(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program(NOT_TAKEN_BRANCH_PROGRAM)

        report = emulator.execute_with_trace()

        branch = next(event for event in report["events"] if event["operation"] == "bne")
        self.assertFalse(branch["branch"]["taken"])
        self.assertEqual(branch["pc"], 2)
        self.assertEqual(branch["register_changes"], {})
        self.assertEqual(branch["branch"]["target_label"], "ELSE")
        self.assertEqual(branch["branch"]["target_pc"], 5)
        self.assertEqual(report["final_registers"]["x3"], 7)
        self.assertIn(branch, report["branches"])
        self.assertTrue(report["terminated"])

    def test_taken_branch_records_target_pc_and_replay_matches_original(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program(TAKEN_BRANCH_PROGRAM)

        report = emulator.execute_with_trace()
        branch = next(event for event in report["events"] if event["operation"] == "beq")

        self.assertTrue(branch["branch"]["taken"])
        self.assertEqual(branch["next_pc"], 5)
        self.assertEqual(report["final_registers"]["x3"], 9)
        self.assertEqual(emulator.replay_trace(report), report)

    def test_execute_and_trace_share_the_same_sparse_final_register_view(self):
        traced = TinyRISCVEmulator()
        traced.load_program("li x1, 4\naddi x2, x1, 3\n")

        plain = TinyRISCVEmulator()
        plain.load_program("li x1, 4\naddi x2, x1, 3\n")

        self.assertEqual(plain.execute(), traced.execute_with_trace()["final_registers"])

    def test_replay_rejects_trace_tampering(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program(TAKEN_BRANCH_PROGRAM)
        report = emulator.execute_with_trace()
        tampered = copy.deepcopy(report)
        tampered["events"][0]["register_changes"]["x1"] = 99

        with self.assertRaisesRegex(ValueError, "trace integrity"):
            emulator.replay_trace(tampered)

    def test_replay_rejects_program_mismatch(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program(TAKEN_BRANCH_PROGRAM)
        report = emulator.execute_with_trace()
        emulator.load_program("li x1, 3\n")

        with self.assertRaisesRegex(ValueError, "program digest"):
            emulator.replay_trace(report)

    def test_load_program_clears_stale_trace_state(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program(TAKEN_BRANCH_PROGRAM)
        first = emulator.execute_with_trace()

        emulator.load_program("li x5, 12\n")
        second = emulator.execute_with_trace()

        self.assertNotEqual(first["program_digest"], second["program_digest"])
        self.assertEqual(second["events"][0]["pc"], 0)
        self.assertEqual(second["steps"], 1)
        self.assertEqual(second["final_registers"], {"x5": 12})

    def test_undefined_branch_label_raises_in_trace_mode(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program("beq x1, x2, MISSING\n")

        with self.assertRaisesRegex(ValueError, "未定义的跳转标签: MISSING"):
            emulator.execute_with_trace()

    def test_trace_mode_preserves_x0_immutability(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program("li x0, 7\naddi x1, x0, 2\n")

        report = emulator.execute_with_trace()

        self.assertEqual(report["initial_registers"], {})
        self.assertEqual(report["final_registers"], {"x1": 2})
        self.assertNotIn("x0", report["final_registers"])

    def test_trace_mode_keeps_step_limit(self):
        emulator = TinyRISCVEmulator()
        emulator.load_program(LOOP_PROGRAM)
        emulator.max_steps = 3

        with self.assertRaisesRegex(RuntimeError, "最大步数限制"):
            emulator.execute_with_trace()


if __name__ == "__main__":
    unittest.main()
