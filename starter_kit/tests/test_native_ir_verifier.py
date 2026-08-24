import unittest
from pathlib import Path

import adapter
from loomq.emitters import emit
from loomq.native_ir import parse_native_ir, verify_native_ir
from loomq.qasm import parse_qasm


ROOT = Path(__file__).resolve().parents[1]


class NativeIRVerifierTests(unittest.TestCase):
    def test_every_algorithm_round_trips_through_each_native_parser(self):
        for filename in (
            "bell.qasm",
            "ghz3.qasm",
            "deutsch_jozsa_balanced.qasm",
            "grover3.qasm",
            "qft4.qasm",
        ):
            circuit = parse_qasm((ROOT / "circuits" / filename).read_text(encoding="utf-8"))
            for target in adapter.SUPPORTED_TARGETS:
                with self.subTest(filename=filename, target=target):
                    native = emit(circuit, target)
                    self.assertEqual(parse_native_ir(native, target), circuit)
                    verify_native_ir(circuit, native, target)

    def test_semantic_verifier_rejects_a_well_formed_but_changed_gate(self):
        circuit = parse_qasm((ROOT / "circuits" / "bell.qasm").read_text(encoding="utf-8"))
        native = emit(circuit, "originq").replace("H q[0]", "X q[0]")

        with self.assertRaisesRegex(ValueError, "semantic mismatch"):
            verify_native_ir(circuit, native, "originq")

    def test_native_parsers_reject_out_of_range_operands(self):
        malformed = "QINIT 2\nCREG 2\nH q[2]\n"

        with self.assertRaisesRegex(ValueError, "out of range"):
            parse_native_ir(malformed, "originq")

    def test_public_transpile_path_returns_self_verified_ir(self):
        source = (ROOT / "circuits" / "qft4.qasm").read_text(encoding="utf-8")

        for target in adapter.SUPPORTED_TARGETS:
            circuit = parse_qasm(source)
            self.assertEqual(parse_native_ir(adapter.transpile(source, target), target), circuit)


if __name__ == "__main__":
    unittest.main()
