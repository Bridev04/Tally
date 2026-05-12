import uuid

from sqlmodel import Session

from app.models import AuditLog


def create_audit_log(*, session: Session, user_id: uuid.UUID, action: str) -> AuditLog:
    audit_log = AuditLog(user_id=user_id, action=action, metadata_json={})
    session.add(audit_log)
    return audit_log
