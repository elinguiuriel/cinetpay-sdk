from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cinetpay_sdk.harness import run_repository_harness


class RepositoryHarnessTests(unittest.TestCase):
    def test_repository_harness_scenarios_pass(self):
        results = run_repository_harness()
        failures = [result for result in results if not result.passed]
        self.assertFalse(
            failures,
            "Harness failures:\n" + "\n".join(f"{result.name}: {result.message}" for result in failures),
        )


if __name__ == "__main__":
    unittest.main()
