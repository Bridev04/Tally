from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip
from app.db.session import get_session
from app.models import User
from app.schemas.monthly_insight_report import (
    MonthlyReportFilterParams,
    MonthlyReportGenerateRequest,
    MonthlyReportListResponse,
    MonthlyReportRead,
)
from app.services.monthly_reports import MonthlyReportService


router = APIRouter(prefix="/reports/monthly", tags=["reports"])
report_rate_limiter: InMemoryRateLimiter | None = None


def get_report_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global report_rate_limiter
    if (
        report_rate_limiter is None
        or report_rate_limiter.limit != settings.report_rate_limit_requests
        or report_rate_limiter.window_seconds != settings.report_rate_limit_window_seconds
    ):
        report_rate_limiter = InMemoryRateLimiter(
            limit=settings.report_rate_limit_requests,
            window_seconds=settings.report_rate_limit_window_seconds,
        )
    return report_rate_limiter


def check_report_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_report_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentReportUser = Annotated[User, Depends(check_report_rate_limit)]


def get_report_filters(
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> MonthlyReportFilterParams:
    try:
        return MonthlyReportFilterParams(month=month, limit=limit, offset=offset)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc


@router.post("/generate", response_model=MonthlyReportRead)
def generate_monthly_report(
    payload: MonthlyReportGenerateRequest,
    current_user: CurrentReportUser,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> MonthlyReportRead:
    report = MonthlyReportService().generate(
        session=session,
        current_user=current_user,
        month=payload.month,
        settings=settings,
        use_ai=payload.use_ai,
        force_refresh=payload.force_refresh,
    )
    session.commit()
    session.refresh(report)
    return MonthlyReportService().to_read(report)


@router.get("", response_model=MonthlyReportListResponse)
def list_monthly_reports(
    filters: Annotated[MonthlyReportFilterParams, Depends(get_report_filters)],
    current_user: CurrentReportUser,
    session: Annotated[Session, Depends(get_session)],
) -> MonthlyReportListResponse:
    reports = MonthlyReportService().list_reports(
        session=session,
        user_id=current_user.id,
        month=filters.month,
        limit=filters.limit,
        offset=filters.offset,
    )
    service = MonthlyReportService()
    return MonthlyReportListResponse(
        reports=[service.to_read(item) for item in reports],
        limit=filters.limit,
        offset=filters.offset,
        count=len(reports),
    )


@router.get("/{report_id}", response_model=MonthlyReportRead)
def get_monthly_report(
    report_id: uuid.UUID,
    current_user: CurrentReportUser,
    session: Annotated[Session, Depends(get_session)],
) -> MonthlyReportRead:
    service = MonthlyReportService()
    report = service.get_for_user(session=session, user_id=current_user.id, report_id=report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found.")
    return service.to_read(report)
