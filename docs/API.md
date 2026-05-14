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
