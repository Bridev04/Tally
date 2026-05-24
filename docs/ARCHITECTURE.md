# Architecture

Tally is split into a FastAPI backend and an Expo React Native mobile app.

## Backend

The backend uses service layers for transaction import, manual transaction
creation, auditing, and deterministic categorization. API handlers validate
requests, enforce authentication and rate limits, and delegate business logic to
services.

Phase 5 adds `TransactionCategorizerService` in
`app/services/transaction_categorizer.py`.

Responsibilities:

- Normalize merchant names consistently.
- Match deterministic merchant and description keyword rules.
- Assign explainable confidence scores.
- Mark unclear transactions as `needs_review`.
- Preserve manual corrections unless explicit overwrite is requested.
- Write audit logs for automatic category changes.

The service is used by CSV upload, paste confirm, manual entry without a
category, demo data loading, and `POST /transactions/categorize`.

Phase 6 adds deterministic recurring payment detection in
`app/services/subscription_detection.py`. It groups expense transactions by
normalized merchant, scores cadence and amount consistency, and stores
subscription-like patterns for the authenticated user.

Phase 7 adds deterministic budget leak and anomaly detection in
`app/services/anomalies.py`.

Responsibilities:

- Compare current month spending with the previous month.
- Detect category spikes, merchant frequency spikes, repeated small purchases,
  subscription price changes, duplicate-like transactions, and needs-review
  clusters.
- Upsert anomalies for the selected month so repeated detection is idempotent.
- Store period metadata for filtering and summary counts.
- Avoid storing or returning raw transaction descriptions in anomaly payloads.

All Phase 7 API routes use `get_current_user`, per-user rate limiting, schema
validation, ORM-safe queries, generic validation errors, and audit logs for
manual detection runs.

Phase 8 adds `DashboardService` in `app/services/dashboard.py` and
`GET /dashboard/summary`.

Responsibilities:

- Select the requested month or the latest transaction month for the user.
- Summarize income, expenses, net flow, recent transactions, top categories,
  active recurring payments, anomaly counts, and needs-review rows.
- Return a beautiful empty state contract when the user has no data.
- Scope every query to the authenticated user's ID.
- Avoid returning password hashes, raw upload contents, raw imported text, or
  internal errors.

Phase 9 adds `MonthlyReportService` in `app/services/monthly_reports.py`,
`/reports/monthly` API routes, and a small LLM abstraction in
`app/services/llm`.

Responsibilities:

- Validate `YYYY-MM` report months and scope every query to the authenticated user.
- Calculate income, expenses, net flow, top expense categories, active recurring
  payments, anomaly summaries, needs-review count, and largest merchant total
  deterministically before any AI step.
- Persist aggregate report data in `MonthlyInsightReport`.
- Send only aggregated facts to the optional LLM wording layer.
- Validate LLM output for advice-like language before saving or returning it.
- Fall back to deterministic neutral text when LLMs are disabled, unavailable,
  or fail safety checks.

Phase 10 adds `PrivacyService` in `app/services/privacy.py` and
`/settings/privacy` API routes.

Responsibilities:

- Summarize stored data counts and data sources for the authenticated user.
- Export normalized app records as JSON for the current user only.
- Exclude password hashes, tokens, secrets, raw CSV contents, and raw pasted
  import text from exports.
- Clear demo data only when records are tied to the internal
  `synthetic-demo-data` upload marker.
- Delete imported app data while preserving the user account and audit history.
- Delete the Tally account and associated app data when the exact confirmation
  phrase is supplied.
- Use per-user rate limiting, schema validation, ORM-safe queries, safe errors,
  and count-only audit metadata.

Phase 12 adds scenario-based demo support in `app/services/demo_data.py` and
the protected `/demo/scenarios`, `/demo/load-sample-data`, and `/demo/reset`
routes.

Responsibilities:

- Load synthetic-only scenario data for the current user.
- Support Basic, Subscription Creep, Budget Leaks, Needs Review, and Full
  Portfolio demos.
- Mark demo uploads and transactions with backend-controlled `source`,
  `is_demo`, and `demo_scenario` fields.
- Avoid duplicate demo inserts unless the caller explicitly resets existing demo
  rows first.
- Reset or clear only current-user demo rows while preserving non-demo data.
- Optionally run categorization, recurring detection, anomaly detection, and a
  deterministic monthly report after loading.

Phase 14 adds AI-assisted manual entry through
`app/services/ai_expense_parser.py` and `/ai/expense` API routes.

Responsibilities:

