from typing import Annotated
import logging
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip
from app.db.session import get_session
from app.models import TransactionUpload, User
from app.schemas.imports import (
    DemoLoadRequest,
    DemoLoadResponse,
    DemoResetRequest,
    DemoScenarioListResponse,
    DemoScenarioRead,
    ImportErrorRow,
    ImportResultResponse,
    PasteConfirmRequest,
    PastePreviewRequest,
    PastePreviewResponse,
    PasteValidRow,
    UploadRead,
)
from app.services.audit import create_audit_log
from app.services.csv_import import CSVImportService
from app.services.demo_data import DemoDataService
from app.services.paste_import import PasteImportService
from app.services.subscription_detection import SubscriptionDetectionService
from app.services.transaction_import_utils import ImportValidationError


router = APIRouter(tags=["imports"])
logger = logging.getLogger(__name__)
import_rate_limiter: InMemoryRateLimiter | None = None


def get_import_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global import_rate_limiter
    if (
        import_rate_limiter is None
        or import_rate_limiter.limit != settings.import_rate_limit_requests
        or import_rate_limiter.window_seconds != settings.import_rate_limit_window_seconds
    ):
        import_rate_limiter = InMemoryRateLimiter(
            limit=settings.import_rate_limit_requests,
            window_seconds=settings.import_rate_limit_window_seconds,
        )
    return import_rate_limiter


def check_import_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_import_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentImportUser = Annotated[User, Depends(check_import_rate_limit)]


@router.post("/uploads/csv", response_model=ImportResultResponse, status_code=status.HTTP_201_CREATED)
async def upload_csv(
    current_user: CurrentImportUser,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    file: UploadFile = File(...),
) -> ImportResultResponse:
    service = CSVImportService(max_upload_bytes=settings.max_upload_bytes, max_rows=settings.max_import_rows)
    try:
        result = await service.import_upload(session=session, user_id=current_user.id, upload_file=file)
    except ImportValidationError as exc:
        session.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="transaction_upload.csv_uploaded",
        metadata={
            "upload_id": str(result.upload.id),
            "total_rows": result.total_rows,
            "processed_rows": result.processed_rows,
            "duplicate_rows": result.duplicate_rows,
        },
    )
    SubscriptionDetectionService().detect_and_upsert(session=session, user_id=current_user.id)
    session.commit()
    session.refresh(result.upload)
    logger.info(
        "CSV upload completed",
        extra={"user_id": str(current_user.id), "upload_id": str(result.upload.id)},
    )
    return ImportResultResponse(
        upload_id=result.upload.id,
        total_rows=result.total_rows,
        processed_rows=result.processed_rows,
        duplicate_rows=result.duplicate_rows,
    )


@router.get("/uploads", response_model=list[UploadRead])
def list_uploads(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> list[TransactionUpload]:
    return session.exec(
        select(TransactionUpload)
        .where(TransactionUpload.user_id == current_user.id)
        .order_by(TransactionUpload.created_at.desc())
    ).all()


@router.get("/uploads/{upload_id}", response_model=UploadRead)
def get_upload(
    upload_id: uuid.UUID,
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TransactionUpload:
    upload = session.get(TransactionUpload, upload_id)
    if upload is None or upload.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Upload not found.")
    return upload


@router.post("/imports/paste/preview", response_model=PastePreviewResponse)
def preview_paste_import(
    payload: PastePreviewRequest,
    current_user: CurrentImportUser,
    settings: Annotated[Settings, Depends(get_settings)],
) -> PastePreviewResponse:
    del current_user
    service = PasteImportService(max_rows=settings.max_import_rows, max_bytes=settings.max_paste_import_bytes)
    try:
        preview = service.preview(text=payload.text)
    except ImportValidationError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc
    return PastePreviewResponse(
        valid_rows=[PasteValidRow(**row.__dict__) for row in preview.valid_rows],
        invalid_rows=[ImportErrorRow(**row) for row in preview.invalid_rows],
    )


@router.post("/imports/paste/confirm", response_model=ImportResultResponse, status_code=status.HTTP_201_CREATED)
def confirm_paste_import(
    payload: PasteConfirmRequest,
    current_user: CurrentImportUser,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ImportResultResponse:
    service = PasteImportService(max_rows=settings.max_import_rows, max_bytes=settings.max_paste_import_bytes)
    try:
        result = service.confirm(session=session, user_id=current_user.id, text=payload.text)
    except ImportValidationError as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc)) from exc

    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="transaction_import.paste_confirmed",
        metadata={
            "upload_id": str(result.upload.id),
            "total_rows": result.total_rows,
            "processed_rows": result.processed_rows,
            "duplicate_rows": result.duplicate_rows,
            "invalid_rows": len(result.invalid_rows),
        },
    )
    SubscriptionDetectionService().detect_and_upsert(session=session, user_id=current_user.id)
    session.commit()
    return ImportResultResponse(
        upload_id=result.upload.id,
        total_rows=result.total_rows,
        processed_rows=result.processed_rows,
        duplicate_rows=result.duplicate_rows,
        invalid_rows=[ImportErrorRow(**row) for row in result.invalid_rows],
    )


