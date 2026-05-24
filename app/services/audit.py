from sqlalchemy.orm import Session

from app.db.models import AuditLog
from app.models.case import AuditRecord


class AuditService:
    def __init__(self, db: Session | None = None) -> None:
        self.db = db
        self.records: list[AuditRecord] = []

    def record(self, audit: AuditRecord) -> None:
        if self.db is None:
            self.records.append(audit)
            return
        self.db.add(
            AuditLog(
                actor=audit.actor,
                action=audit.action,
                resource_type=audit.resource_type,
                resource_id=audit.resource_id,
                details=audit.details,
            )
        )
        self.db.commit()
