#!/usr/bin/env python
"""
Verification script to check that:
- 'from jose import JWTError, jwt' succeeds
- 'uvicorn' is importable
- 'src.api.main:app' can be imported successfully

This script runs the install guard first to ensure python-jose exists, then performs imports.
Exit code 0 indicates success; non-zero indicates failure.
"""

import sys

# Run install guard to ensure python-jose is present in environments that ignore requirements.
try:
    from src.api._install_guard import main as install_guard_main
    install_guard_main()
except Exception as exc:
    # Guard is best-effort; continue to test imports regardless.
    sys.stderr.write(f"[verify] install guard raised: {exc}\n")

try:
    from jose import JWTError, jwt  # noqa: F401
    import uvicorn  # noqa: F401
    import importlib

    importlib.import_module("src.api.main")
except Exception as exc:
    sys.stderr.write(f"[verify] import failure: {exc}\n")
    sys.exit(1)

print("ok")
sys.exit(0)
