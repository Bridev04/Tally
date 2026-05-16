from app.services.llm.schemas import MonthlySummaryInput


class FakeMonthlySummaryLLM:
    def generate_monthly_summary(self, summary_input: MonthlySummaryInput) -> str:
        category_names = [item.category.replace("_", " ") for item in summary_input.top_categories[:3]]
        categories = ", ".join(category_names) if category_names else "no expense categories"
        return (
            f"Based on your imported transactions for {summary_input.month}, this month's spending activity shows "
            f"{summary_input.transaction_count} transactions and total expenses of "
            f"{summary_input.currency} {summary_input.total_expenses:,.2f}. The largest categories were {categories}. "
            f"Several recurring payments were detected: {summary_input.recurring_payment_count}. "
            f"Some transactions may be worth reviewing: {summary_input.needs_review_count}."
        )
