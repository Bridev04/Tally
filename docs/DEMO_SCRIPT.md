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

## Phase 11 Dark Mobile Polish

1. Open Tally.
2. Register or log in.
3. Confirm the auth screens use the dark premium Tally style and say no bank
   connection is required.
4. Load demo data from Add / Import.
5. View Home and confirm the financial pulse card, insight card, summary cards,
   upcoming charges, top categories, recent transactions, and budget leak
   preview render cleanly in dark mode.
6. Open Add and confirm CSV upload, paste import, manual entry, and demo data
   options are easy to scan.
7. Open Transactions and confirm search, filters, category badges, confidence
   badges, and transaction detail/category editing remain functional.
8. Open Recurring and confirm detected recurring payments use calm, neutral
   copy based on imported transactions.
9. Open Insights and confirm anomaly cards, severity badges, and empty/loading
   states avoid advice-like language.
10. Open Monthly Report and confirm the summary is readable and includes
    `Generated from imported data only. Not financial advice.`
11. Open Profile / Settings and confirm export, clear demo data, delete app
    data, and delete account controls are visible.
12. Confirm delete app data requires `DELETE MY TALLY DATA` and delete account
    requires `DELETE MY ACCOUNT`.

Narration points:

- Phase 11 adds a cohesive dark mobile design system; it does not change data
  sources or backend security boundaries.
- Tally remains CSV/manual/paste/demo-data only.
- Tally does not use Plaid, FinanceKit, bank APIs, account linking, or card
  linking.
- Tally is not financial advice; language stays neutral and based on imported
  or synthetic demo data.

## Phase 12 Portfolio Demo Flow

1. Open Tally.
2. Register or log in.
3. Open Add / Import.
4. Confirm the Try demo data card says synthetic transactions are used.
5. Choose Full Portfolio Demo.
6. Tap Load demo data.
7. Confirm the success message says demo data is loaded.
8. View Home Dashboard and show income, spending, net flow, recent
   transactions, recurring previews, and budget leak previews.
9. Open Transactions and show search, filters, categories, needs-review rows,
   and category editing.
10. Open Recurring and show detected Netflix, Spotify, Canva, YouTube Premium,
    Apple iCloud, or Google One patterns.
11. Open Insights and show category, merchant frequency, repeated small
    purchase, duplicate-like, and needs-review patterns.
12. Open Monthly Report and show the neutral deterministic summary for the demo
    month.
13. Open Settings / Privacy and show stored-data counts, export, clear demo
    data, delete app data, and delete account controls.
14. Tap Clear demo data and confirm non-demo transactions would be preserved.

Backend smoke test:

1. Start the backend.
2. Register or log in a test user.
3. Call `GET /demo/scenarios`.
4. Call `POST /demo/load-sample-data` with `scenario=full_portfolio`,
   `reset_existing_demo=true`, and `run_processing=true`.
5. Confirm transactions, subscriptions, anomalies, and one monthly report are
   created for that user.
6. Call dashboard, transactions, subscriptions, anomalies, monthly report, and
   privacy summary routes.
7. Call `POST /settings/privacy/clear-demo-data`.
8. Confirm demo rows are removed and any non-demo rows are preserved.
9. Create a second user and confirm they cannot access the first user's data.
10. Send an invalid scenario and confirm the response is a safe validation
    error.

Narration points:

- Demo data is synthetic and labeled for portfolio preview.
- Tally uses imported or synthetic data only.
- Tally does not connect to banks or use Plaid, FinanceKit, bank APIs, card
  linking, or account linking.
- Tally is not financial advice.

## Phase 13 Deployment Readiness

1. Confirm `.env.example` and `mobile/.env.example` contain placeholders only.
2. Confirm no real `.env` files are tracked.
3. Open `mobile/app.json` and confirm Tally name, slug, scheme, placeholder
   bundle IDs, splash background, and version are present.
4. Open `mobile/eas.json` and confirm development, preview, and production
   build profiles exist.
5. Confirm `EXPO_PUBLIC_API_URL` is documented for local and production builds.
6. Confirm backend config exposes `ENVIRONMENT`, `DEBUG`,
   `CORS_ALLOWED_ORIGINS`, `DATABASE_URL`, JWT settings, rate limits, upload
   limits, and optional LLM settings.
7. Confirm production config rejects wildcard CORS, weak JWT secrets, debug
   mode, and SQLite.
8. Run backend tests.
9. Run mobile typecheck and auth safety check.
10. Run `npx expo doctor` when the local Expo environment is available.

Portfolio smoke test:

1. Start the backend with local env values.
2. Call `GET /health`.
3. Register a test user.
4. Load Full Portfolio Demo synthetic data.
5. Visit Home, Transactions, Recurring, Insights, Monthly Report, and
   Profile/Settings.
6. Confirm the app remains CSV/manual/paste/synthetic only and all copy stays
   neutral.

## Phase 14 AI Entry

1. Open Add / Import.
2. Tap AI Entry.
3. Type `I bought chicken from Jollibee for 200 pesos.`
4. Show the parsed draft with merchant Jollibee, amount -200 PHP, food category,
   and today's date.
5. Confirm that the draft is not saved yet.
6. Tap Save transaction.
7. Open Transactions.
8. Show the new Jollibee transaction under the food category.
9. Explain: `This is AI-assisted manual entry, not bank sync.`
10. Try `I bought coffee.`
11. Confirm Tally asks for the missing amount and does not save anything.

Narration points:

- AI Entry only parses the message the user types.
- The user reviews and confirms before saving.
- Tally does not connect to banks, Plaid, FinanceKit, bank APIs, cards, or
  accounts.
- Tally does not provide financial advice.
