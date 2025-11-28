# Journal Backend

FastAPI backend for the Personal Journal application.

Environment variables (configure via the container's .env):
- DATABASE_URL: SQLAlchemy URL for PostgreSQL, e.g. postgresql+psycopg://user:pass@host:port/db
- JWT_SECRET_KEY: Secret key used to sign JWT tokens
- JWT_ALGORITHM: JWT algorithm (default: HS256)
- ACCESS_TOKEN_EXPIRE_MINUTES: Token expiration in minutes (default: 60)
- CORS_ALLOW_ORIGINS: Comma-separated origins for CORS, or * for all
- SEED_KEY: Header key value to authorize /admin/seed endpoint

Local development fallback:
If DATABASE_URL is not provided, a local sqlite file (journal.db) will be used automatically.

OpenAPI:
- Generate updated schema after changes by running the provided script that imports app and writes interfaces/openapi.json.
```python
# from within the container
python -m src.api.generate_openapi
```

Notes:
- Do not hardcode secrets in code; use environment variables.
- This backend is designed to work with a PostgreSQL database container using psycopg and SQLAlchemy 2.x.

Dependency note for JWT:
- The application imports jose via: `from jose import JWTError, jwt`.
- Ensure the package installed is `python-jose` (not `jose`).
- requirements.txt already pins: `python-jose[cryptography]==3.3.0` to enable recommended crypto backends.

If your environment disallows installing extras from requirements (e.g., `[cryptography]` is rejected), install directly:
    pip install "python-jose[cryptography]"==3.3.0

As a last-resort fallback (not preferred), you may install without extras:
    pip install python-jose==3.3.0
Note: Without the `cryptography` extra some algorithms/backends may be slower or unavailable.

Quick import check:
- After installing dependencies, you can validate imports by running:
    python -c "from jose import JWTError, jwt; import uvicorn; print('ok')"
- Or ensure the app imports:
    python -c "import importlib; importlib.import_module('src.api.main'); print('app import ok')"

Runtime install guard (fallback):
- Some preview/CI environments may ignore requirements.txt. To ensure python-jose gets installed, this repo includes an install guard:
    python -m src.api._install_guard
- CI verification helper that runs the guard and validates imports:
    python scripts/verify_jose_and_app_import.py
