from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field


class CaseType(StrEnum):
    fraud = "fraud"
    complaint = "complaint"
    mixed = "mixed"


class CaseStatus(StrEnum):
    received = "received"
    investigating = "investigating"
    awaiting_approval = "awaiting_approval"
    approved = "approved"
    rejected = "rejected"
    closed = "closed"


class RecommendationAction(StrEnum):
    approve_refund = "approve_refund"
    deny_claim = "deny_claim"
    escalate = "escalate"
    request_more_information = "request_more_information"


class CaseCreate(BaseModel):
    customer_id: str = Field(min_length=1)
    case_type: CaseType
    summary: str = Field(min_length=10)
    amount: float = Field(ge=0)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    channel: str = Field(default="unknown")
    metadata: dict[str, Any] = Field(default_factory=dict)


class Evidence(BaseModel):
    source: str
    title: str
    content: str
    score: float = Field(ge=0, le=1)


class AgentFinding(BaseModel):
    agent: str
    risk_score: int = Field(ge=0, le=100)
    summary: str
    signals: list[str] = Field(default_factory=list)


class CaseRecommendation(BaseModel):
    action: RecommendationAction
    risk_score: int = Field(ge=0, le=100)
    rationale: str
    requires_human_approval: bool


class CaseRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    customer_id: str
    case_type: CaseType
    summary: str
    amount: float
    currency: str
    channel: str
    status: CaseStatus = CaseStatus.received
    metadata: dict[str, Any] = Field(default_factory=dict)
    evidence: list[Evidence] = Field(default_factory=list)
    findings: list[AgentFinding] = Field(default_factory=list)
    recommendation: CaseRecommendation | None = None
    approval: "ApprovalRecord | None" = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ApprovalRequest(BaseModel):
    approved: bool
    reviewer: str = Field(min_length=3)
    notes: str = Field(min_length=3)


class ApprovalRecord(BaseModel):
    approved: bool
    reviewer: str
    notes: str
    decided_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


CaseRecord.model_rebuild()
