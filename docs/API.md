# API

Tally exposes protected transaction APIs for imported, pasted, demo, and manual
transactions only. It does not connect to real banks or provide financial advice.

## Transaction Categorization

`POST /transactions/categorize`

Protected route. The backend scopes all work to the current authenticated user.

Request body:

```json
{
  "force": false,
  "overwrite_manual": false,
  "transaction_ids": ["optional-transaction-uuid"]
}
```

Rules:

- `force=false` categorizes uncategorized, unknown, imported, `other`, or `needs_review` transactions.
- `force=true` can recategorize automatic/imported/unknown transactions.
- Manual corrections are never overwritten unless `overwrite_manual=true` is explicitly supplied.
- `transaction_ids` is optional and limited to 100 IDs.
- IDs for other users are ignored safely.

Response:

```json
{
  "processed": 42,
  "updated": 38,
  "skipped_manual": 4,
  "needs_review": 6,
  "categories": {
    "food": 10,
    "transportation": 8,
    "subscriptions": 5,
    "income": 2,
    "needs_review": 6
  }
}
```

## Transaction Fields

`GET /transactions` and `GET /transactions/{id}` include categorization metadata:

- `category`
- `category_confidence`
- `category_manually_set`
- `category_source`
- `categorization_reason`
- `categorization_rule`

Allowed categories are `food`, `transportation`, `rent`, `subscriptions`,
`shopping`, `entertainment`, `utilities`, `education`, `health`, `income`,
`transfer`, `fees`, `other`, and `needs_review`.

`PATCH /transactions/{id}/category` accepts only `category` and marks the record
as manual. It does not accept amount, user, merchant, or other mass-assignment
fields.

## Recurring Subscriptions

Recurring detection is deterministic and protected. It analyzes only the current
authenticated user's imported/manual/demo transactions. It does not use an LLM
and does not connect to banks.

`POST /subscriptions/detect`

Runs recurring payment detection for the current user and upserts detected
records by merchant. Re-running detection updates existing records instead of
creating duplicates.

Response:

```json
{
  "subscriptions": [
    {
      "id": "subscription-uuid",
      "merchant_name": "Netflix",
      "average_amount": "549.00",
      "frequency": "monthly",
      "first_seen": "2026-01-01",
      "last_seen": "2026-05-01",
      "next_expected_date": "2026-06-01",
      "confidence_score": 1.0,
      "status": "active",
      "created_at": "2026-05-14T00:00:00",
      "updated_at": "2026-05-14T00:00:00"
    }
  ],
  "detected_count": 1,
  "updated_count": 0
}
```

`GET /subscriptions`

Lists the current user's subscriptions. Optional filters:

- `status`: `active`, `paused`, or `cancelled`
- `frequency`: `weekly`, `biweekly`, `monthly`, or `yearly`
- `search`: merchant search text
- `limit`: 1 to 100, default 50
- `offset`: default 0

Default sort is active first, then soonest `next_expected_date`, then highest
`confidence_score`.

`GET /subscriptions/{id}`

Returns one subscription owned by the current user. Returns 404 if the
subscription does not exist or belongs to another user.

`PATCH /subscriptions/{id}/status`

Accepts only a status update and rejects mass-assignment fields:

```json
{
  "status": "paused"
}
```

Allowed statuses are `active`, `paused`, and `cancelled`. Status changes are
audit logged without raw transaction content.

## Budget Leaks And Anomalies

Budget leak detection is deterministic and protected. It analyzes only the
current authenticated user's transaction records and does not use AI, LLMs,
bank APIs, account linking, or external enrichment. Results are neutral review
prompts based on imported data only.

`POST /anomalies/detect`

Runs detection for a month and upserts anomaly records without creating
duplicates for the same user, month, type, category, and merchant.

Request body:

```json
{
  "month": "2026-05",
  "force_refresh": false
}
```

`month` is optional and must use `YYYY-MM`. If omitted, the backend uses the
latest transaction month for the current user, or the current month when there
are no transactions.

Response:

```json
{
  "month": "2026-05",
  "detected_count": 2,
  "anomalies": [
    {
      "id": "anomaly-uuid",
      "anomaly_type": "CATEGORY_SPIKE",
      "category": "food",
      "merchant_name": null,
      "amount_delta": "3500.00",
      "percentage_change": 77.8,
      "explanation": "Food spending increased by 78% compared with the previous month, based on imported transactions.",
      "severity": "medium",
      "period_start": "2026-05-01",
      "period_end": "2026-05-31",
      "baseline_period_start": "2026-04-01",
      "baseline_period_end": "2026-04-30",
      "transaction_count": 2,
      "created_at": "2026-05-15T00:00:00"
    }
  ]
}
```

