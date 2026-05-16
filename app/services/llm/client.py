from __future__ import annotations

import json
import logging
from urllib import error, request

from app.core.config import Settings
from app.services.llm.fake import FakeMonthlySummaryLLM
from app.services.llm.schemas import MonthlySummaryInput


logger = logging.getLogger(__name__)

MONTHLY_SUMMARY_PROMPT = """You are generating a neutral monthly spending summary for Tally.
Tally is not a financial advisor.
Do not provide financial advice.
Do not tell the user what they should do.
Do not recommend investments, loans, credit products, debt actions, or cancellation decisions.
Use only the provided aggregated data.
Do not infer facts not present in the data.
Keep tone calm, neutral, and helpful.
Mention that the summary is based on imported transactions.
Keep it concise."""


class OpenAIMonthlySummaryLLM:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate_monthly_summary(self, summary_input: MonthlySummaryInput) -> str:
        payload = {
            "model": self.model,
            "input": [
                {"role": "system", "content": MONTHLY_SUMMARY_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(
                        summary_input.model_dump(mode="json"),
                        sort_keys=True,
                    ),
                },
            ],
            "max_output_tokens": 220,
        }
        encoded_payload = json.dumps(payload).encode("utf-8")
        api_request = request.Request(
            "https://api.openai.com/v1/responses",
            data=encoded_payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(api_request, timeout=20) as response:
                body = json.loads(response.read().decode("utf-8"))
        except (TimeoutError, error.URLError, error.HTTPError, json.JSONDecodeError) as exc:
            logger.info("Monthly report LLM provider unavailable", extra={"provider": "openai"})
            raise RuntimeError("LLM provider unavailable.") from exc

        text = self._extract_text(body)
        if not text:
            raise RuntimeError("LLM provider returned an empty response.")
        return text

    def _extract_text(self, body: dict) -> str:
        if isinstance(body.get("output_text"), str):
            return body["output_text"].strip()
        output = body.get("output")
        if not isinstance(output, list):
            return ""
        chunks: list[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            for content in item.get("content", []):
                if isinstance(content, dict) and content.get("type") in {"output_text", "text"}:
                    text = content.get("text")
                    if isinstance(text, str):
                        chunks.append(text)
        return " ".join(chunks).strip()


def build_monthly_summary_llm(settings: Settings):
    if not settings.llm_enabled:
        return None
    if settings.llm_provider == "fake":
        return FakeMonthlySummaryLLM()
    if settings.llm_provider == "openai" and settings.llm_api_key is not None:
        return OpenAIMonthlySummaryLLM(
            api_key=settings.llm_api_key.get_secret_value(),
            model=settings.llm_model,
        )
    return None
