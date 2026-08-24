import json
import threading
import unittest
import urllib.error
import urllib.request

import adapter
from loomq.qasm import parse_qasm
from loomq.simulator import simulate_statevector
from loomq.web import create_server


def declared_circuit(qubits: int) -> str:
    return f'''OPENQASM 2.0;
include "qelib1.inc";
qreg q[{qubits}];
creg c[{qubits}];
measure q -> c;
'''


class ResourceBoundaryTests(unittest.TestCase):
    def test_parser_rejects_oversized_register_before_expansion(self):
        with self.assertRaisesRegex(ValueError, "at most 256 quantum bits"):
            parse_qasm(declared_circuit(257))

    def test_statevector_rejects_exponential_allocation(self):
        circuit = parse_qasm(declared_circuit(21))

        with self.assertRaisesRegex(ValueError, "at most 20 qubits"):
            simulate_statevector(circuit)

    def test_sparse_local_execution_matches_published_backend_limits(self):
        for target, qubits in (("spinq", 24), ("originq", 30), ("braket", 25)):
            with self.subTest(target=target, boundary="accepted"):
                result = adapter.run(declared_circuit(qubits), target, 16)
                self.assertEqual(result["counts"], {"0" * qubits: 16})
            with self.subTest(target=target, boundary="rejected"):
                with self.assertRaisesRegex(ValueError, f"at most {qubits} qubits"):
                    adapter.run(declared_circuit(qubits + 1), target, 16)

    def test_sparse_execution_preserves_entanglement_above_dense_limit(self):
        source = declared_circuit(21).replace(
            "measure q -> c;", "h q[0];\ncx q[0],q[20];\nmeasure q -> c;"
        )

        result = adapter.run(source, "originq", 16)

        self.assertEqual(result["counts"], {"0" * 21: 8, "1" + "0" * 19 + "1": 8})

    def test_web_returns_structured_error_for_unsafe_simulation_size(self):
        server = create_server("127.0.0.1", 0)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            request = urllib.request.Request(
                f"http://127.0.0.1:{server.server_port}/api/run",
                data=json.dumps(
                    {"qasm": declared_circuit(31), "target": "originq", "shots": 16}
                ).encode(),
                headers={"Content-Type": "application/json"},
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=3)

            error = raised.exception
            self.assertEqual(error.code, 400)
            payload = json.loads(error.read())
            error.close()
            self.assertEqual(payload["error"]["code"], "invalid_request")
            self.assertIn("at most 30 qubits", payload["error"]["message"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)

    def test_hybrid_rejects_pathological_branch_nesting(self):
        depth = 65
        nested = "if (c[0] == 0) { " * depth + "r1 = 1;" + " }" * depth
        source = f'''OPENQASM 2.0; include "qelib1.inc";
qreg q[1]; creg c[1]; measure q -> c;
classical {{ {nested} }}
'''

        with self.assertRaisesRegex(ValueError, "nesting exceeds 64"):
            adapter.compile_hybrid(source)


if __name__ == "__main__":
    unittest.main()
