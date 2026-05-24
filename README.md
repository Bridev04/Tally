# Tally Backend

Tally is a CSV-first spending intelligence backend. It does not connect to banks,
store card numbers, store bank credentials, or provide financial advice.

Allowed transaction input sources are CSV upload, manual transaction entry, paste
import, and synthetic demo data only. Do not add bank connections, account
aggregation, or financial-account login flows.

## Latest Git Update

- Merged the Phase 14 AI-assisted expense entry work into `main`
- Added `babel-preset-expo` as an explicit mobile dev dependency for stable Expo
  Babel resolution
- Validated the update with mobile typechecking, mobile auth safety checks, and
  the backend pytest suite

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

## Phase 8

- Prototype-based Home Dashboard with the Tally Stitch financial pulse design
- Protected `GET /dashboard/summary` endpoint scoped to the authenticated user
- Deterministic dashboard aggregation over imported, manual, pasted, and synthetic transaction data only
- Monthly totals for income, spending, net flow, transactions, needs review, top categories, recent transactions, recurring charges, and spending insights
- Mobile Home tab with cream background, forest-green pulse card, soft rounded cards, upcoming charges, top categories, recent transactions, insight preview, and five-tab bottom navigation
- Empty, loading, retry, and no-data states that avoid raw backend errors

The dashboard is an informational overview of user-owned data. It does not
connect to banks, use LLMs, or provide financial advice.

## Phase 9

- Monthly Insight Reports persisted per authenticated user and month
- Protected `POST /reports/monthly/generate`, `GET /reports/monthly`, and `GET /reports/monthly/{id}` endpoints
- Deterministic monthly calculations for income, expenses, net flow, top categories, recurring payments, anomalies, and needs-review counts
- Optional LLM wording layer for neutral monthly explanation text only
- Deterministic fallback summary when LLMs are disabled, unavailable, or fail safety validation
- AI output validation before saving or returning summaries
- Mobile Monthly Report screen with totals, neutral summary, top categories, recurring payments, budget leak patterns, needs-review links, and empty/loading/error states

Monthly reports are based on imported, pasted, manual, or synthetic data only.
Raw transaction files, pasted import text, and full transaction descriptions are
not sent to the LLM. Tally still does not connect to banks and does not provide
financial advice.

## Phase 10

- Protected privacy summary, JSON export, demo-data clearing, imported app-data deletion, and account deletion endpoints
- Mobile Settings / Privacy controls with calm copy and confirmation flows for destructive actions
- JSON export scoped to the current user, with passwords, tokens, secrets, raw CSV contents, and raw pasted import text excluded
- Demo-data clearing uses the internal `synthetic-demo-data` upload marker and does not guess when records are not marked as demo data
- Delete app data removes uploads, transactions, recurring detections, budget leaks, and monthly reports while preserving the login account
- Delete account removes the Tally profile and associated app data; existing JWTs are not server-stored, but future requests fail after the user row is removed

Privacy controls are about Tally app data only. Tally does not delete bank
accounts, financial accounts, cards, or linked institutions because it never
connects to them. Destructive actions require exact confirmation phrases.

## Phase 11

- Mobile dark mode polish using the Financial Organicism / Nature-Tech direction
- Centralized mobile design tokens for dark colors, spacing, radii, typography, shadows, and gradients
- Shared mobile UI primitives for screens, cards, buttons, badges, loading/empty/error states, section headers, and confirmation modals
- Dark charcoal app shell with emerald accents, glassy cards, muted secondary text, and a floating bottom navigation
- Polished Home, Import/Add, Transactions, Recurring, Insights, Monthly Report, and Settings / Privacy screens
- Auth screens now use calm onboarding copy: no bank connection required, imported/demo data only, and not financial advice
- Frontend static checks cover the dark visual system, shared UI components, neutral copy, and destructive confirmation phrases

Phase 11 is frontend polish only. Tally still uses CSV upload, paste import,
manual transaction entry, and synthetic demo data only. It does not connect to
banks, use Plaid, use FinanceKit, link cards, link accounts, or provide
financial advice.

## Phase 12

- Scenario-based synthetic demo datasets for Basic, Subscription Creep, Budget
  Leaks, Needs Review, and Full Portfolio demos
- Sample CSVs in `sample_data/` for portfolio walkthroughs and import testing
- Protected demo endpoints for scenario discovery, reset/reload, duplicate-safe
  loading, and optional downstream processing
- Demo records are marked with backend-controlled `source`, `is_demo`, and
  `demo_scenario` fields for reliable clearing and export provenance
- Full Portfolio Demo is the default mobile demo flow and supports dashboard,
  transactions, recurring payments, budget leaks, monthly reports, and privacy
  counts
- Mobile Import includes a polished Try demo data card with scenario selection;
  empty states offer demo CTAs without implying bank connection
- Backend tests cover demo scenarios, ownership boundaries, duplicate handling,
  reset behavior, privacy clearing, and processing hooks

Phase 12 demo data is synthetic only. It never comes from real bank accounts,
Plaid, FinanceKit, bank APIs, cards, account linking, or real user financial
data. Demo data can be reset and reloaded safely without deleting non-demo
transactions.

