from datetime import date
from decimal import Decimal, ROUND_HALF_UP
import uuid

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.models import Transaction
from app.schemas.transaction import (
    CategorySummaryItem,
    CategorySummaryResponse,
    MerchantSummaryItem,
    MerchantSummaryResponse,
    TransactionCategory,
    TransactionFilterParams,
)
from app.services.audit import create_audit_log
from app.services.transaction_import_utils import normalize_merchant


class TransactionService:
    def list_transactions(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        filters: TransactionFilterParams,
    ) -> list[Transaction]:
        statement = self._filtered_statement(user_id=user_id, filters=filters)
        statement = statement.order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc(),
        ).limit(filters.limit).offset(filters.offset)
        return session.exec(statement).all()

    def get_transaction(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
    ) -> Transaction | None:
        return session.exec(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        ).first()

    def update_category(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        transaction_id: uuid.UUID,
        category: TransactionCategory,
    ) -> Transaction | None:
        transaction = self.get_transaction(session=session, user_id=user_id, transaction_id=transaction_id)
        if transaction is None:
            return None

        old_category = transaction.category
        transaction.category = category.value
        transaction.category_manually_set = True
        session.add(transaction)
        create_audit_log(
            session=session,
            user_id=user_id,
            action="transaction.category_changed",
            metadata={
                "transaction_id": str(transaction.id),
                "old_category": old_category,
                "new_category": category.value,
            },
        )
        session.flush()
        session.refresh(transaction)
        return transaction

    def category_summary(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CategorySummaryResponse:
        filters = TransactionFilterParams(date_from=date_from, date_to=date_to, limit=100, offset=0)
        base_conditions = self._base_conditions(user_id=user_id, filters=filters)
        category_expr = func.coalesce(Transaction.category, TransactionCategory.needs_review.value)
        expense_total_expr = func.sum(-Transaction.amount)

        rows = session.exec(
            select(category_expr, expense_total_expr, func.count(Transaction.id))
            .where(*base_conditions, Transaction.amount < 0)
            .group_by(category_expr)
            .order_by(expense_total_expr.desc(), category_expr.asc())
        ).all()

        total_expenses = self._decimal_or_zero(
            session.exec(select(func.sum(-Transaction.amount)).where(*base_conditions, Transaction.amount < 0)).one()
        )
        total_income = self._decimal_or_zero(
            session.exec(select(func.sum(Transaction.amount)).where(*base_conditions, Transaction.amount > 0)).one()
        )
        transaction_count = session.exec(select(func.count(Transaction.id)).where(*base_conditions)).one()

        items = [
            CategorySummaryItem(
                category=category,
                total_amount=self._decimal_or_zero(total_amount),
                transaction_count=count,
                percentage_of_total_expenses=self._percentage(self._decimal_or_zero(total_amount), total_expenses),
            )
            for category, total_amount, count in rows
        ]
        return CategorySummaryResponse(
            items=items,
            total_expenses=total_expenses,
            total_income=total_income,
            transaction_count=transaction_count,
        )

    def merchant_summary(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        date_from: date | None = None,
        date_to: date | None = None,
        category: TransactionCategory | None = None,
    ) -> MerchantSummaryResponse:
        filters = TransactionFilterParams(date_from=date_from, date_to=date_to, category=category, limit=100, offset=0)
        base_conditions = self._base_conditions(user_id=user_id, filters=filters)
        merchant_expr = func.coalesce(Transaction.merchant_normalized, Transaction.merchant_raw)
        total_expr = func.sum(Transaction.amount)

        rows = session.exec(
            select(
                merchant_expr,
                total_expr,
                func.count(Transaction.id),
                func.min(Transaction.transaction_date),
                func.max(Transaction.transaction_date),
            )
            .where(*base_conditions)
            .group_by(merchant_expr)
            .order_by(func.count(Transaction.id).desc(), merchant_expr.asc())
        ).all()
        return MerchantSummaryResponse(
            items=[
                MerchantSummaryItem(
                    merchant_normalized=merchant,
                    total_amount=self._decimal_or_zero(total_amount),
                    transaction_count=count,
                    first_seen=first_seen,
                    last_seen=last_seen,
                )
                for merchant, total_amount, count, first_seen, last_seen in rows
            ]
        )

    def _filtered_statement(self, *, user_id: uuid.UUID, filters: TransactionFilterParams):
        return select(Transaction).where(*self._base_conditions(user_id=user_id, filters=filters))

    def _base_conditions(self, *, user_id: uuid.UUID, filters: TransactionFilterParams) -> list:
        conditions = [Transaction.user_id == user_id]
        if filters.date_from is not None:
            conditions.append(Transaction.transaction_date >= filters.date_from)
        if filters.date_to is not None:
            conditions.append(Transaction.transaction_date <= filters.date_to)
        if filters.category is not None:
            conditions.append(Transaction.category == filters.category.value)
        if filters.payment_type is not None:
            conditions.append(func.lower(Transaction.payment_type) == filters.payment_type.strip().lower())
        if filters.min_amount is not None:
            conditions.append(Transaction.amount >= filters.min_amount)
        if filters.max_amount is not None:
            conditions.append(Transaction.amount <= filters.max_amount)
        if filters.merchant is not None:
            merchant = filters.merchant.strip().lower()
            normalized = normalize_merchant(filters.merchant)
            conditions.append(
                or_(
                    func.lower(Transaction.merchant_raw).contains(merchant),
                    func.lower(Transaction.merchant_normalized).contains(normalized),
                )
            )
        if filters.search is not None:
            search = filters.search.strip().lower()
            normalized_search = normalize_merchant(filters.search)
            conditions.append(
                or_(
                    func.lower(Transaction.merchant_raw).contains(search),
                    func.lower(Transaction.merchant_normalized).contains(normalized_search),
                    func.lower(Transaction.description).contains(search),
                )
            )
        return conditions

    def _decimal_or_zero(self, value: Decimal | int | None) -> Decimal:
        if value is None:
            return Decimal("0.00")
        if not isinstance(value, Decimal):
            value = Decimal(str(value))
        return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _percentage(self, value: Decimal, total: Decimal) -> Decimal:
        if total == 0:
            return Decimal("0.00")
        return ((value / total) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
