import uuid

from sqlmodel import Session

from app.models import AuditLog


def create_audit_log(
    *,
    session: Session,
    user_id: uuid.UUID,
    action: str,
    metadata: dict | None = None,
) -> AuditLog:
    audit_log = AuditLog(user_id=user_id, action=action, metadata_json=metadata or {})
    session.add(audit_log)
    return audit_log
