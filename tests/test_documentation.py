from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_DIR = ROOT / "src" / "cinetpay_sdk"


class RepositoryDocumentationTests(unittest.TestCase):
    def test_public_sdk_modules_expose_docstrings(self):
        """Public repository modules should stay mechanically documented."""
        module_names = [
            "__init__",
            "client",
            "exceptions",
            "harness",
            "models",
            "transport",
        ]

        missing = []
        for module_name in module_names:
            path = PACKAGE_DIR / f"{module_name}.py"
            tree = ast.parse(path.read_text(encoding="utf-8"))

            if not ast.get_docstring(tree):
                missing.append(f"{module_name}.py module docstring")

            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name.startswith("_"):
                        continue
                    if not ast.get_docstring(node):
                        missing.append(f"{module_name}.py::{node.name}")

                if isinstance(node, ast.ClassDef):
                    if node.name.startswith("_"):
                        continue
                    if not ast.get_docstring(node):
                        missing.append(f"{module_name}.py::{node.name}")

                    for child in node.body:
                        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            if child.name.startswith("_") and not child.name.startswith("__"):
                                continue
                            if child.name.startswith("__") and child.name not in {"__enter__", "__exit__"}:
                                continue
                            if not ast.get_docstring(child):
                                missing.append(f"{module_name}.py::{node.name}.{child.name}")

        self.assertFalse(missing, "Missing docstrings:\n" + "\n".join(sorted(missing)))


if __name__ == "__main__":
    unittest.main()
