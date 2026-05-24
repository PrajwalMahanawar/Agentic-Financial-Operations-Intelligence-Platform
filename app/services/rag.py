from app.models.case import CaseCreate, Evidence


class EvidenceRetriever:
    def retrieve(self, case: CaseCreate) -> list[Evidence]:
        raise NotImplementedError


class LocalEvidenceRetriever(EvidenceRetriever):
    """Small deterministic retriever used until a vector store is connected."""

    policy_corpus = [
        Evidence(
            source="policy://fraud-disputes",
            title="Card dispute investigation policy",
            content=(
                "High-value card disputes require merchant checks, customer contact, "
                "velocity review, and provisional credit consideration."
            ),
            score=0.91,
        ),
        Evidence(
            source="policy://complaints",
            title="Complaint handling obligations",
            content=(
                "Complaints involving customer harm require acknowledgement, root-cause "
                "analysis, clear remediation, and auditable human sign-off."
            ),
            score=0.87,
        ),
        Evidence(
            source="signals://transaction-risk",
            title="Transaction risk indicators",
            content=(
                "Risk increases with unusual channel, high amount, repeated merchant activity, "
                "customer distress language, and metadata indicating account takeover."
            ),
            score=0.84,
        ),
    ]

    def retrieve(self, case: CaseCreate) -> list[Evidence]:
        terms = {case.case_type.value, case.channel.lower(), *case.summary.lower().split()}
        ranked = []
        for evidence in self.policy_corpus:
            haystack = f"{evidence.title} {evidence.content}".lower()
            overlap = sum(1 for term in terms if term in haystack)
            ranked.append(evidence.model_copy(update={"score": min(1.0, evidence.score + overlap * 0.02)}))
        return sorted(ranked, key=lambda item: item.score, reverse=True)
