# Demo Script

## Phase 5 Categorization

1. Register or log in.
2. Load synthetic demo data from the mobile app or `POST /demo/load-sample-data`.
3. Open Transactions.
4. Confirm common merchants are categorized automatically:
   - Netflix as subscriptions
   - Grab as transportation
   - Company Payroll as income
   - Meralco as utilities
5. Check confidence badges on transaction rows.
6. Filter by Needs Review to inspect unclear transactions.
7. Edit one transaction category.
8. Run `POST /transactions/categorize`.
9. Confirm the manual category persists.
10. Open the dashboard and confirm category cards and the Needs Review count use
    categorized data.

Narration points:

- Phase 5 uses deterministic rules only, with no AI or LLM calls.
- Confidence is explainable through stored reason and rule fields.
- Tally does not connect to banks and does not give financial advice.
- Users stay in control because categories are editable and manual corrections
  are protected.

## Phase 7 Budget Leaks

1. Register or log in.
2. Load synthetic demo data from the mobile app or `POST /demo/load-sample-data`.
3. Open Budget Leaks.
4. Tap Run detection.
5. Confirm summary cards show total budget leaks, high priority, medium
   priority, and needs-review counts.
6. Confirm anomaly cards appear for examples such as category changes, repeated
   small purchases, merchant frequency changes, duplicate-like rows, or recurring
   charge amount changes.
7. Pull to refresh and confirm the same anomaly set remains stable.
8. Create a fresh user with no transactions, open Budget Leaks, and confirm the
   empty state appears.

Backend smoke test:

1. Start the backend.
2. Register or log in a test user.
3. Load demo data.
4. Run `POST /anomalies/detect`.
5. Call `GET /anomalies`.
6. Call `GET /anomalies/summary`.
7. Confirm unauthenticated anomaly requests return 401.
8. Confirm a second user cannot see the first user's anomalies.

Narration points:

- Budget leak detection uses deterministic rules only, with no AI or LLM calls.
- Results are based only on imported, pasted, manual, or synthetic transactions.
- Tally does not connect to banks and does not provide financial advice.
- Results are review prompts, not instructions.