@router.get("/demo/scenarios", response_model=DemoScenarioListResponse)
def list_demo_scenarios(
    current_user: CurrentImportUser,
) -> DemoScenarioListResponse:
    del current_user
    return DemoScenarioListResponse(
        scenarios=[DemoScenarioRead(**item.__dict__) for item in DemoDataService().scenarios()]
    )


@router.post("/demo/load-sample-data", response_model=DemoLoadResponse, status_code=status.HTTP_201_CREATED)
def load_sample_data(
    payload: DemoLoadRequest,
    current_user: CurrentImportUser,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DemoLoadResponse:
    service = DemoDataService()
    try:
        result = service.load(
            session=session,
            user_id=current_user.id,
            scenario=payload.scenario,
            reset_existing_demo=payload.should_reset_demo,
            run_processing=payload.run_processing,
            current_user=current_user,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc
    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="transaction_import.demo_data_loaded",
        metadata={
            "upload_id": str(result.upload.id) if result.upload is not None else None,
            "scenario": result.scenario,
            "processed_rows": result.processed_rows,
            "duplicate_rows": result.duplicate_rows,
            "reset_existing_demo": result.reset_existing_demo,
            "run_processing": result.run_processing,
            "subscriptions_detected": result.subscriptions_detected,
            "anomalies_detected": result.anomalies_detected,
            "reports_generated": result.reports_generated,
        },
    )
    session.commit()
    return DemoLoadResponse(
        upload_id=result.upload.id,
        total_rows=result.total_rows,
        processed_rows=result.processed_rows,
        duplicate_rows=result.duplicate_rows,
        scenario=result.scenario,
        transactions_created=result.processed_rows,
        uploads_created=result.uploads_created,
        subscriptions_detected=result.subscriptions_detected,
        anomalies_detected=result.anomalies_detected,
        reports_generated=result.reports_generated,
        reset_existing_demo=result.reset_existing_demo,
        run_processing=result.run_processing,
        message="Demo data loaded. You can now explore your dashboard.",
    )


@router.post("/demo/reset", response_model=DemoLoadResponse)
def reset_demo_data(
    payload: DemoResetRequest,
    current_user: CurrentImportUser,
    session: Annotated[Session, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> DemoLoadResponse:
    service = DemoDataService()
    try:
        result = service.reset(
            session=session,
            user_id=current_user.id,
            scenario=payload.scenario,
            run_processing=payload.run_processing,
            current_user=current_user,
            settings=settings,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc
    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="transaction_import.demo_data_reset",
        metadata={
            "upload_id": str(result.upload.id) if result.upload is not None else None,
            "scenario": result.scenario,
            "processed_rows": result.processed_rows,
            "run_processing": result.run_processing,
        },
    )
    session.commit()
    return DemoLoadResponse(
        upload_id=result.upload.id if result.upload is not None else uuid.uuid4(),
        total_rows=result.total_rows,
        processed_rows=result.processed_rows,
        duplicate_rows=result.duplicate_rows,
        scenario=result.scenario,
        transactions_created=result.processed_rows,
        uploads_created=result.uploads_created,
        subscriptions_detected=result.subscriptions_detected,
        anomalies_detected=result.anomalies_detected,
        reports_generated=result.reports_generated,
        reset_existing_demo=True,
        run_processing=result.run_processing,
        message=(
            "Demo data reset and reloaded. You can now explore your dashboard."
            if result.upload is not None
            else "Demo data reset."
        ),
    )
