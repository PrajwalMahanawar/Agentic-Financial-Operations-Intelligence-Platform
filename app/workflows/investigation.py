from typing import TypedDict

from app.core.config import Settings
from app.models.case import (
    AgentFinding,
    CaseCreate,
    CaseRecord,
    CaseRecommendation,
    CaseStatus,
    CaseType,
    RecommendationAction,
)
from app.services.llm import LLMService, LocalLLMService
from app.services.rag import EvidenceRetriever

try:
    from langgraph.graph import END, StateGraph
except ImportError:  # pragma: no cover - only used before dependencies are installed
    END = None
    StateGraph = None


class InvestigationState(TypedDict):
    case: CaseRecord


class InvestigationWorkflow:
    def __init__(
        self,
        retriever: EvidenceRetriever,
        settings: Settings,
        llm_service: LLMService | None = None,
    ) -> None:
        self.retriever = retriever
        self.settings = settings
        self.llm_service = llm_service or LocalLLMService()
        self.graph = self._build_graph()

    def run(self, case_request: CaseCreate) -> CaseRecord:
        case = CaseRecord(**case_request.model_dump(), status=CaseStatus.investigating)
        state: InvestigationState = {"case": case}

        if self.graph is not None:
            return self.graph.invoke(state)["case"]

        for step in (
            self._retrieve_evidence,
            self._fraud_agent,
            self._complaint_agent,
            self._decision_agent,
            self._approval_gate,
        ):
            state = step(state)

        return state["case"]

    def _build_graph(self):
        if StateGraph is None or END is None:
            return None

        graph = StateGraph(InvestigationState)
        graph.add_node("retrieve_evidence", self._retrieve_evidence)
        graph.add_node("fraud_agent", self._fraud_agent)
        graph.add_node("complaint_agent", self._complaint_agent)
        graph.add_node("decision_agent", self._decision_agent)
        graph.add_node("approval_gate", self._approval_gate)

        graph.set_entry_point("retrieve_evidence")
        graph.add_edge("retrieve_evidence", "fraud_agent")
        graph.add_edge("fraud_agent", "complaint_agent")
        graph.add_edge("complaint_agent", "decision_agent")
        graph.add_edge("decision_agent", "approval_gate")
        graph.add_edge("approval_gate", END)
        return graph.compile()

    def _retrieve_evidence(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        case.evidence = self.retriever.retrieve(
            CaseCreate(
                customer_id=case.customer_id,
                case_type=case.case_type,
                summary=case.summary,
                amount=case.amount,
                currency=case.currency,
                channel=case.channel,
                metadata=case.metadata,
            )
        )
        return state

    def _fraud_agent(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        signals = []
        risk = 10

        if case.amount >= 1000:
            risk += 35
            signals.append("high_value_transaction")
        elif case.amount >= 250:
            risk += 20
            signals.append("medium_value_transaction")

        summary_lower = case.summary.lower()
        if any(term in summary_lower for term in ("unauthorized", "stolen", "takeover", "dispute")):
            risk += 30
            signals.append("customer_reports_unauthorized_activity")

        if case.channel.lower() in {"mobile", "web", "api"}:
            risk += 10
            signals.append("digital_channel")

        if case.metadata.get("device_mismatch") is True:
            risk += 20
            signals.append("device_mismatch")

        if case.metadata.get("velocity_24h", 0) >= 5:
            risk += 20
            signals.append("high_transaction_velocity")

        if case.metadata.get("sanctions_hit") is True:
            risk += 30
            signals.append("sanctions_screening_hit")

        if case.case_type in {CaseType.fraud, CaseType.mixed}:
            risk += 15
            signals.append("fraud_case_type")

        case.findings.append(
            AgentFinding(
                agent="fraud_investigator",
                risk_score=min(risk, 100),
                summary="Assessed transaction, customer narrative, device, velocity, and sanctions indicators.",
                signals=signals,
                explanation="Fraud risk combines amount, channel, narrative, device, velocity, and sanctions signals.",
            )
        )
        return state

    def _complaint_agent(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        signals = []
        risk = 5
        summary_lower = case.summary.lower()

        if case.case_type in {CaseType.complaint, CaseType.mixed}:
            risk += 25
            signals.append("regulated_complaint")

        if any(term in summary_lower for term in ("complaint", "distress", "harm", "vulnerable")):
            risk += 25
            signals.append("potential_customer_harm")

        if case.amount >= 500:
            risk += 15
            signals.append("material_financial_impact")

        if any(evidence.source == "policy://complaints" for evidence in case.evidence):
            risk += 10
            signals.append("complaint_policy_match")

        case.findings.append(
            AgentFinding(
                agent="complaints_specialist",
                risk_score=min(risk, 100),
                summary="Assessed complaint obligations, harm indicators, and remediation needs.",
                signals=signals,
                explanation="Complaint risk combines regulated complaint markers, customer harm, amount, and policy matches.",
            )
        )
        return state

    def _decision_agent(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        risk_score = max((finding.risk_score for finding in case.findings), default=0)
        signals = {signal for finding in case.findings for signal in finding.signals}

        if risk_score >= 80:
            action = RecommendationAction.escalate
            rationale = "Risk score is high; escalate for senior operations review."
        elif "customer_reports_unauthorized_activity" in signals:
            action = RecommendationAction.approve_refund
            rationale = "Unauthorized activity indicators support provisional customer remediation."
        elif risk_score < 30:
            action = RecommendationAction.deny_claim
            rationale = "Available evidence does not support the claim at this stage."
        else:
            action = RecommendationAction.request_more_information
            rationale = "More customer or merchant evidence is needed before final disposition."

        case.recommendation = CaseRecommendation(
            action=action,
            risk_score=risk_score,
            rationale=f"{rationale} {self.llm_service.summarize_case(case)}",
            requires_human_approval=risk_score >= self.settings.human_approval_risk_threshold
            or action in {RecommendationAction.approve_refund, RecommendationAction.escalate},
        )
        return state

    def _approval_gate(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        if case.recommendation and case.recommendation.requires_human_approval:
            case.status = CaseStatus.awaiting_approval
        else:
            case.status = CaseStatus.closed
        return state
