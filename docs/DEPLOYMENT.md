# Deployment Prep

Tally is portfolio-demo ready when the backend, mobile app, database, and demo
flow all run from explicit non-secret configuration. Do not deploy from real
`.env` files, and do not commit production credentials.

## Backend Environment

Required variables:

- `ENVIRONMENT=production`
- `DEBUG=false`
- `DATABASE_URL=postgresql+psycopg://USER:PASSWORD@HOST:PORT/DBNAME`
- `JWT_SECRET=<strong random value, at least 48 characters for production>`
- `JWT_ALGORITHM=HS256`
- `CORS_ALLOWED_ORIGINS=https://your-preview.example.com,https://your-web.example.com`
- `ACCESS_TOKEN_EXPIRE_MINUTES=30`
- `AUTH_RATE_LIMIT_REQUESTS=5`
- `AUTH_RATE_LIMIT_WINDOW_SECONDS=60`
- `IMPORT_RATE_LIMIT_REQUESTS=20`
- `IMPORT_RATE_LIMIT_WINDOW_SECONDS=60`
- `TRANSACTION_RATE_LIMIT_REQUESTS=60`
- `TRANSACTION_RATE_LIMIT_WINDOW_SECONDS=60`
- `DASHBOARD_RATE_LIMIT_REQUESTS=60`
- `DASHBOARD_RATE_LIMIT_WINDOW_SECONDS=60`
- `SUBSCRIPTION_RATE_LIMIT_REQUESTS=30`
- `SUBSCRIPTION_RATE_LIMIT_WINDOW_SECONDS=60`
- `ANOMALY_RATE_LIMIT_REQUESTS=30`
- `ANOMALY_RATE_LIMIT_WINDOW_SECONDS=60`
- `REPORT_RATE_LIMIT_REQUESTS=20`
- `REPORT_RATE_LIMIT_WINDOW_SECONDS=60`
- `PRIVACY_RATE_LIMIT_REQUESTS=20`
- `PRIVACY_RATE_LIMIT_WINDOW_SECONDS=60`
- `AI_RATE_LIMIT_REQUESTS=20`
- `AI_RATE_LIMIT_WINDOW_SECONDS=60`
- `MAX_REQUEST_BODY_BYTES=1048576`
- `MAX_UPLOAD_BYTES=5242880`
- `MAX_IMPORT_ROWS=1000`
- `MAX_PASTE_IMPORT_BYTES=100000`

Optional LLM variables:

- `LLM_ENABLED=false`
- `LLM_PROVIDER=fake`
- `LLM_API_KEY=<set only in the deployment secret manager when needed>`
- `LLM_MODEL=gpt-4.1-mini`

Production startup validation rejects SQLite, wildcard CORS, debug mode, empty
CORS origins, and weak/test JWT secrets.

## Backend Deployment

Render/Fly-style start command:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Docker is available through the root `Dockerfile`. It does not copy `.env`
files, runs as a non-root user, exposes port `8000`, and starts
`app.main:app`.

Health checks:

- `GET /health` returns `{"status":"ok"}` and exposes no config.
- `GET /health/db` checks database reachability and should be protected by host
  networking or deployment health-check access if you do not want it public.

## Database

Hosted Postgres options that fit this app:

- Supabase Postgres
- Neon Postgres
- Render or Fly Postgres

Use the provider's connection string as `DATABASE_URL`. Hosted Postgres
providers often require SSL; include the provider-recommended SSL query
parameter if their docs require it.

Before production migrations:

1. Confirm the target `DATABASE_URL` points to the intended database.
2. Take a backup or snapshot.
3. Run the migration from a one-off job or trusted shell:

```powershell
alembic upgrade head
```

Local migration command is the same after setting local `.env` values.
Use a local Postgres database when validating the full Alembic chain. The test
suite uses SQLite metadata setup for speed, but one historical constraint
migration relies on ALTER behavior SQLite does not support.

## CORS And API URLs

Local backend CORS defaults allow Expo dev origins:

- `http://localhost:8081`
- `http://127.0.0.1:8081`
- `http://localhost:8082`
- `http://127.0.0.1:8082`

Production must set `CORS_ALLOWED_ORIGINS` explicitly. Native mobile requests
are not browser-CORS constrained, but Expo web/dev previews and any future web
preview are.

Mobile reads the backend URL from the public, non-secret variable:

```powershell
EXPO_PUBLIC_API_URL=https://your-backend.example.com
```

Do not put secrets in `EXPO_PUBLIC_*` variables.

## Expo And EAS

Use Node.js `20.19.4` or newer for Expo SDK 55 tooling.

Local checks:

```powershell
cd mobile
npm install
npm run typecheck
npm run check:auth
npx expo doctor
```

Local run:

```powershell
cd mobile
$env:EXPO_PUBLIC_API_URL="http://localhost:8000"
npm start
```

EAS profiles are defined in `mobile/eas.json`:

```powershell
cd mobile
eas build --profile preview --platform ios
eas build --profile production --platform ios
```

The app currently uses placeholder bundle IDs:

- iOS: `com.yourname.tally`
- Android: `com.yourname.tally`

Replace them before a real store build.

## App Icon And Splash

No production icon or splash image assets are checked in yet. The Expo config
sets the dark splash background to `#050807` without referencing missing image
files.

Recommended assets:

- App icon: 1024x1024 PNG, dark background, emerald Tally mark.
- Splash image: simple centered Tally mark or logo on `#050807`.
- Android adaptive icon if Android builds remain in scope.

Do not reference asset paths in `app.json` until the files exist.

## Production Checklist

Backend:

- `DATABASE_URL` set in the host secret manager.
- `JWT_SECRET` strong and production-only.
- `ENVIRONMENT=production`.
- `DEBUG=false`.
- `CORS_ALLOWED_ORIGINS` explicit, with no wildcard.
- Migrations run against the intended database.
- Rate limits enabled.
- Request and upload size limits enabled.
- `GET /health` passes.
- Logs do not include secrets, tokens, raw transaction descriptions, full
  imports, or exports.
- No `.env` file committed.

Mobile:

- `EXPO_PUBLIC_API_URL` points to the deployed backend.
- No secrets in `EXPO_PUBLIC_*`.
- SecureStore token persistence works on device.
- API client returns safe errors.
- App icon and splash assets are added before a public build.
- Dark mode screens checked on a physical or simulator iPhone.
- Synthetic demo flow works.
- Empty states work.

Privacy:

- No bank connection.
- No Plaid, FinanceKit, bank APIs, card linking, or account linking.
- CSV upload, manual entry, paste import, and synthetic demo data only.
- Export works.
- Delete app data works.
- Clear demo data works.
- Account deletion works.
- Monthly AI summary fallback works.
- No financial advice language.

## Smoke Test

Backend:

1. Start the API.
2. Call `GET /health`.
3. Register a test user.
4. Load the Full Portfolio Demo.
5. Call dashboard summary, transactions, recurring payments, anomalies,
   monthly reports, privacy summary, and export.
6. Confirm no raw stack traces, secrets, SQL errors, internal paths, tokens, or
   full imported content appear.

Mobile:

1. Set `EXPO_PUBLIC_API_URL` to the local or deployed API.
2. Start Expo.
3. Register or log in.
4. Load synthetic demo data.
5. Navigate Home, Insights, Add/Import, Recurring, Profile/Settings, and
   Monthly Report.
6. Confirm no screen crashes and copy stays neutral.
