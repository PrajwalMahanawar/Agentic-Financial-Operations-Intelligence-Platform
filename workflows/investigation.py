from typing import TypedDict

from django.conf import settings
from langchain_core.runnables import RunnableLambda
from langgraph.graph import END, StateGraph

from ai.llm import get_llm_service
from ai.rag import RetrievedEvidence, get_rag_retriever
from investigations.models import AgentFinding, EvidenceDocument, InvestigationCase


class InvestigationState(TypedDict):
    case: InvestigationCase
    evidence: list[RetrievedEvidence]
    findings: list[dict]


class InvestigationWorkflow:
    def __init__(self) -> None:
        self.retriever = get_rag_retriever()
        self.llm = get_llm_service()
        self.graph = self._build_graph()

    def run(self, case: InvestigationCase) -> InvestigationCase:
        case.status = InvestigationCase.Status.INVESTIGATING
        case.save(update_fields=["status", "updated_at"])
        final_state = self.graph.invoke({"case": case, "evidence": [], "findings": []})
        return final_state["case"]

    def _build_graph(self):
        graph = StateGraph(InvestigationState)
        graph.add_node("retrieve_evidence", RunnableLambda(self._retrieve_evidence))
        graph.add_node("fraud_agent", RunnableLambda(self._fraud_agent))
        graph.add_node("complaint_agent", RunnableLambda(self._complaint_agent))
        graph.add_node("decision_agent", RunnableLambda(self._decision_agent))
        graph.add_node("approval_gate", RunnableLambda(self._approval_gate))
        graph.set_entry_point("retrieve_evidence")
        graph.add_edge("retrieve_evidence", "fraud_agent")
        graph.add_edge("fraud_agent", "complaint_agent")
        graph.add_edge("complaint_agent", "decision_agent")
        graph.add_edge("decision_agent", "approval_gate")
        graph.add_edge("approval_gate", END)
        return graph.compile()

    def _retrieve_evidence(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        evidence = self.retriever.retrieve(case)
        EvidenceDocument.objects.filter(case=case).delete()
        EvidenceDocument.objects.bulk_create(
            [
                EvidenceDocument(
                    case=case,
                    source=item.source,
                    title=item.title,
                    content=item.content,
                    score=item.score,
                )
                for item in evidence
            ]
        )
        state["evidence"] = evidence
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
        if case.case_type in {InvestigationCase.CaseType.FRAUD, InvestigationCase.CaseType.MIXED}:
            risk += 15
            signals.append("fraud_case_type")
        finding = {
            "agent": "fraud_investigator",
            "risk_score": min(risk, 100),
            "summary": "Assessed transaction, channel, narrative, device, velocity, and sanctions signals.",
            "signals": signals,
            "explanation": "Fraud scoring combines rule-based indicators with retrieved policy context.",
        }
        state["findings"].append(finding)
        return state

    def _complaint_agent(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        signals = []
        risk = 5
        summary_lower = case.summary.lower()
        if case.case_type in {InvestigationCase.CaseType.COMPLAINT, InvestigationCase.CaseType.MIXED}:
            risk += 25
            signals.append("regulated_complaint")
        if any(term in summary_lower for term in ("complaint", "distress", "harm", "vulnerable")):
            risk += 25
            signals.append("potential_customer_harm")
        if case.amount >= 500:
            risk += 15
            signals.append("material_financial_impact")
        if any(item.source == "policy://complaints" for item in state["evidence"]):
            risk += 10
            signals.append("complaint_policy_match")
        finding = {
            "agent": "complaints_specialist",
            "risk_score": min(risk, 100),
            "summary": "Assessed complaint obligations, customer harm, and remediation needs.",
            "signals": signals,
            "explanation": "Complaint scoring combines regulatory markers, harm language, amount, and policy matches.",
        }
        state["findings"].append(finding)
        return state

    def _decision_agent(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        AgentFinding.objects.filter(case=case).delete()
        AgentFinding.objects.bulk_create([AgentFinding(case=case, **finding) for finding in state["findings"]])
        risk_score = max((finding["risk_score"] for finding in state["findings"]), default=0)
        signals = {signal for finding in state["findings"] for signal in finding["signals"]}
        if risk_score >= 80:
            action = InvestigationCase.Action.ESCALATE
            rationale = "Risk score is high; escalate for senior operations review."
        elif "customer_reports_unauthorized_activity" in signals:
            action = InvestigationCase.Action.APPROVE_REFUND
            rationale = "Unauthorized activity indicators support provisional remediation."
        elif risk_score < 30:
            action = InvestigationCase.Action.DENY_CLAIM
            rationale = "Available evidence does not support the claim at this stage."
        else:
            action = InvestigationCase.Action.REQUEST_MORE_INFORMATION
            rationale = "More customer or merchant evidence is needed before final disposition."
        case.risk_score = risk_score
        case.recommended_action = action
        case.requires_human_approval = risk_score >= settings.HUMAN_APPROVAL_RISK_THRESHOLD or action in {
            InvestigationCase.Action.APPROVE_REFUND,
            InvestigationCase.Action.ESCALATE,
        }
        case.recommendation_rationale = f"{rationale} {self.llm.summarize_case(case, state['findings'])}"
        case.save(
            update_fields=[
                "risk_score",
                "recommended_action",
                "requires_human_approval",
                "recommendation_rationale",
                "updated_at",
            ]
        )
        return state

    def _approval_gate(self, state: InvestigationState) -> InvestigationState:
        case = state["case"]
        case.status = (
            InvestigationCase.Status.AWAITING_APPROVAL
            if case.requires_human_approval
            else InvestigationCase.Status.CLOSED
        )
        case.save(update_fields=["status", "updated_at"])
        return state
