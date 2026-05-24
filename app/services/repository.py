from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import InvestigationCase
from app.models.case import CaseRecord


class CaseRepository:
    def save(self, case: CaseRecord) -> CaseRecord:
        raise NotImplementedError

    def get(self, case_id: str) -> CaseRecord | None:
        raise NotImplementedError

    def list_recent(self, limit: int = 25) -> list[CaseRecord]:
        raise NotImplementedError


class InMemoryCaseRepository(CaseRepository):
    def __init__(self) -> None:
        self._cases: dict[str, CaseRecord] = {}

    def save(self, case: CaseRecord) -> CaseRecord:
        case.updated_at = datetime.now(UTC)
        self._cases[case.id] = case
        return case

    def get(self, case_id: str) -> CaseRecord | None:
        return self._cases.get(case_id)

    def list_recent(self, limit: int = 25) -> list[CaseRecord]:
        return sorted(self._cases.values(), key=lambda case: case.updated_at, reverse=True)[:limit]


class SqlAlchemyCaseRepository(CaseRepository):
    def __init__(self, db: Session) -> None:
        self.db = db

    def save(self, case: CaseRecord) -> CaseRecord:
        payload = case.model_dump(mode="json")
        row = self.db.get(InvestigationCase, case.id)
        if row is None:
            row = InvestigationCase(
                id=case.id,
                customer_id=case.customer_id,
                case_type=case.case_type.value,
                summary=case.summary,
                amount=case.amount,
                currency=case.currency,
                channel=case.channel,
                status=case.status.value,
                payload=payload,
            )
            self.db.add(row)
        else:
            row.customer_id = case.customer_id
            row.case_type = case.case_type.value
            row.summary = case.summary
            row.amount = case.amount
            row.currency = case.currency
            row.channel = case.channel
            row.status = case.status.value
            row.payload = payload
        self.db.commit()
        return case

    def get(self, case_id: str) -> CaseRecord | None:
        row = self.db.get(InvestigationCase, case_id)
        if row is None:
            return None
        return CaseRecord.model_validate(row.payload)

    def list_recent(self, limit: int = 25) -> list[CaseRecord]:
        rows = self.db.scalars(
            select(InvestigationCase).order_by(InvestigationCase.updated_at.desc()).limit(limit)
        ).all()
        return [CaseRecord.model_validate(row.payload) for row in rows]
