from dataclasses import dataclass, field
import re
import uuid
from collections import Counter

from sqlmodel import Session, select

from app.models import Transaction
from app.schemas.transaction import TransactionCategory
from app.services.audit import create_audit_log


@dataclass(frozen=True)
class CategorizationResult:
    category: str
    confidence: float
    reason: str
    matched_rule: str | None
    merchant_normalized: str | None


@dataclass
class CategorizationSummary:
    processed: int = 0
    updated: int = 0
    skipped_manual: int = 0
    needs_review: int = 0
    categories: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class KeywordRule:
    category: str
    strong: tuple[str, ...]
    weak: tuple[str, ...] = ()


whitespace_pattern = re.compile(r"\s+")
punctuation_pattern = re.compile(r"[^a-z0-9 ]+")

payment_prefixes = (
    "paypal",
    "visa",
    "mastercard",
    "mc",
    "debit",
    "credit",
    "pos",
    "purchase",
    "payment",
)

merchant_aliases = {
    "netflix com": "netflix",
    "netflix": "netflix",
    "spotify pte ltd": "spotify",
    "spotify": "spotify",
    "grab trip": "grab",
    "grab ride": "grab",
    "grab": "grab",
    "uber trip": "uber",
    "uber": "uber",
    "mcdo": "mcdonalds",
    "mcdonald s": "mcdonalds",
    "mcdonalds": "mcdonalds",
    "apple com bill": "apple",
    "apple bill": "apple",
    "google youtube": "youtube",
    "youtube premium": "youtube premium",
    "canva": "canva",
    "paypal canva": "canva",
    "jollibee": "jollibee",
    "starbucks": "starbucks",
}

exact_merchant_categories = {
    "netflix": TransactionCategory.subscriptions.value,
    "spotify": TransactionCategory.subscriptions.value,
    "canva": TransactionCategory.subscriptions.value,
    "youtube premium": TransactionCategory.subscriptions.value,
    "icloud": TransactionCategory.subscriptions.value,
    "google one": TransactionCategory.subscriptions.value,
    "notion": TransactionCategory.subscriptions.value,
    "figma": TransactionCategory.subscriptions.value,
    "adobe": TransactionCategory.subscriptions.value,
    "grab": TransactionCategory.transportation.value,
    "uber": TransactionCategory.transportation.value,
    "mcdonalds": TransactionCategory.food.value,
    "jollibee": TransactionCategory.food.value,
    "starbucks": TransactionCategory.food.value,
    "kfc": TransactionCategory.food.value,
    "chowking": TransactionCategory.food.value,
    "mang inasal": TransactionCategory.food.value,
    "meralco": TransactionCategory.utilities.value,
    "maynilad": TransactionCategory.utilities.value,
    "globe": TransactionCategory.utilities.value,
    "smart": TransactionCategory.utilities.value,
    "pldt": TransactionCategory.utilities.value,
    "converge": TransactionCategory.utilities.value,
    "shopee": TransactionCategory.shopping.value,
    "lazada": TransactionCategory.shopping.value,
    "uniqlo": TransactionCategory.shopping.value,
    "steam": TransactionCategory.entertainment.value,
    "playstation": TransactionCategory.entertainment.value,
    "xbox": TransactionCategory.entertainment.value,
    "mercury drug": TransactionCategory.health.value,
    "watsons": TransactionCategory.health.value,
    "udemy": TransactionCategory.education.value,
    "coursera": TransactionCategory.education.value,
}

