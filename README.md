# Tally Backend

Tally is a CSV-first spending intelligence backend. It does not connect to banks,
store card numbers, store bank credentials, or provide financial advice.

Allowed transaction input sources are CSV upload, manual transaction entry, paste
import, and synthetic demo data only. Do not add bank connections, account
aggregation, or financial-account login flows.

## Phase 1

- SQLModel database models
- Alembic initial migration
- Database session dependency
- Pydantic/SQLModel schemas
- Model creation tests

## Phase 1.5

- Database check constraints for statuses, row counts, confidence scores, severity, currency length, and nonnegative report totals
- Cascading user-data deletion for CSV-derived records
- FastAPI health and database health endpoints
- GitHub Actions test workflow

Deleting a user cascades to their uploads, parsed transactions, subscriptions,
anomalies, monthly reports, and audit rows. Deleting a transaction upload cascades
to its parsed transactions.

## Phase 2

- Email/password registration and login with bcrypt password hashing
- JWT access token creation and validation from centralized settings
- `POST /auth/register`, `POST /auth/login`, and `GET /auth/me`
- `get_current_user` dependency for protected backend routes
- Safe auth errors, generic validation errors, and request body size limits
- Audit log entries for register and login events
- Basic in-memory auth endpoint rate limiting
- Expo Router mobile auth shell with SecureStore token persistence
- Hardened auth schemas that reject unexpected fields
- Explicit no-bank-import guardrails for future transaction ingestion

The current rate limiter is process-local, which is fine for this phase and local
development. Before running multiple backend instances, replace it with a Redis
or managed edge rate limiter so limits apply across all workers.

JWTs are stored only with Expo SecureStore on mobile. Do not move them to
AsyncStorage or frontend logs.

## Environment

Copy `.env.example` to `.env` and set real values locally or in your host's
secret manager. Keep `.env` out of git.

Required backend variables:

- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `AUTH_RATE_LIMIT_REQUESTS`
- `AUTH_RATE_LIMIT_WINDOW_SECONDS`
- `MAX_REQUEST_BODY_BYTES`
- `MAX_UPLOAD_BYTES`

Optional mobile variable:

- `EXPO_PUBLIC_API_URL`

## Local test

```powershell
python -m pip install -e ".[dev]"
pytest
```

## Run API

```powershell
uvicorn app.main:app --reload
```

## Run Mobile

```powershell
cd mobile
npm install
npm start
```
