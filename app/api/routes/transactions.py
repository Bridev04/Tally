from datetime import date
from decimal import Decimal
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
from app.schemas.imports import ManualTransactionRequest, ManualTransactionResponse
from app.schemas.transaction import (
    CategorySummaryResponse,
    MerchantSummaryResponse,
    TransactionCategorizeRequest,
    TransactionCategorizeResponse,
    TransactionCategory,
    TransactionCategoryUpdate,
    TransactionFilterParams,
    TransactionListResponse,
    TransactionRead,
)
from app.services.audit import create_audit_log
from app.services.manual_transaction import ManualTransactionService
from app.services.transaction import TransactionService
from app.services.transaction_categorizer import TransactionCategorizerService


router = APIRouter(prefix="/transactions", tags=["transactions"])
transaction_rate_limiter: InMemoryRateLimiter | None = None


def get_transaction_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global transaction_rate_limiter
    if (
        transaction_rate_limiter is None
        or transaction_rate_limiter.limit != settings.transaction_rate_limit_requests
        or transaction_rate_limiter.window_seconds != settings.transaction_rate_limit_window_seconds
    ):
        transaction_rate_limiter = InMemoryRateLimiter(
            limit=settings.transaction_rate_limit_requests,
            window_seconds=settings.transaction_rate_limit_window_seconds,
        )
    return transaction_rate_limiter


def check_transaction_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_transaction_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentTransactionUser = Annotated[User, Depends(check_transaction_rate_limit)]


def get_transaction_filters(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    category: Annotated[TransactionCategory | None, Query()] = None,
    merchant: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    search: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    payment_type: Annotated[str | None, Query(min_length=1, max_length=100)] = None,
    min_amount: Annotated[Decimal | None, Query()] = None,
    max_amount: Annotated[Decimal | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> TransactionFilterParams:
    try:
        return TransactionFilterParams(
            date_from=date_from,
            date_to=date_to,
            category=category,
            merchant=merchant,
            search=search,
            payment_type=payment_type,
            min_amount=min_amount,
            max_amount=max_amount,
            limit=limit,
            offset=offset,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc


def get_summary_filters(
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> tuple[date | None, date | None]:
    try:
        TransactionFilterParams(date_from=date_from, date_to=date_to, limit=100, offset=0)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc
    return date_from, date_to


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    filters: Annotated[TransactionFilterParams, Depends(get_transaction_filters)],
    current_user: CurrentTransactionUser,
    session: Annotated[Session, Depends(get_session)],
) -> TransactionListResponse:
    transactions = TransactionService().list_transactions(
        session=session,
        user_id=current_user.id,
        filters=filters,
    )
    return TransactionListResponse(
        transactions=[TransactionRead.model_validate(item) for item in transactions],
        limit=filters.limit,
        offset=filters.offset,
        count=len(transactions),
    )


@router.post("/manual", response_model=ManualTransactionResponse, status_code=201)
def create_manual_transaction(
    payload: ManualTransactionRequest,
    current_user: CurrentTransactionUser,
    session: Annotated[Session, Depends(get_session)],
) -> ManualTransactionResponse:
    transaction = ManualTransactionService().create(
        session=session,
        user_id=current_user.id,
        payload=payload,
    )
    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="transaction.manual_created",
        metadata={"transaction_id": str(transaction.id)},
    )
    session.commit()
    session.refresh(transaction)
    return ManualTransactionResponse(transaction=TransactionRead.model_validate(transaction))


@router.get("/categories/summary", response_model=CategorySummaryResponse)
def get_category_summary(
    filters: Annotated[tuple[date | None, date | None], Depends(get_summary_filters)],
    current_user: CurrentTransactionUser,
    session: Annotated[Session, Depends(get_session)],
) -> CategorySummaryResponse:
    date_from, date_to = filters
    return TransactionService().category_summary(
        session=session,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/merchants/summary", response_model=MerchantSummaryResponse)
def get_merchant_summary(
    current_user: CurrentTransactionUser,
    session: Annotated[Session, Depends(get_session)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    category: Annotated[TransactionCategory | None, Query()] = None,
) -> MerchantSummaryResponse:
    try:
        TransactionFilterParams(date_from=date_from, date_to=date_to, category=category, limit=100, offset=0)
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc
    return TransactionService().merchant_summary(
        session=session,
        user_id=current_user.id,
        date_from=date_from,
        date_to=date_to,
        category=category,
    )


@router.post("/categorize", response_model=TransactionCategorizeResponse)
def categorize_transactions(
    payload: TransactionCategorizeRequest,
    current_user: CurrentTransactionUser,
    session: Annotated[Session, Depends(get_session)],
) -> TransactionCategorizeResponse:
    summary = TransactionCategorizerService().categorize_user_transactions(
        session=session,
        user_id=current_user.id,
        force=payload.force,
        overwrite_manual=payload.overwrite_manual,
        transaction_ids=payload.transaction_ids,
    )
    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="transaction.bulk_categorized",
        metadata={
            "processed": summary.processed,
            "updated": summary.updated,
            "skipped_manual": summary.skipped_manual,
            "needs_review": summary.needs_review,
            "transaction_ids_requested": len(payload.transaction_ids or []),
            "force": payload.force,
            "overwrite_manual": payload.overwrite_manual,
        },
    )
    session.commit()
    return TransactionCategorizeResponse(
        processed=summary.processed,
        updated=summary.updated,
        skipped_manual=summary.skipped_manual,
        needs_review=summary.needs_review,
        categories=summary.categories,
    )


@router.get("/{transaction_id}", response_model=TransactionRead)
def get_transaction(
    transaction_id: uuid.UUID,
    current_user: CurrentTransactionUser,
    session: Annotated[Session, Depends(get_session)],
) -> TransactionRead:
    transaction = TransactionService().get_transaction(
        session=session,
        user_id=current_user.id,
        transaction_id=transaction_id,
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    return TransactionRead.model_validate(transaction)


@router.patch("/{transaction_id}/category", response_model=TransactionRead)
def update_transaction_category(
    transaction_id: uuid.UUID,
    payload: TransactionCategoryUpdate,
    current_user: CurrentTransactionUser,
    session: Annotated[Session, Depends(get_session)],
) -> TransactionRead:
    transaction = TransactionService().update_category(
        session=session,
        user_id=current_user.id,
        transaction_id=transaction_id,
        category=payload.category,
    )
    if transaction is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaction not found.")
    session.commit()
    session.refresh(transaction)
    return TransactionRead.model_validate(transaction)
