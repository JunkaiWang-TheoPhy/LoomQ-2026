import math
import unittest

from starter_kit.loomq.qasm import Circuit, Gate, Measurement
from starter_kit.loomq.quantum_riscv import (
    CUSTOM_0_OPCODE,
    EncodedQuantumProgram,
    QuantumRISCVError,
    decode_program,
    encode_circuit,
)
from starter_kit.riscv_emulator import TinyRISCVEmulator


class QuantumRISCVEncodingTests(unittest.TestCase):
    def test_all_gates_and_measurement_round_trip_through_machine_words(self):
        circuit = Circuit(
            5,
            5,
            [
                Gate("h", (0,)),
                Gate("x", (1,)),
                Gate("s", (2,)),
                Gate("sdg", (3,)),
                Gate("t", (4,)),
                Gate("tdg", (0,)),
                Gate("rz", (1,), math.pi / 3),
                Gate("ry", (2,), -0.25),
                Gate("cx", (0, 1)),
                Gate("cu1", (1, 2), math.pi / 7),
                Gate("swap", (2, 3)),
                Gate("ccx", (0, 1, 4)),
                Measurement(4, 3),
            ],
        )

        encoded = encode_circuit(circuit)
        restored = decode_program(encoded)
        from_bytes = EncodedQuantumProgram.from_bytes(
            encoded.to_bytes(),
            num_qubits=5,
            num_clbits=5,
            parameters=encoded.parameters,
        )

        self.assertEqual(restored, circuit)
        self.assertEqual(from_bytes, encoded)
        self.assertTrue(all(word & 0x7F == CUSTOM_0_OPCODE for word in encoded.words))

    def test_rejects_non_custom_opcode_and_truncated_machine_code(self):
        with self.assertRaisesRegex(QuantumRISCVError, "custom-0 opcode"):
            decode_program(EncodedQuantumProgram(1, 1, (0x00000013,), ()))

        with self.assertRaisesRegex(QuantumRISCVError, "multiple of four"):
            EncodedQuantumProgram.from_bytes(
                b"\x0b\x00\x00", num_qubits=1, num_clbits=1, parameters=()
            )

    def test_rejects_nonzero_reserved_fields(self):
        malformed_measurement = EncodedQuantumProgram(1, 1, (0xFFF0500B,), ())
        valid_rz = encode_circuit(Circuit(1, 1, [Gate("rz", (0,), 1.0)]))
        malformed_rz = EncodedQuantumProgram(
            1, 1, (valid_rz.words[0] | (1 << 15),), valid_rz.parameters
        )

        with self.assertRaisesRegex(QuantumRISCVError, "reserved"):
            decode_program(malformed_measurement)
        with self.assertRaisesRegex(QuantumRISCVError, "reserved"):
            decode_program(malformed_rz)

    def test_rejects_out_of_range_quantum_operand(self):
        circuit = Circuit(33, 1, [Gate("h", (32,)), Measurement(0, 0)])

        with self.assertRaisesRegex(QuantumRISCVError, "5-bit operand"):
            encode_circuit(circuit)


class QuantumRISCVExecutionTests(unittest.TestCase):
    def test_bell_machine_code_executes_through_extended_emulator(self):
        circuit = Circuit(
            2,
            2,
            [
                Gate("h", (0,)),
                Gate("cx", (0, 1)),
                Measurement(0, 0),
                Measurement(1, 1),
            ],
        )
        program = encode_circuit(circuit)
        emulator = TinyRISCVEmulator()

        emulator.load_quantum_program(program)
        result = emulator.execute_quantum(1024)

        self.assertEqual(result["counts"], {"00": 512, "11": 512})
        self.assertEqual(result["meta"]["machine_words"], 4)
        self.assertEqual(result["meta"]["custom_opcode"], "0x0b")


if __name__ == "__main__":
    unittest.main()
