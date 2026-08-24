import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_example(name: str):
    path = ROOT / "examples" / f"run_{name}.py"
    spec = importlib.util.spec_from_file_location(f"loomq_example_{name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SDKExampleIntegrityTests(unittest.TestCase):
    def test_examples_import_without_optional_vendor_packages(self):
        for name in ("spinq", "originq", "braket"):
            with self.subTest(name=name):
                self.assertIsNotNone(load_example(name))

    def test_missing_sdk_is_an_explicit_failure_not_mock_success(self):
        spinq = load_example("spinq")
        originq = load_example("originq")
        spinq.sq = None
        originq.pq = None

        with self.assertRaisesRegex(RuntimeError, "spinqit"):
            spinq.run_on_spinq_simulator("OPENQASM 2.0;", 16)
        with self.assertRaisesRegex(RuntimeError, "pyqpanda"):
            originq.run_on_originq_simulator("OPENQASM 2.0;", 16)

    def test_examples_contain_no_fabricated_job_or_timestamp(self):
        for path in (ROOT / "examples").glob("run_*.py"):
            source = path.read_text(encoding="utf-8")
            with self.subTest(path=path.name):
                self.assertNotIn("mock-job", source.lower())
                self.assertNotIn("Mock data", source)
                self.assertNotIn("2026-07-06T10:00:00Z", source)

    def test_originq_count_normalization_preserves_binary_strings(self):
        originq = load_example("originq")

        self.assertEqual(originq._normalize_counts({"11": 5}, 2), {"11": 5})
        self.assertEqual(originq._normalize_counts({3: 5}, 2), {"11": 5})
        self.assertEqual(originq._normalize_counts({"3": 5}, 2), {"11": 5})


if __name__ == "__main__":
    unittest.main()
