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
from app.schemas.subscription import (
    SubscriptionDetectionResponse,
    SubscriptionFilterParams,
    SubscriptionFrequency,
    SubscriptionListResponse,
    SubscriptionRead,
    SubscriptionStatus,
    SubscriptionStatusUpdate,
)
from app.services.subscription_detection import SubscriptionDetectionService


router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
subscription_rate_limiter: InMemoryRateLimiter | None = None


def get_subscription_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global subscription_rate_limiter
    if (
        subscription_rate_limiter is None
        or subscription_rate_limiter.limit != settings.subscription_rate_limit_requests
        or subscription_rate_limiter.window_seconds != settings.subscription_rate_limit_window_seconds
    ):
        subscription_rate_limiter = InMemoryRateLimiter(
            limit=settings.subscription_rate_limit_requests,
            window_seconds=settings.subscription_rate_limit_window_seconds,
        )
    return subscription_rate_limiter


def check_subscription_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_subscription_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentSubscriptionUser = Annotated[User, Depends(check_subscription_rate_limit)]


def get_subscription_filters(
    status_filter: Annotated[SubscriptionStatus | None, Query(alias="status")] = None,
    frequency: Annotated[SubscriptionFrequency | None, Query()] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> SubscriptionFilterParams:
    try:
        return SubscriptionFilterParams(
            status=status_filter,
            frequency=frequency,
            search=search,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc


@router.post("/detect", response_model=SubscriptionDetectionResponse)
def detect_subscriptions(
    current_user: CurrentSubscriptionUser,
    session: Annotated[Session, Depends(get_session)],
) -> SubscriptionDetectionResponse:
    summary = SubscriptionDetectionService().detect_and_upsert(
        session=session,
        user_id=current_user.id,
        audit=True,
    )
    session.commit()
    return SubscriptionDetectionResponse(
        subscriptions=[SubscriptionRead.model_validate(item) for item in summary.subscriptions],
        detected_count=summary.detected_count,
        updated_count=summary.updated_count,
    )


@router.get("", response_model=SubscriptionListResponse)
def list_subscriptions(
    filters: Annotated[SubscriptionFilterParams, Depends(get_subscription_filters)],
    current_user: CurrentSubscriptionUser,
    session: Annotated[Session, Depends(get_session)],
) -> SubscriptionListResponse:
    subscriptions = SubscriptionDetectionService().list_subscriptions(
        session=session,
        user_id=current_user.id,
        filters=filters,
    )
    return SubscriptionListResponse(
        subscriptions=[SubscriptionRead.model_validate(item) for item in subscriptions],
        limit=filters.limit,
        offset=filters.offset,
        count=len(subscriptions),
    )


@router.get("/{subscription_id}", response_model=SubscriptionRead)
def get_subscription(
    subscription_id: uuid.UUID,
    current_user: CurrentSubscriptionUser,
    session: Annotated[Session, Depends(get_session)],
) -> SubscriptionRead:
    subscription = SubscriptionDetectionService().get_subscription(
        session=session,
        user_id=current_user.id,
        subscription_id=subscription_id,
    )
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    return SubscriptionRead.model_validate(subscription)


@router.patch("/{subscription_id}/status", response_model=SubscriptionRead)
def update_subscription_status(
    subscription_id: uuid.UUID,
    payload: SubscriptionStatusUpdate,
    current_user: CurrentSubscriptionUser,
    session: Annotated[Session, Depends(get_session)],
) -> SubscriptionRead:
    subscription = SubscriptionDetectionService().update_status(
        session=session,
        user_id=current_user.id,
        subscription_id=subscription_id,
        status=payload.status.value,
    )
    if subscription is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found.")
    session.commit()
    return SubscriptionRead.model_validate(subscription)
