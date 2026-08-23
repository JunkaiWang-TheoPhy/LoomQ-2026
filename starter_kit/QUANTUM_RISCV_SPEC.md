# LoomQ 32-bit Quantum RISC-V Extension

## Scope

This extension is the executable bonus path for LoomQ. It does not change the
official L3 classical instruction subset or the `compile_hybrid()` contract.
Quantum operations are encoded as real 32-bit instruction words, serialized in
little-endian byte order, decoded by the extended `TinyRISCVEmulator`, and then
executed by the same state-vector engine used by L1.

## Instruction word

Every quantum instruction uses the standard RISC-V `custom-0` major opcode:

```text
31          25 24       20 19       15 14    12 11        7 6         0
+--------------+-----------+-----------+--------+-----------+-----------+
| payload [6:0]| operand 2 | operand 1 | format | operand 0 | 0001011   |
+--------------+-----------+-----------+--------+-----------+-----------+
      7 bits       5 bits      5 bits    3 bits     5 bits      0x0b
```

All qubit and classical-bit operands are unsigned five-bit indices, so this
minimal extension addresses `0..31`. The seven-bit payload is either a gate ID
or an index into the program's immutable floating-point parameter table.

## Formats

| `format` | Meaning | `operand0` | `operand1` | `operand2` | `payload` |
|---:|---|---|---|---|---|
| 0 | one-qubit gate | target qubit | 0 | 0 | gate ID |
| 1 | parameterized one-qubit gate | target qubit | 0 | gate ID | parameter index |
| 2 | two-qubit gate | first qubit | second qubit | 0 | gate ID |
| 3 | parameterized two-qubit gate | first qubit | second qubit | 0 | parameter index (`cu1`) |
| 4 | three-qubit gate | first control | second control | target | gate ID (`ccx`) |
| 5 | measurement | qubit | classical bit | 0 | 0 |

## Gate IDs

| ID | Gate | ID | Gate |
|---:|---|---:|---|
| 0 | `h` | 6 | `rz` |
| 1 | `x` | 7 | `ry` |
| 2 | `s` | 8 | `cx` |
| 3 | `sdg` | 9 | `cu1` |
| 4 | `t` | 10 | `swap` |
| 5 | `tdg` | 11 | `ccx` |

Parameterized gates store the exact finite Python `float` value in an ordered
table. The machine word carries a seven-bit table index, permitting at most 128
distinct values per encoded program. This avoids silently quantizing rotation
angles while keeping every instruction exactly 32 bits.

## Validation

The encoder and decoder reject:

- words whose low seven bits are not `0x0b`;
- mismatched format and gate ID;
- qubit/classical indices outside the declared circuit size;
- repeated qubit operands within one gate;
- truncated little-endian byte streams;
- non-finite or out-of-range parameter tables and indices.

## Executable closed loop

The end-to-end path is:

```text
Circuit / OpenQASM operations
  -> encode_circuit()
  -> tuple of 32-bit custom-0 words + parameter table
  -> EncodedQuantumProgram.to_bytes()
  -> EncodedQuantumProgram.from_bytes()
  -> decode_program()
  -> TinyRISCVEmulator.load_quantum_program()
  -> TinyRISCVEmulator.execute_quantum()
  -> normalized LoomQ counts
```

Run the complete encoding and Bell execution proof with:

```bash
python3 -m unittest tests.test_quantum_riscv -v
```

The Bell case encodes `h`, `cx`, and two measurements into four machine words,
decodes them through the extended official lightweight emulator, and returns
exactly 512 counts each for `00` and `11` at 1024 shots.
