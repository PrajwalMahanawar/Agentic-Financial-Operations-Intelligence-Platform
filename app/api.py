from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.db.session import get_db
from app.models.case import ApprovalRequest, CaseCreate, CaseRecord
from app.services.approvals import ApprovalService
from app.services.rag import LocalEvidenceRetriever
from app.services.repository import CaseRepository, InMemoryCaseRepository, SqlAlchemyCaseRepository
from app.workflows.investigation import InvestigationWorkflow

router = APIRouter()
memory_repository = InMemoryCaseRepository()


def get_repository(
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
) -> CaseRepository:
    if settings.enable_database:
        return SqlAlchemyCaseRepository(db)
    return memory_repository


def get_workflow(settings: Settings = Depends(get_settings)) -> InvestigationWorkflow:
    return InvestigationWorkflow(LocalEvidenceRetriever(), settings)


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/cases", response_model=CaseRecord, status_code=status.HTTP_201_CREATED)
def create_case(
    request: CaseCreate,
    repository: CaseRepository = Depends(get_repository),
    workflow: InvestigationWorkflow = Depends(get_workflow),
) -> CaseRecord:
    case = workflow.run(request)
    return repository.save(case)


@router.get("/cases/{case_id}", response_model=CaseRecord)
def get_case(
    case_id: str,
    repository: CaseRepository = Depends(get_repository),
) -> CaseRecord:
    case = repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return case


@router.post("/cases/{case_id}/approval", response_model=CaseRecord)
def approve_case(
    case_id: str,
    request: ApprovalRequest,
    repository: CaseRepository = Depends(get_repository),
) -> CaseRecord:
    case = repository.get(case_id)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")

    try:
        approved_case = ApprovalService().apply(case, request)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    return repository.save(approved_case)
