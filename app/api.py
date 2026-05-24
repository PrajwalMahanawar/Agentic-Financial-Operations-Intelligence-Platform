from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from app.core.auth import User, authenticate, create_access_token, get_current_user, require_roles
from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.case import (
    ApprovalRequest,
    AuditRecord,
    CaseCreate,
    CaseRecord,
    LoginRequest,
    TokenResponse,
)
from app.services.approvals import ApprovalService
from app.services.audit import AuditService
from app.services.llm import get_llm_service
from app.services.rag import LocalEvidenceRetriever, PostgresVectorEvidenceRetriever
from app.services.repository import CaseRepository, InMemoryCaseRepository, SqlAlchemyCaseRepository
from app.workflows.investigation import InvestigationWorkflow

router = APIRouter()
memory_repository = InMemoryCaseRepository()
memory_audit = AuditService()


def get_repository(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> CaseRepository:
    if settings.enable_database:
        return SqlAlchemyCaseRepository(db)
    return memory_repository


def get_audit_service(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> AuditService:
    if settings.enable_database:
        return AuditService(db)
    return memory_audit


def get_workflow(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> InvestigationWorkflow:
    retriever = (
        PostgresVectorEvidenceRetriever(db)
        if settings.enable_database and settings.rag_backend.lower() == "postgres"
        else LocalEvidenceRetriever()
    )
    return InvestigationWorkflow(retriever, settings, get_llm_service(settings))


def audit(
    service: AuditService,
    user: User,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    details: dict | None = None,
) -> None:
    service.record(
        AuditRecord(
            actor=user.email,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details or {},
        )
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/auth/token", response_model=TokenResponse)
def login(request: LoginRequest, settings: Settings = Depends(get_settings)) -> TokenResponse:
    user = authenticate(request.email, request.password, settings)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials.")
    return TokenResponse(
        access_token=create_access_token(user, settings),
        expires_in=settings.auth_token_ttl_seconds,
        role=user.role,
    )


@router.post("/cases", response_model=CaseRecord, status_code=status.HTTP_201_CREATED)
def create_case(
    request: CaseCreate,
    repository: CaseRepository = Depends(get_repository),
    workflow: InvestigationWorkflow = Depends(get_workflow),
    audit_service: AuditService = Depends(get_audit_service),
    user: User = Depends(require_roles("admin", "analyst")),
) -> CaseRecord:
    case = repository.save(workflow.run(request))
    audit(audit_service, user, "case.created", "case", case.id, {"status": case.status.value})
    return case


@router.get("/cases", response_model=list[CaseRecord])
def list_cases(
    repository: CaseRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
    user: User = Depends(require_roles("admin", "analyst", "approver")),
) -> list[CaseRecord]:
    cases = repository.list_recent()
    audit(audit_service, user, "case.listed", "case", details={"count": len(cases)})
    return cases


@router.get("/cases/{case_id}", response_model=CaseRecord)
def get_case(
    case_id: str,
    repository: CaseRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
    user: User = Depends(require_roles("admin", "analyst", "approver")),
) -> CaseRecord:
    case = repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    audit(audit_service, user, "case.viewed", "case", case.id)
    return case


@router.post("/cases/{case_id}/approval", response_model=CaseRecord)
def approve_case(
    case_id: str,
    request: ApprovalRequest,
    repository: CaseRepository = Depends(get_repository),
    audit_service: AuditService = Depends(get_audit_service),
    user: User = Depends(require_roles("admin", "approver")),
) -> CaseRecord:
    case = repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    try:
        approved_case = ApprovalService().apply(case, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    saved = repository.save(approved_case)
    audit(
        audit_service,
        user,
        "case.approved" if request.approved else "case.rejected",
        "case",
        case.id,
        {"reviewer": request.reviewer},
    )
    return saved


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard(
    request: Request,
    repository: CaseRepository = Depends(get_repository),
    user: User = Depends(get_current_user),
) -> HTMLResponse:
    cases = repository.list_recent(50)
    rows = "".join(
        f"<tr><td>{case.id[:8]}</td><td>{case.case_type}</td><td>{case.status}</td>"
        f"<td>{case.amount:.2f} {case.currency}</td>"
        f"<td>{case.recommendation.risk_score if case.recommendation else '-'}</td>"
        f"<td>{case.recommendation.action if case.recommendation else '-'}</td></tr>"
        for case in cases
    )
    return HTMLResponse(
        """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Financial Ops Dashboard</title>
  <style>
    body { font-family: Inter, system-ui, sans-serif; margin: 0; background: #f7f8fa; color: #18202a; }
    header { padding: 24px 32px; background: #102033; color: white; }
    main { padding: 24px 32px; }
    table { width: 100%; border-collapse: collapse; background: white; border: 1px solid #dde3ea; }
    th, td { text-align: left; padding: 12px 14px; border-bottom: 1px solid #edf0f4; }
    th { font-size: 12px; text-transform: uppercase; color: #536172; }
  </style>
</head>
<body>
  <header><h1>Financial Operations Intelligence</h1><p>Signed in as: USER</p></header>
  <main><table><thead><tr><th>Case</th><th>Type</th><th>Status</th><th>Amount</th><th>Risk</th><th>Action</th></tr></thead><tbody>ROWS</tbody></table></main>
</body>
</html>""".replace("USER", user.email).replace("ROWS", rows or "<tr><td colspan='6'>No cases yet.</td></tr>")
    )
