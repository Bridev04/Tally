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

## Mobile

The Expo app consumes backend transaction metadata directly. The Transactions
screen shows category and confidence badges, exposes a Needs Review filter, and
keeps category editing on the backend. The dashboard uses category summaries and
shows a Needs Review count so review work is visible immediately.

The Budget Leaks tab consumes `/anomalies`, `/anomalies/summary`, and
`/anomalies/detect`. It shows severity summary cards and anomaly cards with
neutral explanations. It does not provide recommendations, cancellation prompts,
or financial advice.

## Boundaries

Tally does not use AI or LLMs for categorization, subscription detection, or
budget leak detection in this phase. It does not connect to banks, Plaid,
FinanceKit, account linking, cards, or real financial accounts. Categorization
and anomaly detection are transparent organization aids, not financial advice.
