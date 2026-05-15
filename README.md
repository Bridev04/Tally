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

## Phase 5

- Deterministic transaction categorization service, with no AI or LLM calls
- Merchant normalization for common payment prefixes, punctuation, and aliases
- Explainable keyword rules for merchant and description matching
- Category confidence scores from 0 to 1
- `needs_review` fallback for unclear low-confidence transactions
- Manual category corrections protected from automatic overwrites
- `POST /transactions/categorize` for authenticated bulk categorization
- Auto-categorization after CSV upload, paste confirm, manual entry without a category, and synthetic demo data
- Mobile confidence badges, Needs Review filtering, and dashboard review count

Tally remains an informational transaction organization app. Categories and
confidence scores are editable aids for understanding imported data; they are
not financial advice, investment advice, credit advice, or loan advice.

## Phase 6

- Deterministic recurring subscription and recurring payment detection, with no AI or LLM calls
- Merchant-based grouping scoped to the authenticated user
- Expense-only recurrence checks for weekly, biweekly, monthly, and yearly cadences
- Confidence scores from occurrence count, amount consistency, interval consistency, and subscription category signals
- Status calculation for active, paused, and cancelled patterns
- `POST /subscriptions/detect`, `GET /subscriptions`, `GET /subscriptions/{id}`, and `PATCH /subscriptions/{id}/status`
- Automatic detection after CSV upload, paste confirm, manual entry, and synthetic demo data
- Mobile Recurring tab with status filters, confidence badges, and a detection CTA

Recurring detection is a neutral pattern-finding feature over imported
transactions. It is not financial advice and does not connect to banks.

## Phase 7

- Deterministic budget leak and spending anomaly detection, with no AI or LLM calls
- Current-user-only analysis over imported, pasted, manual, and synthetic transactions
- Category spike, merchant frequency spike, repeated small purchase, subscription price change, duplicate-like transaction, and needs-review cluster rules
- Idempotent `POST /anomalies/detect` with optional `month` and `force_refresh`
- `GET /anomalies` filters for month, severity, type, and paginated results
- `GET /anomalies/summary` for severity counts and top affected categories/merchants
- Mobile Budget Leaks tab with summary cards, neutral anomaly cards, loading/error states, pull-to-refresh, and Run detection CTA
- Synthetic anomaly demo data in `sample_data/anomalies_detectable.csv`

Budget leaks are review prompts based only on imported or synthetic transaction
data. Tally does not say what users should do financially.

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
- `IMPORT_RATE_LIMIT_REQUESTS`
- `IMPORT_RATE_LIMIT_WINDOW_SECONDS`
- `TRANSACTION_RATE_LIMIT_REQUESTS`
- `TRANSACTION_RATE_LIMIT_WINDOW_SECONDS`
- `SUBSCRIPTION_RATE_LIMIT_REQUESTS`
- `SUBSCRIPTION_RATE_LIMIT_WINDOW_SECONDS`
- `ANOMALY_RATE_LIMIT_REQUESTS`
- `ANOMALY_RATE_LIMIT_WINDOW_SECONDS`
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
