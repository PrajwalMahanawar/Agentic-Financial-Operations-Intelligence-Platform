from datetime import UTC, datetime

from sqlalchemy import JSON, DateTime, Float, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class InvestigationCase(Base):
    __tablename__ = "investigation_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    customer_id: Mapped[str] = mapped_column(String(128), index=True)
    case_type: Mapped[str] = mapped_column(String(32), index=True)
    summary: Mapped[str] = mapped_column(Text)
    amount: Mapped[float] = mapped_column(Float)
    currency: Mapped[str] = mapped_column(String(3))
    channel: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    actor: Mapped[str] = mapped_column(String(256), index=True)
    action: Mapped[str] = mapped_column(String(128), index=True)
    resource_type: Mapped[str] = mapped_column(String(64), index=True)
    resource_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(256), index=True)
    title: Mapped[str] = mapped_column(String(512))
    content: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
