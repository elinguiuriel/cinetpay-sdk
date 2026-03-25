from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class RepositoryArchitectureTests(unittest.TestCase):
    def test_required_repository_contract_files_exist(self):
        required_paths = [
            ROOT / "AGENTS.md",
            ROOT / "docs" / "architecture.md",
            ROOT / "docs" / "cinetpay-sandbox-contract.md",
            ROOT / "harness" / "scenarios",
            ROOT / "scripts" / "run_harness.py",
            ROOT / "scripts" / "run_quality.py",
        ]
        for path in required_paths:
            self.assertTrue(path.exists(), f"Missing repository contract artifact: {path}")

    def test_gitignore_covers_generated_artifacts(self):
        gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in [
            "__pycache__/",
            ".pytest_cache/",
            "build/",
            "dist/",
            "*.egg-info/",
        ]:
            self.assertIn(pattern, gitignore)

    def test_sdk_module_import_boundaries(self):
        package_dir = ROOT / "src" / "cinetpay_sdk"
        allowed = {
            "__init__": {"client", "exceptions", "models"},
            "client": {"exceptions", "models", "transport"},
            "exceptions": set(),
            "harness": {"client", "transport"},
            "models": set(),
            "transport": {"exceptions"},
        }

        for module_name, permitted in allowed.items():
            path = package_dir / f"{module_name}.py"
            tree = ast.parse(path.read_text(encoding="utf-8"))
            local_imports = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.level:
                    imported = (node.module or "").split(".")[0]
                    if imported:
                        local_imports.add(imported)
            forbidden = local_imports - permitted
            self.assertFalse(
                forbidden,
                f"{module_name}.py imports forbidden local modules: {sorted(forbidden)}",
            )


if __name__ == "__main__":
    unittest.main()
