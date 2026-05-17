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

## Phase 8 Home Dashboard

1. Register or log in.
2. Open Home and confirm the empty state says no imported transactions yet.
3. Tap Try Demo Data or import the sample CSV.
4. Return to Home and confirm the financial pulse dashboard appears.
5. Confirm the screen uses the Stitch design direction:
   - warm cream background
   - dark forest green pulse card
   - soft rounded summary cards
   - upcoming charges
   - top categories with rounded progress bars
   - recent transactions
   - spending insights preview
   - bottom tabs for Home, Insights, Add, Recurring, and Profile
6. Tap View all under recent transactions and confirm Transactions opens.
7. Tap See all under upcoming charges and confirm Recurring opens.
8. Tap the insight card and confirm Budget Leaks / Insights opens.
9. Tap Add and confirm Import opens.
10. Tap Profile and confirm Settings opens.

Backend smoke test:

1. Start the backend.
2. Register or log in a test user.
3. Load demo data.
4. Run categorization, subscription detection, and anomaly detection if needed.
5. Call `GET /dashboard/summary`.
6. Confirm `has_data=true`, spending totals, top categories, recent
   transactions, recurring summary, and anomaly summary are present.
7. Create a second user and confirm their dashboard does not show the first
   user's rows.
8. Confirm unauthenticated requests return 401.
9. Confirm a new user with no transactions gets `has_data=false`.

Narration points:

- The dashboard is deterministic and uses user-owned imported or synthetic data
  only.
- The dashboard does not connect to banks and does not provide financial advice.
- Language stays neutral: financial pulse, detected pattern, may be worth
  reviewing, and based on imported transactions.

## Phase 9 Monthly Report

1. Register or log in.
2. Load synthetic demo data from the mobile app or `POST /demo/load-sample-data`.
3. Run categorization, subscription detection, and anomaly detection if needed.
4. Open Monthly Report from the Home dashboard.
5. Tap Generate Report.
6. Confirm the main report card shows monthly expenses, income, net flow, and
   transaction count.
7. Confirm Monthly Summary uses neutral wording based on imported data only.
8. Confirm Top categories show amounts, percentages, counts, and rounded
   progress bars.
9. Confirm Recurring payments shows active count, estimated monthly total, and
   links to Recurring.
10. Confirm Budget leaks / patterns shows anomaly counts and links to Insights.
11. Confirm Needs review links to Transactions filtered by `needs_review`.
12. Create a fresh user with no transactions and confirm the empty state offers
    Import Transactions and Try Demo Data.

Backend smoke test:

1. Start the backend.
2. Register or log in a test user.
3. Load demo data.
4. Run categorization, subscription detection, and anomaly detection if needed.
5. Call `POST /reports/monthly/generate` with `{"month":"2026-05","use_ai":false}`.
6. Confirm deterministic report fields include total expenses, top categories,
   detected subscriptions, anomalies, and a neutral summary.
7. Call `GET /reports/monthly`.
8. Call `GET /reports/monthly/{id}`.
9. Call `POST /reports/monthly/generate` with `use_ai=true`; if no LLM is
   configured, confirm fallback works.
10. Confirm unauthenticated report requests return 401.
11. Confirm a second user cannot access the first user's report.
12. Confirm invalid month input returns the generic validation error.

Narration points:

- Monthly reports are based on imported, pasted, manual, or synthetic data only.
- Tally does not connect to banks and does not provide financial advice.
- LLMs are optional and limited to neutral monthly summary wording.
- Raw files, pasted text, and full transaction descriptions are not sent to the LLM.
- Unsafe AI output is rejected and replaced with deterministic fallback text.

## Phase 10 Settings Privacy Controls

1. Register or log in.
2. Open Profile / Settings.
3. Confirm the Privacy & Data section says Tally does not connect to your bank.
4. Confirm counts load for transactions, uploads, recurring patterns, budget
   leaks, and monthly reports.
5. Tap Export my Tally data.
6. Confirm the JSON preview appears and includes only Tally app records.
7. Tap Clear demo data.
8. Confirm the modal says this removes sample data and keeps the account.
9. Tap Delete app data.
10. Confirm the button stays disabled until typing `DELETE MY TALLY DATA`.
11. Tap Delete account.
12. Confirm the button stays disabled until typing `DELETE MY ACCOUNT`.

Backend smoke test:

1. Start the backend.
2. Register or log in a test user.
3. Load demo data.
4. Generate subscriptions, anomalies, and a monthly report if needed.
5. Call `GET /settings/privacy/summary`.
6. Confirm counts appear and privacy notes mention no bank connection and no
   financial advice.
7. Call `GET /settings/privacy/export`.
8. Confirm the JSON export returns only current-user data and excludes
   password hashes, tokens, secrets, raw CSV contents, and raw pasted import
   text.
9. Call `POST /settings/privacy/clear-demo-data`.
10. Confirm only records tied to the safe demo marker are cleared.
11. Create non-demo data.
12. Call `POST /settings/privacy/delete-app-data` with a wrong confirmation and
    confirm it fails safely.
13. Call it again with `DELETE MY TALLY DATA` and confirm the app data is
    deleted while the account remains.
14. Create a second user and confirm they cannot access or delete the first
    user's data.
15. Call `POST /settings/privacy/delete-account` with a wrong confirmation and
    confirm it fails safely.
16. Call it again with `DELETE MY ACCOUNT` and confirm the Tally account and
    associated app data are deleted. Existing JWTs are not server-stored, but
    future requests fail because the user no longer exists.

Narration points:

- Tally uses CSV upload, manual entry, paste import, and synthetic demo data
  only.
- Tally does not use Plaid, FinanceKit, bank APIs, card linking, or account
  linking.
- Export and delete controls manage Tally app data, not bank accounts or
  financial accounts.
- Destructive actions require explicit confirmation and use safe, neutral copy.
- Tally does not provide financial advice.
