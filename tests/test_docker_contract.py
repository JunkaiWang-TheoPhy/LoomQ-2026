from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
DOCKERFILE = ROOT / "starter_kit" / "Dockerfile"


class DockerContractTests(unittest.TestCase):
    def test_base_suite_matches_the_installed_curl_abi(self):
        """Catch a floating slim tag moving past the requested Debian package."""
        dockerfile = DOCKERFILE.read_text(encoding="utf-8")
        base_image = re.search(r"^FROM\s+(\S+)", dockerfile, re.MULTILINE).group(1)
        packages = set(
            re.findall(r"^\s{4}([a-z0-9.+-]+)\s*\\?$", dockerfile, re.MULTILINE)
        )

        compatible_suite = {
            "libcurl4": "bookworm",
            "libcurl4t64": "trixie",
        }
        curl_packages = packages.intersection(compatible_suite)
        self.assertEqual(curl_packages, {"libcurl4"})
        self.assertTrue(
            base_image.endswith(f"-slim-{compatible_suite['libcurl4']}"),
            f"{base_image!r} may resolve to a Debian suite without libcurl4",
        )


if __name__ == "__main__":
    unittest.main()
