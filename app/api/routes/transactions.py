from typing import Annotated

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.api.deps import get_current_user
from app.api.routes.imports import CurrentImportUser
from app.db.session import get_session
from app.models import Transaction, User
from app.schemas.imports import ManualTransactionRequest, ManualTransactionResponse, TransactionListResponse, TransactionRead
from app.services.audit import create_audit_log
from app.services.manual_transaction import ManualTransactionService


router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=TransactionListResponse)
def list_transactions(
    current_user: Annotated[User, Depends(get_current_user)],
    session: Annotated[Session, Depends(get_session)],
) -> TransactionListResponse:
    transactions = session.exec(
        select(Transaction)
        .where(Transaction.user_id == current_user.id)
        .order_by(Transaction.transaction_date.desc(), Transaction.created_at.desc())
        .limit(200)
    ).all()
    return TransactionListResponse(transactions=[TransactionRead.model_validate(item) for item in transactions])


@router.post("/manual", response_model=ManualTransactionResponse, status_code=201)
def create_manual_transaction(
    payload: ManualTransactionRequest,
    current_user: CurrentImportUser,
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
