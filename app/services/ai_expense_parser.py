from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.schemas.ai_expense import ChatExpenseParseResponse, ChatTransactionDraft
from app.schemas.transaction import TransactionCategory
from app.services.transaction_categorizer import TransactionCategorizerService


AI_CHAT_SOURCE = "ai_chat_manual"
MAX_CHAT_MESSAGE_LENGTH = 500
SAFE_DRAFT_REPLY = "I found a possible transaction. Please review before saving."

forbidden_instruction_patterns = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore (all )?(previous|system|developer) instructions",
        r"reveal (the )?(prompt|system|developer|secret)",
        r"bypass",
        r"jailbreak",
        r"do not ask.*confirm",
        r"save (it|this|the transaction) (directly|automatically|now)",
    ]
]

income_patterns = re.compile(r"\b(salary|payroll|income|came in|received|deposit|bonus|paid me)\b", re.IGNORECASE)
expense_patterns = re.compile(
    r"\b(bought|buy|paid|spent|spend|charged|bill|ride|subscription|coffee|lunch|dinner|breakfast)\b",
    re.IGNORECASE,
)
currency_amount_patterns = (
    re.compile(r"(?:₱|php)\s*(?P<amount>\d[\d,]*(?:\.\d{1,2})?)", re.IGNORECASE),
    re.compile(r"(?P<amount>\d[\d,]*(?:\.\d{1,2})?)\s*(?:pesos?|php)\b", re.IGNORECASE),
)
number_pattern = re.compile(r"(?<![\w-])\d[\d,]*(?:\.\d{1,2})?(?![\w-])")
date_iso_pattern = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
month_day_pattern = re.compile(
    r"\b(?:on\s+)?(?P<month>jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|"
    r"aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\s+(?P<day>\d{1,2})\b",
    re.IGNORECASE,
)
weekday_pattern = re.compile(r"\blast\s+(?P<weekday>monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE)

month_numbers = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}
weekdays = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}
known_merchants = {
    "jollibee": "Jollibee",
    "netflix": "Netflix",
    "grab": "Grab",
    "starbucks": "Starbucks",
    "meralco": "Meralco",
    "national book store": "National Book Store",
    "canva": "Canva",
    "company payroll": "Company Payroll",
    "spotify": "Spotify",
    "mcdonalds": "McDonalds",
    "mcdo": "McDonalds",
}
payment_keywords = {
    "cash": "cash",
    "card": "card",
    "credit card": "card",
    "debit card": "card",
    "gcash": "gcash",
    "maya": "maya",
    "bank transfer": "bank_transfer",
    "transfer": "bank_transfer",
}


@dataclass(frozen=True)
class ParsedBits:
    amount: Decimal | None
    transaction_type: str | None
    transaction_date: date
    explicit_date: bool
    merchant: str | None
    description: str | None
    payment_type: str