## Phase 13

- Expo app metadata for Tally name, slug, scheme, version, placeholder bundle
  identifiers, splash background, and EAS build profiles
- Mobile API URL normalization through `EXPO_PUBLIC_API_URL`
- Backend production settings for `ENVIRONMENT`, `DEBUG`, and
  `CORS_ALLOWED_ORIGINS`
- Production startup validation for weak JWT secrets, wildcard CORS, debug mode,
  and SQLite production databases
- Dockerfile and `.dockerignore` for secret-safe backend container builds
- Deployment, database migration, EAS, icon/splash, CORS, and smoke-test docs

Phase 13 does not deploy automatically and does not add secrets. Production
values belong in the deployment host secret manager and mobile build
environment, not in git.

## Phase 14

- Protected AI Entry parse and confirm endpoints for AI-assisted manual
  transaction entry
- Deterministic natural-language parser for one user-provided message at a time,
  with safe clarification questions when required fields are missing
- Structured transaction drafts with amount, date, merchant, description,
  category, payment type, confidence, and `ai_chat_manual` source
- Review-before-save confirm flow; parsing never creates a transaction directly
- Mobile AI Entry screen with chat-style input, assistant replies, editable
  draft review card, save, discard, and view-transaction actions
- Add / Import screen entry point for AI Entry alongside CSV, paste, manual, and
  synthetic demo data flows
- Tests for parsing, clarification, authentication, mass-assignment rejection,
  invalid drafts, rate limits, prompt-injection handling, and mobile static copy

AI Entry is AI-assisted manual entry, not bank sync. It only parses the message
the user types, does not use full transaction history as LLM context, and does
not automatically save expenses. The user must review and confirm before saving.
Tally remains neutral and does not provide financial advice.

## Environment

Copy `.env.example` to `.env` and set real values locally or in your host's
secret manager. Keep `.env` out of git.

Required backend variables:

- `ENVIRONMENT`
- `DEBUG`
- `DATABASE_URL`
- `JWT_SECRET`
- `JWT_ALGORITHM`
- `CORS_ALLOWED_ORIGINS`
- `ACCESS_TOKEN_EXPIRE_MINUTES`
- `AUTH_RATE_LIMIT_REQUESTS`
- `AUTH_RATE_LIMIT_WINDOW_SECONDS`
- `IMPORT_RATE_LIMIT_REQUESTS`
- `IMPORT_RATE_LIMIT_WINDOW_SECONDS`
- `TRANSACTION_RATE_LIMIT_REQUESTS`
- `TRANSACTION_RATE_LIMIT_WINDOW_SECONDS`
- `DASHBOARD_RATE_LIMIT_REQUESTS`
- `DASHBOARD_RATE_LIMIT_WINDOW_SECONDS`
- `DASHBOARD_LOW_CONFIDENCE_THRESHOLD`
- `SUBSCRIPTION_RATE_LIMIT_REQUESTS`
- `SUBSCRIPTION_RATE_LIMIT_WINDOW_SECONDS`
- `ANOMALY_RATE_LIMIT_REQUESTS`
- `ANOMALY_RATE_LIMIT_WINDOW_SECONDS`
- `REPORT_RATE_LIMIT_REQUESTS`
- `REPORT_RATE_LIMIT_WINDOW_SECONDS`
- `PRIVACY_RATE_LIMIT_REQUESTS`
- `PRIVACY_RATE_LIMIT_WINDOW_SECONDS`
- `AI_RATE_LIMIT_REQUESTS`
- `AI_RATE_LIMIT_WINDOW_SECONDS`
- `LLM_ENABLED`
- `LLM_PROVIDER`
- `LLM_API_KEY`
- `LLM_MODEL`
- `MAX_REQUEST_BODY_BYTES`
- `MAX_UPLOAD_BYTES`
- `MAX_IMPORT_ROWS`
- `MAX_PASTE_IMPORT_BYTES`

Optional mobile variable:

- `EXPO_PUBLIC_API_URL`

Use `EXPO_PUBLIC_API_URL=http://localhost:8000` for local development. Use a
deployed backend URL, such as `https://your-backend.example.com`, for preview or
production builds. `EXPO_PUBLIC_*` values are public and must never contain
secrets.

## Local test

```powershell
python -m pip install -e ".[dev]"
pytest
```

## Run API

```powershell
uvicorn app.main:app --reload
```

## Migrations

```powershell
alembic upgrade head
```

Use Postgres when validating the full Alembic chain; SQLite is used by the test
suite for fast isolated tests. Back up production data before running
migrations against a hosted database.

## Run Mobile

```powershell
cd mobile
npm install
npm start
```

## Deployment Prep

See `docs/DEPLOYMENT.md` for Render/Fly-style backend setup, Docker notes,
hosted Postgres migration steps, production CORS examples, EAS build commands,
icon/splash asset requirements, and the production smoke-test checklist.

Quick checks:

```powershell
pytest
cd mobile
npm run typecheck
npm run check:auth
npx expo doctor
```