- Parse one user-provided transaction message into a structured draft.
- Use deterministic parsing for common expense and income messages, peso
  formats, relative dates, known merchants, categories, and payment-type hints.
- Ask one concise clarification question when required fields are missing.
- Never save from the parse endpoint; only the confirm endpoint creates a
  transaction after the user reviews the draft.
- Store confirmed transactions with backend-controlled `source=ai_chat_manual`.
- Scope confirmation to the authenticated user, reject mass assignment, use
  schema validation, apply rate limiting, and avoid logging full chat messages.

## Mobile

The Expo app consumes backend transaction metadata directly. The Transactions
screen shows category and confidence badges, exposes a Needs Review filter, and
keeps category editing on the backend. The Home Dashboard consumes
`/dashboard/summary` and follows the Tally Stitch design system: warm cream
background, forest-green pulse card, soft rounded cards, upcoming charges, top
categories, recent transactions, and neutral spending insight previews.

The Budget Leaks tab consumes `/anomalies`, `/anomalies/summary`, and
`/anomalies/detect`. It shows severity summary cards and anomaly cards with
neutral explanations. It does not provide recommendations, cancellation prompts,
or financial advice.

The Monthly Report screen consumes `/reports/monthly` and
`/reports/monthly/generate`. It shows a neutral month-level report, top category
progress bars, recurring payment previews, budget leak patterns, needs-review
links, and empty/loading/error states in the same warm Tally design language.

The Settings/Profile screen consumes `/settings/privacy/summary`,
`/settings/privacy/export`, `/settings/privacy/clear-demo-data`,
`/settings/privacy/delete-app-data`, and `/settings/privacy/delete-account`.
It explains that Tally does not connect to banks, shows stored-data counts,
offers a JSON export preview, and requires confirmation modals for destructive
actions. Account deletion clears SecureStore through the existing logout flow and
returns the user to auth navigation.

Phase 11 adds a mobile dark-mode visual system in `mobile/src/theme.ts` and
shared primitives under `mobile/src/components/ui`. The theme centralizes
charcoal backgrounds, emerald accents, elevated card surfaces, spacing, radii,
typography, shadows, and gradient references. Screens use these primitives for
consistent safe-area padding, bottom-navigation clearance, card treatment,
buttons, badges, loading states, empty states, error states, and destructive
confirmation UX.

The polished mobile screens keep the same Expo Router paths and backend API
calls. Phase 11 changes presentation and copy only; it does not introduce bank
connections, Plaid, FinanceKit, account linking, card linking, or advice-like
recommendations.

Phase 12 adds demo support to the mobile Import screen and empty states. The
default flow loads the Full Portfolio Demo, while a compact selector exposes the
other scenarios. Empty dashboard, transaction, recurring, insight, and report
states point users to import transactions or load synthetic demo data without
implying bank access.

Phase 14 adds `mobile/app/(app)/ai-entry.tsx`. The screen uses the existing
dark visual system and shows a chat-style input, assistant reply bubbles, and an
editable transaction draft card. Save is disabled while loading and only calls
`/ai/expense/confirm` after a draft exists. The Add / Import screen links to AI
Entry without removing CSV upload, paste import, manual entry, or demo data.

## Deployment Configuration

Phase 13 keeps deployment configuration explicit and centralized. Backend
settings live in `app/core/config.py` and include environment, debug mode,
database URL, JWT settings, CORS origins, rate limits, request/upload limits,
and optional LLM settings. `app/main.py` reads CORS from those settings instead
of hardcoding deployment behavior.

In production, settings validation rejects SQLite databases, wildcard CORS,
debug mode, empty CORS origins, and weak or test JWT secrets. Local development
keeps the default Expo dev origins and local API URL fallback.

The mobile app reads only public runtime values, currently
`EXPO_PUBLIC_API_URL`, and normalizes the base URL before API calls. Auth tokens
remain in Expo SecureStore and are not logged.

Deployment notes, migration commands, EAS build profiles, icon/splash asset
requirements, and smoke-test steps live in `docs/DEPLOYMENT.md`.

## Boundaries

Tally does not use AI or LLMs for categorization, subscription detection, or
budget leak detection. Phase 9 may use an LLM only for neutral explanation text
after deterministic monthly aggregates are computed. Phase 14 AI Entry parses
only the user's single message into a draft and requires confirmation before
saving. It does not connect to banks, Plaid, FinanceKit, account linking, cards,
or real financial accounts. Categorization, anomaly detection, monthly reports,
and AI Entry are transparent organization aids, not financial advice.
