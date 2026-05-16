from typing import Protocol

from app.services.llm.schemas import MonthlySummaryInput


class MonthlySummaryLLM(Protocol):
    def generate_monthly_summary(self, summary_input: MonthlySummaryInput) -> str:
        """Return neutral prose based only on aggregated monthly report facts."""
