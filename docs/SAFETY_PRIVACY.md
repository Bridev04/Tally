# Safety And Privacy

Tally is not a financial advisor. It does not give investment, loan, credit, tax,
or financial advice. It helps users understand imported transaction data through
categorization, subscription detection, anomaly detection, and neutral spending
insights.

## Data Sources

Allowed sources:

- CSV upload
- Manual transaction entry
- Paste import
- Synthetic demo data

Disallowed sources:

- Real bank connections
- Plaid
- FinanceKit
- Bank APIs
- Card linking
- Account linking

## Phase 5 Categorization

Phase 5 categorization is deterministic and explainable. It does not use AI,
LLMs, embeddings, or external enrichment APIs.

The categorizer stores:

- `category`
- `category_confidence`
- `category_source`
- `categorization_reason`
- `categorization_rule`

Low-confidence or unclear transactions are marked `needs_review`. Users can edit
categories, and those manual corrections are protected from future automatic
categorization unless an authenticated request explicitly sets
`overwrite_manual=true`.

## Phase 6 Recurring Detection

Phase 6 recurring payment detection is deterministic and explainable. It does
not use AI, LLMs, embeddings, bank enrichment, or external transaction APIs.

The detector only analyzes transactions that belong to the logged-in user. It
groups expense transactions by normalized merchant, ignores income and transfers,
checks amount consistency and date intervals, and uses existing subscription
category signals as confidence inputs.

Detected records are neutral spending patterns. Tally may show language such as
`Detected recurring pattern` or `Expected again around`, but it must not tell the
user to cancel, keep, invest, borrow, repay, or make any other financial
decision.

## Phase 7 Budget Leaks

Phase 7 budget leak and anomaly detection is deterministic and explainable. It
does not use AI, LLMs, embeddings, bank enrichment, or external transaction APIs.

The detector only analyzes transactions owned by the logged-in user. It compares
current-month expenses with the previous month, checks merchant frequency,
repeated small purchases, subscription price changes, duplicate-like rows, and
clusters of low-confidence or `needs_review` categorization.

Budget leaks are neutral observations based on imported or synthetic data only.
Acceptable language includes:

- `This category increased compared with your previous period.`
- `This merchant appeared more frequently than usual.`
- `This recurring charge changed amount.`
- `This may be worth reviewing.`
- `Detected from imported data only.`

Tally must not use wording such as `cancel this`, `stop spending`, `bad habit`,
`waste`, or tell users what they should do financially.

Anomaly payloads omit raw transaction descriptions. Audit logs record detection
counts, month, and refresh status, not private imported transaction contents.

## Phase 8 Home Dashboard

Phase 8 dashboard summaries are deterministic and protected. They do not use AI,
LLMs, bank enrichment, external transaction APIs, Plaid, FinanceKit, card
linking, or account linking.

The dashboard only summarizes records owned by the logged-in user. It returns
monthly totals, top categories, recent transaction display fields, active
recurring payment previews, and anomaly counts. It does not return password
hashes, raw upload contents, raw CSV or paste text, internal paths, SQL errors,
or stack traces.

Dashboard copy must remain neutral. Acceptable language includes:

- `Here’s your financial pulse.`
- `Based on imported transactions.`
- `Detected pattern.`
- `May be worth reviewing.`
- `Needs review.`

The dashboard must not tell users to cancel, invest, borrow, repay, or make a
financial decision.

## Security Practices

- Secrets are read from centralized settings and are never exposed to the mobile app.
- Protected routes require authentication and current-user scoping.
- Import, auth, transaction, dashboard, subscription, and anomaly routes use rate limiting.
- Request and upload sizes are limited.
- Schemas reject unexpected fields to reduce mass-assignment risk.
- ORM-safe queries are used for database access.
- Errors are generic and avoid stack traces, SQL details, internal paths, or secrets.
- Audit logs record security-relevant events without raw CSV contents, pasted rows,
  full transaction text, passwords, tokens, API keys, or card/bank credentials.
