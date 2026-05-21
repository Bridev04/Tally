from typing import Any
import uuid

from sqlalchemy import func, or_
from sqlmodel import Session, select

from app.models import MonthlyInsightReport, SpendingAnomaly, Subscription, Transaction, TransactionUpload, User
from app.models.audit_log import AuditLog
from app.models.common import utc_now
from app.schemas.privacy import (
    ClearDemoDataResponse,
    DataExportResponse,
    DataSourcesUsed,
    DeletedCounts,
    DeleteAccountResponse,
    DeleteAppDataResponse,
    ExportAnomaly,
    ExportMetadata,
    ExportMonthlyReport,
    ExportSubscription,
    ExportTransaction,
    ExportUpload,
    ExportUser,
    PrivacySummaryResponse,
)


DEMO_UPLOAD_FILE_NAME = "synthetic-demo-data"
MANUAL_UPLOAD_FILE_NAME = "manual-entry"
PASTE_UPLOAD_FILE_NAME = "paste-import"
PRIVACY_NOTES = [
    "Tally does not connect to banks.",
    "Tally does not use Plaid or FinanceKit.",
    "Tally does not provide financial advice.",
    "Data is based on imported, manual, pasted, or synthetic demo entries only.",
]
EXPORT_NOTICE = (
    "This export contains Tally app data based on imported/manual/demo transactions only. "
    "Tally does not connect to banks and does not provide financial advice."
)


