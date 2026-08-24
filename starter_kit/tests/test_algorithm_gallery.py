import unittest
from pathlib import Path

import adapter
from loomq.qasm import parse_qasm
from loomq.simulator import trace_statevector


ROOT = Path(__file__).resolve().parents[1]


class AlgorithmGalleryTests(unittest.TestCase):
    def source(self, name: str) -> str:
        return (ROOT / "circuits" / name).read_text(encoding="utf-8")

    def test_deutsch_jozsa_balanced_oracle_is_deterministic(self):
        result = adapter.run(self.source("deutsch_jozsa_balanced.qasm"), "spinq", 1024)

        self.assertEqual(result["counts"], {"11": 1024})

    def test_two_grover_iterations_amplify_111(self):
        result = adapter.run(self.source("grover3.qasm"), "originq", 1024)

        self.assertEqual(result["counts"]["111"], 968)
        self.assertEqual(sum(result["counts"].values()), 1024)
        self.assertEqual(set(result["counts"].values()), {8, 968})

    def test_qft4_exposes_uniform_probabilities_with_nontrivial_phases(self):
        source = self.source("qft4.qasm")
        result = adapter.run(source, "braket", 1024)
        trace = trace_statevector(parse_qasm(source))
        final_states = trace[-2]["states"]

        self.assertEqual(len(result["counts"]), 16)
        self.assertEqual(set(result["counts"].values()), {64})
        self.assertGreaterEqual(
            len({round(state["phase_radians"], 6) for state in final_states}),
            8,
        )

    def test_every_algorithm_transpiles_and_runs_for_all_targets(self):
        for name in ("deutsch_jozsa_balanced.qasm", "grover3.qasm", "qft4.qasm"):
            source = self.source(name)
            for target in adapter.SUPPORTED_TARGETS:
                with self.subTest(name=name, target=target):
                    self.assertTrue(adapter.transpile(source, target).strip())
                    self.assertEqual(sum(adapter.run(source, target, 127)["counts"].values()), 127)


if __name__ == "__main__":
    unittest.main()
