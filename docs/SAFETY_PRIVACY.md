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

## Phase 9 Monthly Reports

Phase 9 monthly reports are deterministic first. The backend computes totals,
top categories, recurring payment summaries, anomaly summaries, and needs-review
counts before any optional LLM call.

Allowed LLM input is aggregated report data only:

- month
- income, expense, net flow, and transaction totals
- top category totals
- active recurring payment summaries
- anomaly summaries
- needs-review counts

Disallowed LLM input:

- raw CSV contents
- pasted import text
- full transaction descriptions
- passwords, tokens, API keys, or secrets
- unrelated profile data

The LLM is optional and may only generate neutral explanation text. If it is
disabled, unavailable, or returns advice-like wording, Tally uses deterministic
fallback copy. AI output is checked for phrases such as `you should`, `you must`,
`cancel`, `stop spending`, `waste`, `invest`, `loan`, `credit card`,
`guaranteed`, and `profit` before saving or returning it.

Monthly report copy must remain neutral, for example:

- `Based on your imported transactions...`
- `This month's spending activity shows...`
- `The largest category was...`
- `Some transactions may be worth reviewing...`
- `This is a neutral summary of imported data, not financial advice.`

## Phase 10 Settings Privacy Controls

Phase 10 privacy controls help users understand, export, clear, and delete
their Tally app data. These controls do not imply bank account deletion,
financial account deletion, automatic bank sync, regulatory-grade compliance, or
financial advice.

Settings copy should stay clear and calm:

- `Tally does not connect to your bank.`
- `Your reports are based only on data you imported.`
- `Export a copy of your Tally data.`
- `Clear demo data without deleting your account.`
- `Delete imported transactions and generated insights.`
- `Deleting your account removes your Tally profile and associated app data.`

Privacy API behavior:

- Summary responses include counts, source flags, and privacy notes only.
- JSON export is scoped to the current user.
- Export excludes passwords, password hashes, tokens, secrets, raw CSV contents,
  and raw pasted import text.
- Demo data is cleared only when safely identifiable by the
  `synthetic-demo-data` upload marker.
- Delete app data requires `DELETE MY TALLY DATA` and preserves the user
  account.
- Delete account requires `DELETE MY ACCOUNT` and removes the Tally profile and
  associated app data.
- Destructive actions use database transactions, ownership checks, safe errors,
  rate limits, and count-only audit logs.

Tally still uses only CSV upload, manual transaction entry, paste import, and
synthetic demo data. It does not use Plaid, FinanceKit, bank APIs, card linking,
or account linking.

## Phase 11 Frontend Polish

Phase 11 is a mobile presentation layer update. It adds a dark visual system,
shared UI components, calmer empty/error/loading states, and consistent
destructive confirmation UI.

Safety expectations remain unchanged:

- No bank connection, Plaid, FinanceKit, bank API, card-linking, or
  account-linking copy.
- No financial advice, recommendations, shame-based language, or fear-based
  prompts.
- Expenses remain visually neutral; red is reserved for destructive actions and
  true error states.
- Amber is reserved for review/watch states.
- Privacy controls continue to explain that export and deletion apply only to
  Tally app data.

## Security Practices

- Secrets are read from centralized settings and are never exposed to the mobile app.
- Protected routes require authentication and current-user scoping.
- Import, auth, transaction, dashboard, subscription, anomaly, report, and privacy routes use rate limiting.
- Request and upload sizes are limited.
- Schemas reject unexpected fields to reduce mass-assignment risk.
- ORM-safe queries are used for database access.
- Errors are generic and avoid stack traces, SQL details, internal paths, or secrets.
- Audit logs record security-relevant events without raw CSV contents, pasted rows,
  full transaction text, passwords, tokens, API keys, or card/bank credentials.
