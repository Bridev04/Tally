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
