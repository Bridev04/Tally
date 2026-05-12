from typing import Annotated

from fastapi import Depends, FastAPI
from sqlalchemy import text
from sqlmodel import Session

from app.db.session import get_session


app = FastAPI(
    title="Tally API",
    version="0.1.0",
    description="CSV-first spending intelligence backend. Tally does not provide financial advice.",
)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def database_health_check(
    session: Annotated[Session, Depends(get_session)],
) -> dict[str, str]:
    session.exec(text("SELECT 1")).one()
    return {"status": "ok", "database": "reachable"}