class AIExpenseParserService:
    def parse(self, *, message: str, timezone: str = "Asia/Manila", as_of: date | None = None) -> ChatExpenseParseResponse:
        cleaned = self._clean_message(message)
        today = as_of or self._today(timezone)

        if self._looks_like_prompt_injection(cleaned):
            return self._clarification("I can only turn one transaction message into a draft for you to review.")

        bits = self._parse_bits(cleaned, today=today)
        clarification = self._clarification_for(bits)
        if clarification is not None:
            return self._clarification(clarification)

        assert bits.amount is not None
        assert bits.transaction_type is not None
        assert bits.merchant is not None
        assert bits.description is not None

        signed_amount = abs(bits.amount)
        if bits.transaction_type == "expense":
            signed_amount = -signed_amount

        category = self._category_for(
            transaction_type=bits.transaction_type,
            merchant=bits.merchant,
            description=bits.description,
        )
        confidence = self._confidence(bits=bits)
        draft = ChatTransactionDraft(
            transaction_type=bits.transaction_type,  # type: ignore[arg-type]
            transaction_date=bits.transaction_date,
            merchant=bits.merchant,
            description=bits.description,
            amount=signed_amount,
            currency="PHP",
            category=category,
            payment_type=bits.payment_type,
            confidence=confidence,
            source=AI_CHAT_SOURCE,
        )
        return ChatExpenseParseResponse(
            reply=SAFE_DRAFT_REPLY,
            clarification_needed=False,
            clarification_question=None,
            draft=draft,
        )

    def _clean_message(self, message: str) -> str:
        cleaned = re.sub(r"\s+", " ", message.strip())
        if len(cleaned) > MAX_CHAT_MESSAGE_LENGTH:
            raise ValueError("Message is too long.")
        return cleaned

    def _today(self, timezone: str) -> date:
        try:
            tz = ZoneInfo(timezone)
        except ZoneInfoNotFoundError:
            tz = ZoneInfo("Asia/Manila")
        return datetime.now(tz).date()

    def _looks_like_prompt_injection(self, message: str) -> bool:
        return any(pattern.search(message) for pattern in forbidden_instruction_patterns)

    def _parse_bits(self, message: str, *, today: date) -> ParsedBits:
        return ParsedBits(
            amount=self._extract_amount(message),
            transaction_type=self._extract_transaction_type(message),
            transaction_date=(parsed_date := self._extract_date(message, today=today))[0],
            explicit_date=parsed_date[1],
            merchant=self._extract_merchant(message),
            description=self._extract_description(message),
            payment_type=self._extract_payment_type(message),
        )

    def _extract_amount(self, message: str) -> Decimal | None:
        for pattern in currency_amount_patterns:
            match = pattern.search(message)
            if match is not None:
                return self._to_decimal(match.group("amount"))

        without_dates = date_iso_pattern.sub(" ", message)
        without_dates = month_day_pattern.sub(" ", without_dates)
        candidates = [self._to_decimal(match.group(0)) for match in number_pattern.finditer(without_dates)]
        amounts = [item for item in candidates if item is not None]
        if not amounts:
            return None
        return max(amounts, key=lambda item: abs(item))

    def _to_decimal(self, value: str) -> Decimal | None:
        try:
            amount = Decimal(value.replace(",", ""))
        except (InvalidOperation, ValueError):
            return None
        if not amount.is_finite() or amount == 0:
            return None
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def _extract_transaction_type(self, message: str) -> str | None:
        if income_patterns.search(message):
            return "income"
        if expense_patterns.search(message):
            return "expense"
        return None

    def _extract_date(self, message: str, *, today: date) -> tuple[date, bool]:
        iso_match = date_iso_pattern.search(message)
        if iso_match is not None:
            try:
                return date.fromisoformat(iso_match.group(0)), True
            except ValueError:
                pass
        if re.search(r"\byesterday\b", message, re.IGNORECASE):
            return today - timedelta(days=1), True
        weekday_match = weekday_pattern.search(message)
        if weekday_match is not None:
            target = weekdays[weekday_match.group("weekday").lower()]
            days_back = (today.weekday() - target) % 7
            if days_back == 0:
                days_back = 7
            return today - timedelta(days=days_back), True
        month_match = month_day_pattern.search(message)
        if month_match is not None:
            month = month_numbers[month_match.group("month").lower()[:3]]
            day = int(month_match.group("day"))
            try:
                return date(today.year, month, day), True
            except ValueError:
                return today, False
        return today, False

    def _extract_merchant(self, message: str) -> str | None:
        lowered = message.lower()
        for merchant_key, merchant_name in known_merchants.items():
            if re.search(rf"\b{re.escape(merchant_key)}\b", lowered):
                return merchant_name

        for pattern in [
            r"\bat\s+(?P<merchant>[a-z0-9][a-z0-9& .'-]{1,80}?)(?:\s+for|\s+on|\s+today|\s+yesterday|\s+was|$)",
            r"\bfrom\s+(?P<merchant>[a-z0-9][a-z0-9& .'-]{1,80}?)(?:\s+for|\s+on|\s+today|\s+yesterday|\s+was|$)",
            r"\bfor\s+(?P<merchant>[a-z][a-z0-9& .'-]{1,80}?)(?:\s+today|\s+yesterday|\s+on|$)",
        ]:
            match = re.search(pattern, lowered, re.IGNORECASE)
            if match is not None:
                merchant = self._title(match.group("merchant"))
                if not number_pattern.fullmatch(merchant):
                    return merchant
        return None

    def _extract_description(self, message: str) -> str | None:
        merchant = self._extract_merchant(message)
        lowered = message.lower()
        item_match = re.search(
            r"\b(?:bought|buy|spent|spend)\s+(?P<item>[a-z][a-z0-9 .'-]{1,80}?)(?:\s+from|\s+at|\s+for|\s+on|$)",
            lowered,
            re.IGNORECASE,
        )
        if item_match is not None:
            item = self._title(item_match.group("item"))
            if merchant:
                preposition = "at" if " at " in lowered else "from"
                return f"{item} {preposition} {merchant}"
            return item
        if merchant:
            if income_patterns.search(message):
                return f"Income from {merchant}"
            return f"{merchant} transaction"
        cleaned = self._strip_amount_and_dates(message)
        return cleaned[:1000] if cleaned else None

    def _strip_amount_and_dates(self, message: str) -> str:
        cleaned = message
        for pattern in currency_amount_patterns:
            cleaned = pattern.sub(" ", cleaned)
        cleaned = number_pattern.sub(" ", cleaned)
        cleaned = date_iso_pattern.sub(" ", cleaned)
        cleaned = month_day_pattern.sub(" ", cleaned)
        cleaned = re.sub(r"\b(today|yesterday|last monday|last tuesday|last wednesday|last thursday|last friday|last saturday|last sunday)\b", " ", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip(" .")
        return self._title(cleaned) if cleaned else ""

    def _extract_payment_type(self, message: str) -> str:
        lowered = message.lower()
        for keyword, payment_type in payment_keywords.items():
            if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                return payment_type
        return "unknown"

    def _category_for(self, *, transaction_type: str, merchant: str, description: str) -> TransactionCategory:
        if transaction_type == "income":
            return TransactionCategory.income
        result = TransactionCategorizerService().categorize_values(
            merchant_raw=merchant,
            description=description,
        )
        return TransactionCategory(result.category)

    def _confidence(self, *, bits: ParsedBits) -> float:
        score = Decimal("0.54")
        if bits.amount is not None:
            score += Decimal("0.14")
        if bits.merchant is not None:
            score += Decimal("0.12")
        if bits.description is not None:
            score += Decimal("0.08")
        if bits.transaction_type is not None:
            score += Decimal("0.06")
        if bits.explicit_date:
            score += Decimal("0.03")
        if bits.payment_type != "unknown":
            score += Decimal("0.03")
        return float(min(score, Decimal("0.95")))

    def _clarification_for(self, bits: ParsedBits) -> str | None:
        if bits.amount is None:
            description = (bits.description or bits.merchant or "that transaction").lower()
            return f"How much was {description}?"
        if bits.merchant is None and (bits.description is None or bits.description.lower() in {"paid", "i paid"}):
            return "What merchant or description should I use for this transaction?"
        if bits.transaction_type is None:
            return "Was this an expense or income?"
        return None

    def _clarification(self, question: str) -> ChatExpenseParseResponse:
        return ChatExpenseParseResponse(
            reply=question,
            clarification_needed=True,
            clarification_question=question,
            draft=None,
        )

    def _title(self, value: str) -> str:
        value = re.sub(r"\s+", " ", value.strip(" ."))
        small_words = {"a", "an", "and", "at", "for", "from", "in", "of", "on", "the", "to"}
        words = []
        for index, word in enumerate(value.split()):
            lower = word.lower()
            if index > 0 and lower in small_words:
                words.append(lower)
            else:
                words.append(word[:1].upper() + word[1:])
        return " ".join(words)
