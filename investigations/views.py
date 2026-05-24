from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from investigations.models import ApprovalDecision, AuditLog, InvestigationCase
from investigations.serializers import (
    ApprovalRequestSerializer,
    InvestigationCaseCreateSerializer,
    InvestigationCaseSerializer,
)
from workflows.investigation import InvestigationWorkflow


@api_view(["GET"])
def health(request):
    return Response({"status": "ok"})


class InvestigationCaseViewSet(viewsets.ModelViewSet):
    queryset = InvestigationCase.objects.prefetch_related("evidence", "findings").all()
    filterset_fields = ["case_type", "status", "customer_id"]
    ordering_fields = ["created_at", "updated_at", "risk_score", "amount"]

    def get_serializer_class(self):
        if self.action == "create":
            return InvestigationCaseCreateSerializer
        return InvestigationCaseSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
            case = serializer.save(status=InvestigationCase.Status.RECEIVED)
            case = InvestigationWorkflow().run(case)
            AuditLog.objects.create(
                actor=getattr(request.user, "email", "anonymous") or "anonymous",
                action="case.created",
                resource_type="case",
                resource_id=str(case.id),
                details={"status": case.status},
            )
        return Response(InvestigationCaseSerializer(case).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def approval(self, request, pk=None):
        case = self.get_object()
        if case.status != InvestigationCase.Status.AWAITING_APPROVAL:
            return Response(
                {"detail": "Case is not awaiting approval."},
                status=status.HTTP_409_CONFLICT,
            )
        serializer = ApprovalRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        with transaction.atomic():
            ApprovalDecision.objects.update_or_create(
                case=case,
                defaults={
                    "approved": data["approved"],
                    "reviewer": data["reviewer"],
                    "notes": data["notes"],
                },
            )
            case.status = (
                InvestigationCase.Status.APPROVED
                if data["approved"]
                else InvestigationCase.Status.REJECTED
            )
            case.save(update_fields=["status", "updated_at"])
            AuditLog.objects.create(
                actor=getattr(request.user, "email", "anonymous") or "anonymous",
                action="case.approved" if data["approved"] else "case.rejected",
                resource_type="case",
                resource_id=str(case.id),
                details={"reviewer": data["reviewer"]},
            )
        return Response(InvestigationCaseSerializer(case).data)
