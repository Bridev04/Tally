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

## Mobile

The Expo app consumes backend transaction metadata directly. The Transactions
screen shows category and confidence badges, exposes a Needs Review filter, and
keeps category editing on the backend. The dashboard uses category summaries and
shows a Needs Review count so review work is visible immediately.

## Boundaries

Tally does not use AI or LLMs for Phase 5. It does not connect to banks, Plaid,
FinanceKit, account linking, cards, or real financial accounts. Categorization
is a transparent organization aid, not financial advice.
