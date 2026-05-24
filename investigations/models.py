import uuid

from django.db import models


class InvestigationCase(models.Model):
    class CaseType(models.TextChoices):
        FRAUD = "fraud", "Fraud"
        COMPLAINT = "complaint", "Complaint"
        MIXED = "mixed", "Mixed"

    class Status(models.TextChoices):
        RECEIVED = "received", "Received"
        INVESTIGATING = "investigating", "Investigating"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CLOSED = "closed", "Closed"

    class Action(models.TextChoices):
        APPROVE_REFUND = "approve_refund", "Approve Refund"
        DENY_CLAIM = "deny_claim", "Deny Claim"
        ESCALATE = "escalate", "Escalate"
        REQUEST_MORE_INFORMATION = "request_more_information", "Request More Information"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer_id = models.CharField(max_length=128, db_index=True)
    case_type = models.CharField(max_length=32, choices=CaseType.choices, db_index=True)
    summary = models.TextField()
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    currency = models.CharField(max_length=3, default="USD")
    channel = models.CharField(max_length=64, default="unknown")
    status = models.CharField(max_length=32, choices=Status.choices, default=Status.RECEIVED, db_index=True)
    metadata = models.JSONField(default=dict, blank=True)
    risk_score = models.PositiveSmallIntegerField(default=0)
    recommended_action = models.CharField(max_length=64, choices=Action.choices, blank=True)
    recommendation_rationale = models.TextField(blank=True)
    requires_human_approval = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]

    def __str__(self) -> str:
        return f"{self.case_type}:{self.customer_id}:{self.status}"


class EvidenceDocument(models.Model):
    case = models.ForeignKey(InvestigationCase, related_name="evidence", on_delete=models.CASCADE)
    source = models.CharField(max_length=256)
    title = models.CharField(max_length=512)
    content = models.TextField()
    score = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-score", "title"]


class AgentFinding(models.Model):
    case = models.ForeignKey(InvestigationCase, related_name="findings", on_delete=models.CASCADE)
    agent = models.CharField(max_length=128)
    risk_score = models.PositiveSmallIntegerField(default=0)
    summary = models.TextField()
    signals = models.JSONField(default=list, blank=True)
    explanation = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class ApprovalDecision(models.Model):
    case = models.OneToOneField(InvestigationCase, related_name="approval", on_delete=models.CASCADE)
    approved = models.BooleanField()
    reviewer = models.CharField(max_length=256)
    notes = models.TextField()
    decided_at = models.DateTimeField(auto_now_add=True)


class KnowledgeDocument(models.Model):
    source = models.CharField(max_length=256, db_index=True)
    title = models.CharField(max_length=512)
    content = models.TextField()
    embedding = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["source"])]


class AuditLog(models.Model):
    actor = models.CharField(max_length=256, default="system", db_index=True)
    action = models.CharField(max_length=128, db_index=True)
    resource_type = models.CharField(max_length=64, db_index=True)
    resource_id = models.CharField(max_length=128, blank=True, db_index=True)
    details = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