keyword_rules = (
    KeywordRule(
        TransactionCategory.subscriptions.value,
        (
            "netflix",
            "spotify",
            "canva",
            "icloud",
            "apple icloud",
            "google one",
            "disney",
            "youtube premium",
            "notion",
            "figma",
            "adobe",
            "microsoft 365",
        ),
        ("subscription",),
    ),
    KeywordRule(
        TransactionCategory.transportation.value,
        ("grab", "uber", "mrt", "lrt", "jeepney", "toll", "parking", "fuel", "gas station"),
        ("taxi", "transport"),
    ),
    KeywordRule(
        TransactionCategory.food.value,
        (
            "mcdonald",
            "mcdonalds",
            "jollibee",
            "starbucks",
            "kfc",
            "chowking",
            "mang inasal",
            "foodpanda",
            "grabfood",
        ),
        ("restaurant", "cafe", "coffee"),
    ),
    KeywordRule(
        TransactionCategory.income.value,
        ("salary", "payroll", "payslip", "compensation", "deposit salary"),
    ),
    KeywordRule(
        TransactionCategory.fees.value,
        ("bank fee", "service charge", "transaction fee", "annual fee", "late fee", "convenience fee"),
        ("fee", "charge"),
    ),
    KeywordRule(
        TransactionCategory.utilities.value,
        (
            "meralco",
            "maynilad",
            "water bill",
            "electricity",
            "internet",
            "globe",
            "smart",
            "pldt",
            "converge",
        ),
        ("electric bill",),
    ),
    KeywordRule(
        TransactionCategory.shopping.value,
        ("shopee", "lazada", "uniqlo", "department store", "online shopping"),
        ("mall",),
    ),
    KeywordRule(
        TransactionCategory.entertainment.value,
        ("cinema", "movie", "steam", "playstation", "xbox", "concert", "arcade"),
    ),
    KeywordRule(
        TransactionCategory.health.value,
        ("pharmacy", "mercury drug", "watsons", "hospital", "clinic", "doctor", "dental"),
    ),
    KeywordRule(
        TransactionCategory.education.value,
        ("tuition", "school", "university", "course", "udemy", "coursera"),
    ),
    KeywordRule(
        TransactionCategory.rent.value,
        ("rent", "apartment", "condo rent", "lease"),
    ),
    KeywordRule(
        TransactionCategory.transfer.value,
        ("gcash transfer", "bank transfer", "fund transfer"),
        ("transfer",),
    ),
)


