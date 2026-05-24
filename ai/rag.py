import hashlib
import math
from dataclasses import dataclass
from decimal import Decimal

from investigations.models import InvestigationCase, KnowledgeDocument


@dataclass(frozen=True)
class RetrievedEvidence:
    source: str
    title: str
    content: str
    score: float


def embed_text(text: str, dimensions: int = 16) -> list[float]:
    vector = [0.0] * dimensions
    for word in text.lower().split():
        digest = hashlib.sha256(word.encode()).digest()
        vector[digest[0] % dimensions] += 1.0
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def cosine_similarity(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=False))


class LocalRAGRetriever:
    corpus = [
        RetrievedEvidence(
            source="policy://fraud-disputes",
            title="Card dispute investigation policy",
            content="High-value disputes require merchant checks, customer contact, velocity review, and provisional credit consideration.",
            score=0.91,
        ),
        RetrievedEvidence(
            source="policy://complaints",
            title="Complaint handling obligations",
            content="Complaints involving customer harm require acknowledgement, root-cause analysis, remediation, and auditable sign-off.",
            score=0.88,
        ),
        RetrievedEvidence(
            source="signals://transaction-risk",
            title="Transaction risk indicators",
            content="Risk increases with unusual channel, high amount, repeated merchant activity, device mismatch, and account takeover signals.",
            score=0.84,
        ),
    ]

    def retrieve(self, case: InvestigationCase) -> list[RetrievedEvidence]:
        terms = {case.case_type, case.channel.lower(), *case.summary.lower().split()}
        ranked = []
        for item in self.corpus:
            haystack = f"{item.title} {item.content}".lower()
            overlap = sum(1 for term in terms if term in haystack)
            ranked.append(
                RetrievedEvidence(item.source, item.title, item.content, min(1.0, item.score + overlap * 0.02))
            )
        return sorted(ranked, key=lambda item: item.score, reverse=True)


class PostgresVectorRAGRetriever:
    def __init__(self) -> None:
        self.fallback = LocalRAGRetriever()

    def retrieve(self, case: InvestigationCase) -> list[RetrievedEvidence]:
        documents = list(KnowledgeDocument.objects.all())
        if not documents:
            return self.fallback.retrieve(case)
        query = embed_text(f"{case.case_type} {case.summary} {case.channel} {Decimal(case.amount)}")
        ranked = sorted(
            documents,
            key=lambda document: cosine_similarity(query, document.embedding or []),
            reverse=True,
        )[:5]
        return [
            RetrievedEvidence(
                source=document.source,
                title=document.title,
                content=document.content,
                score=max(0.0, min(1.0, cosine_similarity(query, document.embedding or []))),
            )
            for document in ranked
        ]


def get_rag_retriever():
    return PostgresVectorRAGRetriever()
