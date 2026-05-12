# Tally Backend

Tally is a CSV-first spending intelligence backend. It does not connect to banks,
store card numbers, store bank credentials, or provide financial advice.

## Phase 1

- SQLModel database models
- Alembic initial migration
- Database session dependency
- Pydantic/SQLModel schemas
- Model creation tests

## Local test

```powershell
python -m pip install -e ".[dev]"
pytest
```
