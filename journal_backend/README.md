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
