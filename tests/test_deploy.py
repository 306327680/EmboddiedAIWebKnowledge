import subprocess
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class DeployScriptTests(unittest.TestCase):
    def test_unknown_mode_fails_before_build_or_deploy(self):
        result = subprocess.run(
            ["bash", "deploy.sh", "--unknown"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)
        self.assertNotIn("Building site", result.stdout)


if __name__ == "__main__":
    unittest.main()
