from typing import Annotated, Literal
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip
from app.db.session import get_session
from app.models import User
from app.schemas.privacy import (
    ClearDemoDataResponse,
    DataExportResponse,
    DeleteAccountRequest,
    DeleteAccountResponse,
    DeleteAppDataRequest,
    DeleteAppDataResponse,
    PrivacySummaryResponse,
)
from app.services.audit import create_audit_log
from app.services.privacy import PrivacyService


router = APIRouter(prefix="/settings/privacy", tags=["privacy"])
logger = logging.getLogger(__name__)
privacy_rate_limiter: InMemoryRateLimiter | None = None


def get_privacy_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global privacy_rate_limiter
    if (
        privacy_rate_limiter is None
        or privacy_rate_limiter.limit != settings.privacy_rate_limit_requests
        or privacy_rate_limiter.window_seconds != settings.privacy_rate_limit_window_seconds
    ):
        privacy_rate_limiter = InMemoryRateLimiter(
            limit=settings.privacy_rate_limit_requests,
            window_seconds=settings.privacy_rate_limit_window_seconds,
        )
    return privacy_rate_limiter


def check_privacy_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_privacy_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentPrivacyUser = Annotated[User, Depends(check_privacy_rate_limit)]


@router.get("/summary", response_model=PrivacySummaryResponse)
def get_privacy_summary(
    current_user: CurrentPrivacyUser,
    session: Annotated[Session, Depends(get_session)],
) -> PrivacySummaryResponse:
    return PrivacyService().get_privacy_summary(session=session, current_user=current_user)


@router.get("/export", response_model=DataExportResponse)
def export_user_data(
    current_user: CurrentPrivacyUser,
    session: Annotated[Session, Depends(get_session)],
    format: Annotated[Literal["json"], Query()] = "json",  # noqa: A002
) -> DataExportResponse:
    del format
    export = PrivacyService().export_user_data(session=session, current_user=current_user)
    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="privacy.data_export_requested",
        metadata={
            "format": "json",
            "transactions": len(export.transactions),
            "uploads": len(export.uploads),
            "subscriptions": len(export.subscriptions),
            "anomalies": len(export.anomalies),
            "monthly_reports": len(export.monthly_reports),
        },
    )
    session.commit()
    logger.info("Privacy export requested", extra={"user_id": str(current_user.id), "format": "json"})
    return export


@router.post("/clear-demo-data", response_model=ClearDemoDataResponse)
def clear_demo_data(
    current_user: CurrentPrivacyUser,
    session: Annotated[Session, Depends(get_session)],
) -> ClearDemoDataResponse:
    try:
        response = PrivacyService().clear_demo_data(session=session, current_user=current_user)
        create_audit_log(
            session=session,
            user_id=current_user.id,
            action="privacy.demo_data_cleared",
            metadata=response.deleted_counts.model_dump(),
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not clear demo data.") from exc
    logger.info("Demo data clear requested", extra={"user_id": str(current_user.id)})
    return response


@router.post("/delete-app-data", response_model=DeleteAppDataResponse)
def delete_app_data(
    payload: DeleteAppDataRequest,
    current_user: CurrentPrivacyUser,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteAppDataResponse:
    del payload
    try:
        response = PrivacyService().delete_imported_data(session=session, current_user=current_user)
        create_audit_log(
            session=session,
            user_id=current_user.id,
            action="privacy.app_data_deleted",
            metadata=response.deleted_counts.model_dump(),
        )
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete Tally app data.") from exc
    logger.info("Tally app data deleted", extra={"user_id": str(current_user.id)})
    return response


@router.post("/delete-account", response_model=DeleteAccountResponse)
def delete_account(
    payload: DeleteAccountRequest,
    current_user: CurrentPrivacyUser,
    session: Annotated[Session, Depends(get_session)],
) -> DeleteAccountResponse:
    del payload
    try:
        response = PrivacyService().delete_account_data(session=session, current_user=current_user)
        session.commit()
    except Exception as exc:
        session.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete Tally account.") from exc
    logger.info("Tally account deleted", extra={"user_id": str(current_user.id)})
    return response

