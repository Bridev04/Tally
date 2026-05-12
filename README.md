# Tally Backend

Tally is a CSV-first spending intelligence backend. It does not connect to banks,
store card numbers, store bank credentials, or provide financial advice.

## Phase 1

- SQLModel database models
- Alembic initial migration
- Database session dependency
- Pydantic/SQLModel schemas
- Model creation tests

## Phase 1.5

- Database check constraints for statuses, row counts, confidence scores, severity, currency length, and nonnegative report totals
- Cascading user-data deletion for CSV-derived records
- FastAPI health and database health endpoints
- GitHub Actions test workflow

Deleting a user cascades to their uploads, parsed transactions, subscriptions,
anomalies, monthly reports, and audit rows. Deleting a transaction upload cascades
to its parsed transactions.

## Local test

```powershell
python -m pip install -e ".[dev]"
pytest
```

## Run API

```powershell
uvicorn app.main:app --reload
```
