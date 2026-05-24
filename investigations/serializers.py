from rest_framework import serializers

from investigations.models import AgentFinding, ApprovalDecision, EvidenceDocument, InvestigationCase


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = EvidenceDocument
        fields = ["source", "title", "content", "score"]


class AgentFindingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AgentFinding
        fields = ["agent", "risk_score", "summary", "signals", "explanation"]


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalDecision
        fields = ["approved", "reviewer", "notes", "decided_at"]
        read_only_fields = ["decided_at"]


class InvestigationCaseCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = InvestigationCase
        fields = ["customer_id", "case_type", "summary", "amount", "currency", "channel", "metadata"]


class InvestigationCaseSerializer(serializers.ModelSerializer):
    evidence = EvidenceSerializer(many=True, read_only=True)
    findings = AgentFindingSerializer(many=True, read_only=True)
    approval = ApprovalDecisionSerializer(read_only=True)

    class Meta:
        model = InvestigationCase
        fields = [
            "id",
            "customer_id",
            "case_type",
            "summary",
            "amount",
            "currency",
            "channel",
            "status",
            "metadata",
            "risk_score",
            "recommended_action",
            "recommendation_rationale",
            "requires_human_approval",
            "evidence",
            "findings",
            "approval",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApprovalRequestSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    reviewer = serializers.CharField(min_length=3, max_length=256)
    notes = serializers.CharField(min_length=3)
