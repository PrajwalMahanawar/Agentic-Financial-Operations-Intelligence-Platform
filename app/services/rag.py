import hashlib
import math

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import KnowledgeDocument
from app.models.case import CaseCreate, Evidence


class EvidenceRetriever:
    def retrieve(self, case: CaseCreate) -> list[Evidence]:
        raise NotImplementedError


def embed_text(text: str, dimensions: int = 16) -> list[float]:
    vector = [0.0] * dimensions
    for word in text.lower().split():
        digest = hashlib.sha256(word.encode()).digest()
        index = digest[0] % dimensions
        vector[index] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


class LocalEvidenceRetriever(EvidenceRetriever):
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
                "customer distress language, account takeover, sanctions exposure, and device mismatch."
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


class PostgresVectorEvidenceRetriever(EvidenceRetriever):
    def __init__(self, db: Session) -> None:
        self.db = db
        self.local_fallback = LocalEvidenceRetriever()

    def retrieve(self, case: CaseCreate) -> list[Evidence]:
        query_vector = embed_text(f"{case.case_type} {case.summary} {case.channel}")
        documents = self.db.scalars(select(KnowledgeDocument)).all()
        if not documents:
            return self.local_fallback.retrieve(case)
        ranked = sorted(
            documents,
            key=lambda document: cosine_similarity(query_vector, document.embedding),
            reverse=True,
        )[:5]
        return [
            Evidence(
                source=document.source,
                title=document.title,
                content=document.content,
                score=max(0.0, min(1.0, cosine_similarity(query_vector, document.embedding))),
            )
            for document in ranked
        ]
