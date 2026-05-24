from django.contrib import admin

from investigations.models import (
    AgentFinding,
    ApprovalDecision,
    AuditLog,
    EvidenceDocument,
    InvestigationCase,
    KnowledgeDocument,
)


admin.site.register(InvestigationCase)
admin.site.register(EvidenceDocument)
admin.site.register(AgentFinding)
admin.site.register(ApprovalDecision)
admin.site.register(KnowledgeDocument)
admin.site.register(AuditLog)
