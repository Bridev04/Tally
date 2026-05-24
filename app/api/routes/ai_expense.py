from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import ValidationError
from sqlmodel import Session

from app.api.deps import get_current_user
from app.core.config import Settings, get_settings
from app.core.rate_limit import InMemoryRateLimiter, get_client_ip
from app.db.session import get_session
from app.models import User
from app.schemas.ai_expense import (
    ChatExpenseConfirmRequest,
    ChatExpenseConfirmResponse,
    ChatExpenseParseRequest,
    ChatExpenseParseResponse,
)
from app.schemas.imports import ManualTransactionRequest
from app.schemas.transaction import TransactionRead
from app.services.ai_expense_parser import AIExpenseParserService
from app.services.audit import create_audit_log
from app.services.manual_transaction import ManualTransactionService
from app.services.subscription_detection import SubscriptionDetectionService


router = APIRouter(prefix="/ai/expense", tags=["ai-expense"])
ai_rate_limiter: InMemoryRateLimiter | None = None


def get_ai_rate_limiter(settings: Annotated[Settings, Depends(get_settings)]) -> InMemoryRateLimiter:
    global ai_rate_limiter
    if (
        ai_rate_limiter is None
        or ai_rate_limiter.limit != settings.ai_rate_limit_requests
        or ai_rate_limiter.window_seconds != settings.ai_rate_limit_window_seconds
    ):
        ai_rate_limiter = InMemoryRateLimiter(
            limit=settings.ai_rate_limit_requests,
            window_seconds=settings.ai_rate_limit_window_seconds,
        )
    return ai_rate_limiter


def check_ai_rate_limit(
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    limiter: Annotated[InMemoryRateLimiter, Depends(get_ai_rate_limiter)],
) -> User:
    limiter.check(key=f"{request.url.path}:{current_user.id}:{get_client_ip(request)}")
    return current_user


CurrentAIUser = Annotated[User, Depends(check_ai_rate_limit)]


@router.post("/parse", response_model=ChatExpenseParseResponse)
def parse_chat_expense(
    payload: ChatExpenseParseRequest,
    current_user: CurrentAIUser,
    session: Annotated[Session, Depends(get_session)],
) -> ChatExpenseParseResponse:
    try:
        response = AIExpenseParserService().parse(message=payload.message, timezone=payload.timezone)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc

    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="ai_expense.parse_requested",
        metadata={
            "clarification_needed": response.clarification_needed,
            "draft_returned": response.draft is not None,
            "message_length": len(payload.message),
        },
    )
    session.commit()
    return response


@router.post("/confirm", response_model=ChatExpenseConfirmResponse, status_code=201)
def confirm_chat_expense(
    payload: ChatExpenseConfirmRequest,
    current_user: CurrentAIUser,
    session: Annotated[Session, Depends(get_session)],
) -> ChatExpenseConfirmResponse:
    draft = payload.draft
    try:
        manual_payload = ManualTransactionRequest(
            transaction_date=draft.transaction_date,
            merchant=draft.merchant,
            description=draft.description,
            amount=draft.amount,
            currency=draft.currency,
            category=draft.category,
        )
    except ValidationError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="Invalid request payload.") from exc

    transaction = ManualTransactionService().create(
        session=session,
        user_id=current_user.id,
        payload=manual_payload,
        source=draft.source,
        file_name="ai-chat-manual-entry",
        payment_type=draft.payment_type,
    )
    create_audit_log(
        session=session,
        user_id=current_user.id,
        action="transaction.ai_chat_manual_created",
        metadata={"transaction_id": str(transaction.id), "source": draft.source},
    )
    SubscriptionDetectionService().detect_and_upsert(session=session, user_id=current_user.id)
    session.commit()
    session.refresh(transaction)
    return ChatExpenseConfirmResponse(
        message="Transaction saved.",
        transaction=TransactionRead.model_validate(transaction),
    )
