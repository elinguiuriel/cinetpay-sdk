from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run_step(label: str, command: list[str]) -> None:
    print(f"[quality] {label}")
    completed = subprocess.run(command, cwd=ROOT)
    if completed.returncode != 0:
        raise SystemExit(completed.returncode)


def main() -> int:
    run_step("compileall", [sys.executable, "-m", "compileall", "src", "tests", "scripts"])
    run_step("unit-tests", [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"])
    run_step("harness", [sys.executable, "scripts/run_harness.py"])
    print("[quality] ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