class PrivacyService:
    def get_privacy_summary(self, *, session: Session, current_user: User) -> PrivacySummaryResponse:
        uploads = self._uploads_for_user(session=session, user_id=current_user.id)
        latest_upload_date = max((upload.created_at for upload in uploads), default=None)
        latest_report_date = session.exec(
            select(func.max(MonthlyInsightReport.created_at)).where(MonthlyInsightReport.user_id == current_user.id)
        ).one()

        return PrivacySummaryResponse(
            user_email=current_user.email,
            transaction_count=self._count(session=session, model=Transaction, user_id=current_user.id),
            upload_count=len(uploads),
            subscription_count=self._count(session=session, model=Subscription, user_id=current_user.id),
            anomaly_count=self._count(session=session, model=SpendingAnomaly, user_id=current_user.id),
            monthly_report_count=self._count(session=session, model=MonthlyInsightReport, user_id=current_user.id),
            has_demo_data=any(upload.file_name == DEMO_UPLOAD_FILE_NAME for upload in uploads),
            latest_upload_date=latest_upload_date,
            latest_report_date=latest_report_date,
            data_sources_used=self._data_sources_from_uploads(uploads),
            privacy_notes=PRIVACY_NOTES,
        )

    def export_user_data(self, *, session: Session, current_user: User) -> DataExportResponse:
        uploads = self._uploads_for_user(session=session, user_id=current_user.id)
        transactions = session.exec(
            select(Transaction)
            .where(Transaction.user_id == current_user.id)
            .order_by(Transaction.transaction_date, Transaction.created_at)
        ).all()
        subscriptions = session.exec(
            select(Subscription).where(Subscription.user_id == current_user.id).order_by(Subscription.merchant_name)
        ).all()
        anomalies = session.exec(
            select(SpendingAnomaly)
            .where(SpendingAnomaly.user_id == current_user.id)
            .order_by(SpendingAnomaly.created_at.desc())
        ).all()
        reports = session.exec(
            select(MonthlyInsightReport)
            .where(MonthlyInsightReport.user_id == current_user.id)
            .order_by(MonthlyInsightReport.month.desc())
        ).all()

        return DataExportResponse(
            metadata=ExportMetadata(exported_at=utc_now(), app="Tally", scope="current_user", notice=EXPORT_NOTICE),
            user=ExportUser(id=current_user.id, email=current_user.email, created_at=current_user.created_at),
            uploads=[
                ExportUpload(
                    id=item.id,
                    file_name=item.file_name,
                    upload_status=item.upload_status,
                    total_rows=item.total_rows,
                    processed_rows=item.processed_rows,
                    source=item.source,
                    is_demo=item.is_demo,
                    demo_scenario=item.demo_scenario,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in uploads
            ],
            transactions=[
                ExportTransaction(
                    id=item.id,
                    upload_id=item.upload_id,
                    transaction_date=item.transaction_date,
                    merchant_raw=item.merchant_raw,
                    merchant_normalized=item.merchant_normalized,
                    description=item.description,
                    amount=item.amount,
                    currency=item.currency,
                    category=item.category,
                    category_confidence=item.category_confidence,
                    category_manually_set=item.category_manually_set,
                    category_source=item.category_source,
                    categorization_reason=item.categorization_reason,
                    categorization_rule=item.categorization_rule,
                    payment_type=item.payment_type,
                    is_recurring_candidate=item.is_recurring_candidate,
                    source=item.source,
                    is_demo=item.is_demo,
                    demo_scenario=item.demo_scenario,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in transactions
            ],
            subscriptions=[
                ExportSubscription(
                    id=item.id,
                    merchant_name=item.merchant_name,
                    average_amount=item.average_amount,
                    frequency=item.frequency,
                    first_seen=item.first_seen,
                    last_seen=item.last_seen,
                    next_expected_date=item.next_expected_date,
                    confidence_score=item.confidence_score,
                    status=item.status,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in subscriptions
            ],
            anomalies=[
                ExportAnomaly(
                    id=item.id,
                    anomaly_type=item.anomaly_type,
                    category=item.category,
                    merchant_name=item.merchant_name,
                    amount_delta=item.amount_delta,
                    percentage_change=item.percentage_change,
                    explanation=item.explanation,
                    severity=item.severity,
                    period_start=item.period_start,
                    period_end=item.period_end,
                    baseline_period_start=item.baseline_period_start,
                    baseline_period_end=item.baseline_period_end,
                    transaction_count=item.transaction_count,
                    created_at=item.created_at,
                )
                for item in anomalies
            ],
            monthly_reports=[
                ExportMonthlyReport(
                    id=item.id,
                    month=item.month,
                    total_spend=item.total_spend,
                    total_income=item.total_income,
                    net_flow=item.net_flow,
                    transaction_count=item.transaction_count,
                    top_categories_json=item.top_categories_json,
                    detected_subscriptions_json=item.detected_subscriptions_json,
                    anomalies_json=item.anomalies_json,
                    ai_summary=item.ai_summary,
                    generated_status=item.generated_status,
                    generation_source=item.generation_source,
                    safety_flags_json=item.safety_flags_json,
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                )
                for item in reports
            ],
        )

    def clear_demo_data(self, *, session: Session, current_user: User) -> ClearDemoDataResponse:
        demo_uploads = session.exec(
            select(TransactionUpload).where(
                TransactionUpload.user_id == current_user.id,
                or_(TransactionUpload.is_demo.is_(True), TransactionUpload.file_name == DEMO_UPLOAD_FILE_NAME),
            )
        ).all()
        if not demo_uploads:
            return ClearDemoDataResponse(message="No demo data was found.", deleted_counts=DeletedCounts())

        upload_ids = [upload.id for upload in demo_uploads]
        deleted_counts = DeletedCounts(
            transactions=session.exec(
                select(func.count()).select_from(Transaction).where(Transaction.upload_id.in_(upload_ids))
            ).one(),
            uploads=len(demo_uploads),
            subscriptions=self._count(session=session, model=Subscription, user_id=current_user.id),
            anomalies=self._count(session=session, model=SpendingAnomaly, user_id=current_user.id),
            monthly_reports=self._count(session=session, model=MonthlyInsightReport, user_id=current_user.id),
        )

        self._delete_all_for_user(session=session, model=Subscription, user_id=current_user.id)
        self._delete_all_for_user(session=session, model=SpendingAnomaly, user_id=current_user.id)
        self._delete_all_for_user(session=session, model=MonthlyInsightReport, user_id=current_user.id)
        demo_transactions = session.exec(select(Transaction).where(Transaction.upload_id.in_(upload_ids))).all()
        for transaction in demo_transactions:
            session.delete(transaction)
        session.flush()
        for upload in demo_uploads:
            session.delete(upload)
        session.flush()
        return ClearDemoDataResponse(message="Demo data cleared.", deleted_counts=deleted_counts)

    def delete_imported_data(self, *, session: Session, current_user: User) -> DeleteAppDataResponse:
        deleted_counts = DeletedCounts(
            transactions=self._count(session=session, model=Transaction, user_id=current_user.id),
            uploads=self._count(session=session, model=TransactionUpload, user_id=current_user.id),
            subscriptions=self._count(session=session, model=Subscription, user_id=current_user.id),
            anomalies=self._count(session=session, model=SpendingAnomaly, user_id=current_user.id),
            monthly_reports=self._count(session=session, model=MonthlyInsightReport, user_id=current_user.id),
        )
        self._delete_user_app_records(session=session, user_id=current_user.id, include_audit_logs=False)
        session.flush()
        return DeleteAppDataResponse(message="Tally app data deleted. Your account remains active.", deleted_counts=deleted_counts)

    def delete_account_data(self, *, session: Session, current_user: User) -> DeleteAccountResponse:
        deleted_counts = DeletedCounts(
            transactions=self._count(session=session, model=Transaction, user_id=current_user.id),
            uploads=self._count(session=session, model=TransactionUpload, user_id=current_user.id),
            subscriptions=self._count(session=session, model=Subscription, user_id=current_user.id),
            anomalies=self._count(session=session, model=SpendingAnomaly, user_id=current_user.id),
            monthly_reports=self._count(session=session, model=MonthlyInsightReport, user_id=current_user.id),
            audit_logs=self._count(session=session, model=AuditLog, user_id=current_user.id),
            user=1,
        )
        self._delete_user_app_records(session=session, user_id=current_user.id, include_audit_logs=True)
        session.delete(current_user)
        session.flush()
        return DeleteAccountResponse(
            message="Your Tally account and associated app data were deleted.",
            deleted_counts=deleted_counts,
            session_notice="Existing tokens are not stored server-side; future authenticated requests fail because the account no longer exists.",
        )

    def _uploads_for_user(self, *, session: Session, user_id: uuid.UUID) -> list[TransactionUpload]:
        return session.exec(
            select(TransactionUpload)
            .where(TransactionUpload.user_id == user_id)
            .order_by(TransactionUpload.created_at.desc())
        ).all()

    def _data_sources_from_uploads(self, uploads: list[TransactionUpload]) -> DataSourcesUsed:
        source_names = {upload.file_name for upload in uploads}
        return DataSourcesUsed(
            csv_upload=any(upload.source == "csv" for upload in uploads)
            or any(name not in {MANUAL_UPLOAD_FILE_NAME, PASTE_UPLOAD_FILE_NAME, DEMO_UPLOAD_FILE_NAME} for name in source_names),
            manual_entry=any(upload.source == "manual" for upload in uploads) or MANUAL_UPLOAD_FILE_NAME in source_names,
            paste_import=any(upload.source == "paste" for upload in uploads) or PASTE_UPLOAD_FILE_NAME in source_names,
            demo_data=any(upload.is_demo or upload.file_name == DEMO_UPLOAD_FILE_NAME for upload in uploads),
        )

    def _count(self, *, session: Session, model: Any, user_id: uuid.UUID) -> int:
        return session.exec(select(func.count()).select_from(model).where(model.user_id == user_id)).one()

    def _delete_user_app_records(self, *, session: Session, user_id: uuid.UUID, include_audit_logs: bool) -> None:
        self._delete_all_for_user(session=session, model=Subscription, user_id=user_id)
        self._delete_all_for_user(session=session, model=SpendingAnomaly, user_id=user_id)
        self._delete_all_for_user(session=session, model=MonthlyInsightReport, user_id=user_id)
        self._delete_all_for_user(session=session, model=Transaction, user_id=user_id)
        session.flush()
        self._delete_all_for_user(session=session, model=TransactionUpload, user_id=user_id)
        if include_audit_logs:
            self._delete_all_for_user(session=session, model=AuditLog, user_id=user_id)

    def _delete_all_for_user(self, *, session: Session, model: Any, user_id: uuid.UUID) -> None:
        records = session.exec(select(model).where(model.user_id == user_id)).all()
        for record in records:
            session.delete(record)
