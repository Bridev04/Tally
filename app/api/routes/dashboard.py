from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip
from app.db.session import get_session
from app.models import User
from app.schemas.dashboard import DashboardFilterParams, DashboardSummaryResponse
from app.services.dashboard import DashboardService


router = APIRouter(prefix="/dashboard", tags=["dashboard"])
dashboard_rate_limiter: InMemoryRateLimiter | None = None


def get_dashboard_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global dashboard_rate_limiter
    if (
        dashboard_rate_limiter is None
        or dashboard_rate_limiter.limit != settings.dashboard_rate_limit_requests
        or dashboard_rate_limiter.window_seconds != settings.dashboard_rate_limit_window_seconds
    ):
        dashboard_rate_limiter = InMemoryRateLimiter(
            limit=settings.dashboard_rate_limit_requests,
            window_seconds=settings.dashboard_rate_limit_window_seconds,
        )
    return dashboard_rate_limiter


def check_dashboard_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_dashboard_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentDashboardUser = Annotated[User, Depends(check_dashboard_rate_limit)]


def get_dashboard_filters(
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
) -> DashboardFilterParams:
    try:
        return DashboardFilterParams(month=month)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    filters: Annotated[DashboardFilterParams, Depends(get_dashboard_filters)],
    current_user: CurrentDashboardUser,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DashboardSummaryResponse:
    return DashboardService().summarize(
        session=session,
        user_id=current_user.id,
        month=filters.month,
        low_confidence_threshold=settings.dashboard_low_confidence_threshold,
    )