Supported anomaly types:

- `CATEGORY_SPIKE`
- `MERCHANT_FREQUENCY_SPIKE`
- `REPEATED_SMALL_PURCHASES`
- `SUBSCRIPTION_PRICE_CHANGE`
- `DUPLICATE_LIKE_TRANSACTIONS`
- `NEEDS_REVIEW_CLUSTER`

Severity values are `low`, `medium`, and `high`.

`GET /anomalies`

Lists the current user's anomalies only. Optional filters:

- `month`: `YYYY-MM`
- `severity`: `low`, `medium`, or `high`
- `anomaly_type`: one supported anomaly type
- `limit`: 1 to 100, default 50
- `offset`: default 0

`GET /anomalies/summary`

Returns counts for the selected month:

```json
{
  "total_anomalies": 3,
  "high_count": 1,
  "medium_count": 1,
  "low_count": 1,
  "top_categories": [{ "name": "food", "count": 1 }],
  "top_merchants": [{ "name": "Grab", "count": 1 }],
  "month": "2026-05"
}
```

Anomaly responses intentionally omit raw transaction descriptions and other
private imported text unless needed for a neutral explanation.

## Dashboard

`GET /dashboard/summary`

Protected route. Returns a deterministic Home Dashboard summary for the current
authenticated user only. It uses imported, pasted, manual, and synthetic data; it
does not connect to banks and does not call AI or LLM services.

Optional query parameters:

- `month`: `YYYY-MM`. If omitted, the backend uses the latest transaction month
  for the current user.

Response shape:

```json
{
  "month": "2026-05",
  "currency": "PHP",
  "total_income": "50000.00",
  "total_expenses": "18420.00",
  "net_flow": "31580.00",
  "transaction_count": 42,
  "top_categories": [
    {
      "category": "food",
      "total_amount": "4200.00",
      "transaction_count": 12,
      "percentage_of_total_expenses": "22.80"
    }
  ],
  "recent_transactions": [],
  "subscription_summary": {
    "active_count": 3,
    "estimated_monthly_total": "1197.00",
    "upcoming_items": []
  },
  "anomaly_summary": {
    "total_count": 2,
    "high_count": 0,
    "medium_count": 1,
    "low_count": 1,
    "latest_items": []
  },
  "needs_review_count": 4,
  "latest_upload": null,
  "has_data": true
}
```

If the user has no transactions, the endpoint returns `has_data=false`, zeroed
totals, and empty arrays. Dashboard responses omit password hashes, raw upload
contents, raw imported file text, and other users' data.

## Monthly Reports

Monthly reports are protected, current-user-scoped summaries over imported,
pasted, manual, or synthetic transactions only. They do not connect to banks.
LLM use is optional and limited to neutral summary wording over aggregated facts.
If LLMs are disabled, unavailable, or return unsafe wording, the backend uses a
deterministic fallback summary.

`POST /reports/monthly/generate`

Request body:

```json
{
  "month": "2026-05",
  "use_ai": true,
  "force_refresh": false
}
```

Behavior:

- `month` must use `YYYY-MM`.
- `force_refresh=false` returns an existing report for that user and month.
- `force_refresh=true` recalculates the persisted report.
- `use_ai=false` always uses deterministic fallback text.
- Raw CSV contents, pasted import text, and full transaction descriptions are not sent to the LLM.
- AI summary text is safety-validated before saving or returning.

Response shape:

```json
{
  "id": "report-uuid",
  "user_id": "user-uuid",
  "month": "2026-05",
  "currency": "PHP",
  "total_income": "50000.00",
  "total_expenses": "18420.00",
  "total_spend": "18420.00",
  "net_flow": "31580.00",
  "transaction_count": 42,
  "top_categories": [],
  "detected_subscriptions": [],
  "anomalies": [],
  "needs_review_count": 4,
  "largest_merchant_total": null,
  "recurring_payment_count": 3,
  "ai_summary": "Based on imported transactions...",
  "generated_status": "complete",
  "generation_source": "deterministic",
  "safety_flags": [],
  "has_data": true,
  "created_at": "2026-05-16T00:00:00",
  "updated_at": "2026-05-16T00:00:00"
}
```

`GET /reports/monthly`

Optional filters:

- `month`: `YYYY-MM`
- `limit`: 1 to 100, default 20
- `offset`: default 0

Returns only the current user's reports.

`GET /reports/monthly/{report_id}`

Returns one report owned by the current user. Returns 404 if the report does not
exist or belongs to another user.
