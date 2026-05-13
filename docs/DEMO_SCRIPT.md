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
