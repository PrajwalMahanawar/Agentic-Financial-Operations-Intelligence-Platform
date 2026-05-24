import httpx
from django.conf import settings

from investigations.models import InvestigationCase


class LLMService:
    def summarize_case(self, case: InvestigationCase, findings: list[dict]) -> str:
        raise NotImplementedError


class LocalLLMService(LLMService):
    def summarize_case(self, case: InvestigationCase, findings: list[dict]) -> str:
        finding_text = "; ".join(f"{item['agent']}={item['risk_score']}" for item in findings)
        return f"Local AI summary: case risk is {case.risk_score}; findings: {finding_text}."


class OpenAICompatibleLLMService(LLMService):
    def summarize_case(self, case: InvestigationCase, findings: list[dict]) -> str:
        if not settings.OPENAI_API_KEY:
            return LocalLLMService().summarize_case(case, findings)

        response = httpx.post(
            f"{settings.OPENAI_BASE_URL.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={
                "model": settings.OPENAI_MODEL,
                "temperature": 0.1,
                "messages": [
                    {
                        "role": "user",
                        "content": (
                            "Summarize this fraud or complaint investigation for an operations "
                            f"reviewer. Case={case.id}, summary={case.summary}, findings={findings}"
                        ),
                    }
                ],
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def get_llm_service() -> LLMService:
    if settings.LLM_PROVIDER.lower() == "openai":
        return OpenAICompatibleLLMService()
    return LocalLLMService()
