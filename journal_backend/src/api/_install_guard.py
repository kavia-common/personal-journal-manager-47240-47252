#!/usr/bin/env python
"""
Install guard for ensuring critical runtime dependencies exist when the
execution environment ignored requirements installations.

This script attempts a lightweight, non-interactive install of python-jose
(and a small set of essentials) if they are missing at runtime.

Usage:
    python -m src.api._install_guard
"""

import importlib
import subprocess
import sys

def _ensure(pkg: str, spec: str | None = None) -> None:
    """
    Ensure a package can be imported; if not, attempt to install it via pip.

    Args:
        pkg: The module import name to test (e.g., 'jose').
        spec: Optional pip spec to install (e.g., 'python-jose==3.3.0').
    """
    try:
        importlib.import_module(pkg)
        return
    except ModuleNotFoundError:
        pass

    if spec is None:
        spec = pkg

    # Non-interactive, quiet install
    cmd = [sys.executable, "-m", "pip", "install", "--quiet", spec]
    try:
        subprocess.check_call(cmd)
    except Exception as exc:
        # Best-effort only; do not crash the process
        sys.stderr.write(f"[install-guard] Failed to install {spec}: {exc}\n")

def main() -> None:
    # Ensure jose is available for imports in src.api.main
    _ensure("jose", "python-jose==3.3.0")

    # Optionally ensure minimal deps commonly required for import of the app
    # These are best-effort to prevent failing imports in preview environments.
    _ensure("fastapi", "fastapi==0.115.7")
    _ensure("starlette", "starlette==0.45.3")
    _ensure("uvicorn", "uvicorn==0.34.0")

if __name__ == "__main__":
    main()
