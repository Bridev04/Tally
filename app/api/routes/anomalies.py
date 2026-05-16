from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import ValidationError
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip
from app.db.session import get_session
from app.models import User
from app.schemas.spending_anomaly import (
    AnomalyDetectionResponse,
    AnomalyDetectRequest,
    AnomalyFilterParams,
    AnomalyListResponse,
    AnomalySummaryItem,
    AnomalySummaryResponse,
    AnomalyType,
    Severity,
    SpendingAnomalyRead,
)
from app.services.anomalies import AnomalyDetectionService


router = APIRouter(prefix="/anomalies", tags=["anomalies"])
anomaly_rate_limiter: InMemoryRateLimiter | None = None


def get_anomaly_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global anomaly_rate_limiter
    if (
        anomaly_rate_limiter is None
        or anomaly_rate_limiter.limit != settings.anomaly_rate_limit_requests
        or anomaly_rate_limiter.window_seconds != settings.anomaly_rate_limit_window_seconds
    ):
        anomaly_rate_limiter = InMemoryRateLimiter(
            limit=settings.anomaly_rate_limit_requests,
            window_seconds=settings.anomaly_rate_limit_window_seconds,
        )
    return anomaly_rate_limiter


def check_anomaly_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_anomaly_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentAnomalyUser = Annotated[User, Depends(check_anomaly_rate_limit)]


def get_anomaly_filters(
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
    severity: Annotated[Severity | None, Query()] = None,
    anomaly_type: Annotated[AnomalyType | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AnomalyFilterParams:
    try:
        return AnomalyFilterParams(
            month=month,
            severity=severity,
            anomaly_type=anomaly_type,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc


@router.post("/detect", response_model=AnomalyDetectionResponse)
def detect_anomalies(
    current_user: CurrentAnomalyUser,
    session: Annotated[Session, Depends(get_session)],
    payload: AnomalyDetectRequest | None = None,
) -> AnomalyDetectionResponse:
    payload = payload or AnomalyDetectRequest()
    summary = AnomalyDetectionService().detect_and_upsert(
        session=session,
        user_id=current_user.id,
        month=payload.month,
        force_refresh=payload.force_refresh,
        audit=True,
    )
    session.commit()
    return AnomalyDetectionResponse(
        anomalies=[SpendingAnomalyRead.model_validate(item) for item in summary.anomalies],
        detected_count=summary.detected_count,
        month=summary.month,
    )


@router.get("", response_model=AnomalyListResponse)
def list_anomalies(
    filters: Annotated[AnomalyFilterParams, Depends(get_anomaly_filters)],
    current_user: CurrentAnomalyUser,
    session: Annotated[Session, Depends(get_session)],
) -> AnomalyListResponse:
    anomalies = AnomalyDetectionService().list_anomalies(
        session=session,
        user_id=current_user.id,
        filters=filters,
    )
    return AnomalyListResponse(
        anomalies=[SpendingAnomalyRead.model_validate(item) for item in anomalies],
        limit=filters.limit,
        offset=filters.offset,
        count=len(anomalies),
    )


@router.get("/summary", response_model=AnomalySummaryResponse)
def get_anomaly_summary(
    current_user: CurrentAnomalyUser,
    session: Annotated[Session, Depends(get_session)],
    month: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None,
) -> AnomalySummaryResponse:
    try:
        AnomalyFilterParams(month=month, limit=50, offset=0)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc

    window, anomalies = AnomalyDetectionService().summarize(
        session=session,
        user_id=current_user.id,
        month=month,
    )
    severity_counts = {item.value: 0 for item in Severity}
    category_counts: dict[str, int] = {}
    merchant_counts: dict[str, int] = {}
    for anomaly in anomalies:
        severity_counts[anomaly.severity] = severity_counts.get(anomaly.severity, 0) + 1
        if anomaly.category:
            category_counts[anomaly.category] = category_counts.get(anomaly.category, 0) + 1
        if anomaly.merchant_name:
            merchant_counts[anomaly.merchant_name] = merchant_counts.get(anomaly.merchant_name, 0) + 1

    return AnomalySummaryResponse(
        total_anomalies=len(anomalies),
        high_count=severity_counts[Severity.high.value],
        medium_count=severity_counts[Severity.medium.value],
        low_count=severity_counts[Severity.low.value],
        top_categories=[
            AnomalySummaryItem(name=name, count=count)
            for name, count in sorted(category_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        ],
        top_merchants=[
            AnomalySummaryItem(name=name, count=count)
            for name, count in sorted(merchant_counts.items(), key=lambda item: (-item[1], item[0]))[:5]
        ],
        month=window.label,
    )
