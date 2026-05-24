from app.models.case import ApprovalRecord, ApprovalRequest, CaseRecord, CaseStatus


class ApprovalService:
    def apply(self, case: CaseRecord, request: ApprovalRequest) -> CaseRecord:
        if case.status != CaseStatus.awaiting_approval:
            raise ValueError("Case is not awaiting approval.")

        case.approval = ApprovalRecord(
            approved=request.approved,
            reviewer=request.reviewer,
            notes=request.notes,
        )
        case.status = CaseStatus.approved if request.approved else CaseStatus.rejected
        return case