class TransactionCategorizerService:
    low_confidence_threshold = 0.50

    @classmethod
    def normalize_merchant(cls, raw_merchant: str | None, description: str | None = None) -> str:
        source = raw_merchant or description or ""
        cleaned = punctuation_pattern.sub(" ", source.lower().strip())
        cleaned = whitespace_pattern.sub(" ", cleaned).strip()
        if not cleaned:
            return ""

        cleaned = merchant_aliases.get(cleaned, cleaned)
        tokens = cleaned.split()
        while len(tokens) > 1 and tokens[0] in payment_prefixes:
            tokens = tokens[1:]
        cleaned = " ".join(tokens)

        for alias, canonical in merchant_aliases.items():
            if cleaned == alias or cleaned.startswith(f"{alias} ") or cleaned.endswith(f" {alias}"):
                return canonical
        for canonical in exact_merchant_categories:
            if cleaned == canonical or cleaned.startswith(f"{canonical} ") or cleaned.endswith(f" {canonical}"):
                return canonical
        return cleaned

    def categorize_transaction(self, transaction: Transaction) -> CategorizationResult:
        return self.categorize_values(
            merchant_raw=transaction.merchant_raw,
            merchant_normalized=transaction.merchant_normalized,
            description=transaction.description,
        )

    def categorize_values(
        self,
        *,
        merchant_raw: str | None,
        merchant_normalized: str | None = None,
        description: str | None = None,
    ) -> CategorizationResult:
        normalized_merchant = self.normalize_merchant(merchant_normalized or merchant_raw, description)
        normalized_description = self._normalize_text(description)

        exact_category = exact_merchant_categories.get(normalized_merchant)
        if exact_category is not None:
            return CategorizationResult(
                category=exact_category,
                confidence=0.95,
                reason=f"Exact canonical merchant match: {normalized_merchant}.",
                matched_rule=f"merchant.exact.{normalized_merchant}",
                merchant_normalized=normalized_merchant,
            )

        for rule in keyword_rules:
            merchant_match = self._first_match(normalized_merchant, rule.strong)
            if merchant_match is not None:
                return self._result(
                    category=rule.category,
                    confidence=0.85,
                    reason=f"Strong merchant keyword match: {merchant_match}.",
                    matched_rule=f"merchant.strong.{rule.category}.{merchant_match}",
                    merchant_normalized=normalized_merchant,
                )

        for rule in keyword_rules:
            description_match = self._first_match(normalized_description, rule.strong)
            if description_match is not None:
                return self._result(
                    category=rule.category,
                    confidence=0.75,
                    reason=f"Strong description keyword match: {description_match}.",
                    matched_rule=f"description.strong.{rule.category}.{description_match}",
                    merchant_normalized=normalized_merchant,
                )

        for rule in keyword_rules:
            merchant_match = self._first_match(normalized_merchant, rule.weak)
            if merchant_match is not None:
                return self._result(
                    category=rule.category,
                    confidence=0.60,
                    reason=f"Weak merchant keyword match: {merchant_match}.",
                    matched_rule=f"merchant.weak.{rule.category}.{merchant_match}",
                    merchant_normalized=normalized_merchant,
                )
            description_match = self._first_match(normalized_description, rule.weak)
            if description_match is not None:
                return self._result(
                    category=rule.category,
                    confidence=0.60,
                    reason=f"Weak description keyword match: {description_match}.",
                    matched_rule=f"description.weak.{rule.category}.{description_match}",
                    merchant_normalized=normalized_merchant,
                )

        return CategorizationResult(
            category=TransactionCategory.needs_review.value,
            confidence=0.20,
            reason="No deterministic merchant or description rule matched.",
            matched_rule=None,
            merchant_normalized=normalized_merchant or None,
        )

    def categorize_user_transactions(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        force: bool = False,
        overwrite_manual: bool = False,
        transaction_ids: list[uuid.UUID] | None = None,
    ) -> CategorizationSummary:
        statement = select(Transaction).where(Transaction.user_id == user_id)
        if transaction_ids is not None:
            statement = statement.where(Transaction.id.in_(transaction_ids))
        transactions = session.exec(statement).all()
        return self.categorize_transactions(
            session=session,
            user_id=user_id,
            transactions=transactions,
            force=force,
            overwrite_manual=overwrite_manual,
        )

    def categorize_transactions(
        self,
        *,
        session: Session,
        user_id: uuid.UUID,
        transactions: list[Transaction],
        force: bool = False,
        overwrite_manual: bool = False,
    ) -> CategorizationSummary:
        counts: Counter[str] = Counter()
        summary = CategorizationSummary()

        for transaction in transactions:
            if self._is_manual(transaction) and not overwrite_manual:
                summary.skipped_manual += 1
                continue
            if not force and not self._should_categorize(transaction):
                continue

            summary.processed += 1
            old_category = transaction.category
            result = self.categorize_transaction(transaction)
            changed = self.apply_result(transaction=transaction, result=result, source="auto")
            counts[transaction.category or TransactionCategory.needs_review.value] += 1
            if transaction.category == TransactionCategory.needs_review.value:
                summary.needs_review += 1

            if changed:
                summary.updated += 1
                session.add(transaction)
                create_audit_log(
                    session=session,
                    user_id=user_id,
                    action="transaction.categorized",
                    metadata={
                        "transaction_id": str(transaction.id),
                        "old_category": old_category,
                        "new_category": transaction.category,
                        "category_source": transaction.category_source,
                        "matched_rule": transaction.categorization_rule,
                    },
                )

        summary.categories = dict(sorted(counts.items()))
        session.flush()
        return summary

    def apply_result(
        self,
        *,
        transaction: Transaction,
        result: CategorizationResult,
        source: str,
    ) -> bool:
        new_values = {
            "category": result.category,
            "category_confidence": result.confidence,
            "category_source": source,
            "category_manually_set": source == "manual",
            "categorization_reason": result.reason,
            "categorization_rule": result.matched_rule,
            "merchant_normalized": result.merchant_normalized,
        }
        changed = any(getattr(transaction, key) != value for key, value in new_values.items())
        for key, value in new_values.items():
            setattr(transaction, key, value)
        return changed

    def _should_categorize(self, transaction: Transaction) -> bool:
        if transaction.category is None:
            return True
        if transaction.category in {TransactionCategory.other.value, TransactionCategory.needs_review.value}:
            return True
        return transaction.category_source in {None, "unknown", "imported"}

    def _is_manual(self, transaction: Transaction) -> bool:
        return transaction.category_manually_set or transaction.category_source == "manual"

    def _result(
        self,
        *,
        category: str,
        confidence: float,
        reason: str,
        matched_rule: str,
        merchant_normalized: str,
    ) -> CategorizationResult:
        bounded_confidence = max(0.0, min(1.0, confidence))
        if bounded_confidence < self.low_confidence_threshold:
            return CategorizationResult(
                category=TransactionCategory.needs_review.value,
                confidence=bounded_confidence,
                reason=reason,
                matched_rule=matched_rule,
                merchant_normalized=merchant_normalized or None,
            )
        return CategorizationResult(
            category=category,
            confidence=bounded_confidence,
            reason=reason,
            matched_rule=matched_rule,
            merchant_normalized=merchant_normalized or None,
        )

    def _first_match(self, text: str, keywords: tuple[str, ...]) -> str | None:
        if not text:
            return None
        for keyword in keywords:
            if self._contains_keyword(text, keyword):
                return keyword
        return None

    def _contains_keyword(self, text: str, keyword: str) -> bool:
        normalized_keyword = self._normalize_text(keyword)
        if " " in normalized_keyword:
            return normalized_keyword in text
        return re.search(rf"\b{re.escape(normalized_keyword)}\b", text) is not None

    def _normalize_text(self, value: str | None) -> str:
        if value is None:
            return ""
        cleaned = punctuation_pattern.sub(" ", value.lower().strip())
        return whitespace_pattern.sub(" ", cleaned).strip()
