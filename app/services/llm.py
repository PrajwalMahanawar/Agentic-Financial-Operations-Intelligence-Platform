import httpx

from app.core.config import Settings
from app.models.case import CaseRecord


class LLMService:
    def summarize_case(self, case: CaseRecord) -> str:
        raise NotImplementedError


class LocalLLMService(LLMService):
    def summarize_case(self, case: CaseRecord) -> str:
        finding_text = "; ".join(f"{f.agent}: {f.risk_score}" for f in case.findings)
        action = case.recommendation.action if case.recommendation else "pending"
        return f"Case {case.id} has recommendation {action} with findings [{finding_text}]."


class OpenAICompatibleLLMService(LLMService):
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def summarize_case(self, case: CaseRecord) -> str:
        if not self.settings.openai_api_key:
            return LocalLLMService().summarize_case(case)
        prompt = (
            "Summarize this financial operations investigation for a human approver. "
            "Be concise, include risk, rationale, and required next action.\n"
            f"{case.model_dump(mode='json')}"
        )
        response = httpx.post(
            f"{self.settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
            json={
                "model": self.settings.openai_model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
            },
            timeout=20,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def get_llm_service(settings: Settings) -> LLMService:
    if settings.llm_provider.lower() == "openai":
        return OpenAICompatibleLLMService(settings)
    return LocalLLMService()
