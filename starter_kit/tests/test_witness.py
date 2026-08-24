import copy
import hashlib
import json
import unittest

from loomq.witness import build_causal_audit, verify_causal_audit


BELL = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
"""

MUTATED_BELL = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
x q[1];
measure q -> c;
"""

HYBRID_BRANCH = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q -> c;
classical {
  if (c[1] == 1) { r3 = 9; } else { r3 = 4; }
}
"""

HYBRID_MISMATCH = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
x q[1];
measure q -> c;
classical {
  if (c[1] == 1) { r3 = 9; } else { r3 = 4; }
}
"""

REWRITE_REFERENCE = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
h q[0];
measure q[0] -> c[0];
"""

REWRITE_HYBRID = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[1];
creg c[1];
h q[0];
h q[0];
measure q[0] -> c[0];
classical {
  r1 = 0;
}
"""

STRUCTURAL_MISMATCH = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
creg c[2];
h q[0];
cx q[0],q[1];
measure q[0] -> c[1];
measure q[1] -> c[0];
"""


class WitnessTests(unittest.TestCase):
    def _stage(self, audit, stage):
        return next(item for item in audit["witness_chain"] if item["stage"] == stage)

    def test_build_causal_audit_tracks_gate_assertion_and_branch_witnesses(self):
        audit = build_causal_audit(
            BELL,
            MUTATED_BELL,
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999}],
            HYBRID_BRANCH,
            [1, 1],
            "spinq",
        )

        self.assertEqual(audit["schema_version"], "loomq-witness-chain-v1")
        mutation = self._stage(audit, "counterfactual")
        assertions = self._stage(audit, "assertions")
        hybrid = self._stage(audit, "hybrid")

        self.assertEqual(mutation["counterfactual"]["reference_witness_id"], "g2")
        self.assertEqual(
            assertions["assertions"][0]["measurement_witness_ids"],
            ["m1", "m2"],
        )
        self.assertEqual(
            hybrid["hybrid"]["branch_events"][0]["measurement_witness_ids"],
            ["m2"],
        )
        self.assertTrue(all("witness_ids" in item for item in audit["witness_chain"]))

    def test_prooftrace_rewrite_aliases_use_source_witness_ids(self):
        audit = build_causal_audit(
            REWRITE_REFERENCE,
            REWRITE_REFERENCE,
            [{"kind": "support", "states": ["0", "1"], "minimum_probability": 1.0}],
            REWRITE_HYBRID,
            [0],
            "originq",
        )

        prooftrace = self._stage(audit, "prooftrace")
        self.assertEqual(
            prooftrace["rewrite_aliases"][0]["source_witness_ids"],
            ["g1", "g2"],
        )

    def test_build_causal_audit_is_deterministic(self):
        left = build_causal_audit(
            BELL,
            MUTATED_BELL,
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999}],
            HYBRID_BRANCH,
            [1, 1],
            "spinq",
        )
        right = build_causal_audit(
            BELL,
            MUTATED_BELL,
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999}],
            HYBRID_BRANCH,
            [1, 1],
            "spinq",
        )

        self.assertEqual(left, right)

    def test_verify_causal_audit_rejects_tampering(self):
        audit = build_causal_audit(
            BELL,
            MUTATED_BELL,
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999}],
            HYBRID_BRANCH,
            [1, 1],
            "spinq",
        )
        tampered = copy.deepcopy(audit)
        tampered["witness_chain"][1]["counterfactual"]["reference_witness_id"] = "g1"

        report = verify_causal_audit(tampered)

        self.assertFalse(report["valid"])
        self.assertIn("mismatch", report["reason"])

        payload = {
            key: value
            for key, value in tampered.items()
            if key not in {"integrity", "verification"}
        }
        encoded = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode("utf-8")
        tampered["integrity"]["audit_sha256"] = hashlib.sha256(encoded).hexdigest()

        rebuilt_report = verify_causal_audit(tampered)

        self.assertFalse(rebuilt_report["valid"])
        self.assertEqual(rebuilt_report["reason"], "recomputed audit mismatch")

    def test_verify_accepts_web_response_with_separate_verification_report(self):
        audit = build_causal_audit(
            BELL,
            MUTATED_BELL,
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999}],
            HYBRID_BRANCH,
            [1, 1],
            "spinq",
        )
        audit["verification"] = verify_causal_audit(audit)

        self.assertTrue(verify_causal_audit(audit)["valid"])

    def test_structural_mismatch_does_not_fabricate_divergence_witness(self):
        audit = build_causal_audit(
            BELL,
            STRUCTURAL_MISMATCH,
            [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999}],
            HYBRID_BRANCH,
            [1, 1],
            "spinq",
        )

        mutation = self._stage(audit, "counterfactual")
        self.assertEqual(mutation["counterfactual"]["scope"], "structural-mismatch")
        self.assertIsNone(mutation["counterfactual"]["reference_witness_id"])

    def test_hybrid_quantum_mismatch_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "hybrid quantum circuit must exactly match"):
            build_causal_audit(
                BELL,
                MUTATED_BELL,
                [{"kind": "support", "states": ["00", "11"], "minimum_probability": 0.999}],
                HYBRID_MISMATCH,
                [1, 1],
                "spinq",
            )


if __name__ == "__main__":
    unittest.main()
