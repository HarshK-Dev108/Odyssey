import re

from app.ai.assistant.intent import AssistantIntent
from app.schemas.assistant import AssistantIntentResult


AMOUNT_PATTERN = re.compile(
    r"(?:₹|rs\.?|inr)?\s*"
    r"(\d+(?:,\d{3})*(?:\.\d+)?)\s*(k|thousand)?\b",
    re.IGNORECASE,
)
DAY_PATTERN = re.compile(r"\bday\s+(\d+)\b", re.IGNORECASE)


def _normalize(message: str) -> str:
    return " ".join(message.casefold().split())


def _parse_saving_amount(message: str) -> tuple[float | None, bool, str | None]:
    amount_context = any(
        phrase in message
        for phrase in (
            "save",
            "cheaper",
            "cheap",
            "reduce",
            "lower",
            "cut",
            "spend less",
            "less expensive",
        )
    )
    if not amount_context:
        return None, False, None

    match = AMOUNT_PATTERN.search(message)
    if match:
        amount = float(match.group(1).replace(",", ""))
        multiplier = match.group(2)
        if multiplier and multiplier.casefold() in {"k", "thousand"}:
            amount *= 1000
        return amount, True, None

    explicit_amount_marker = re.search(
        r"(?:₹|rs\.?|inr)\s*[a-z]+|"
        r"(?:save|reduce|lower|cut)\s+(?:the\s+)?(?:trip\s+)?(?:by\s+)?[a-z]+",
        message,
        re.IGNORECASE,
    )
    if explicit_amount_marker:
        return None, True, "I could not understand the requested saving amount."

    return None, False, None


def parse_assistant_message(message: str) -> AssistantIntentResult:
    normalized = _normalize(message)
    amount, amount_requested, parse_error = _parse_saving_amount(normalized)

    if normalized == "budget" or any(phrase in normalized for phrase in ("remaining budget", "budget left", "money left", "how much budget", "how much money")):
        return AssistantIntentResult(
            intent=AssistantIntent.REMAINING_BUDGET,
            confidence=1.0,
        )

    if any(phrase in normalized for phrase in ("upgrade hotel", "upgrade my hotel", "better hotel", "hotel upgrade")):
        return AssistantIntentResult(
            intent=AssistantIntent.UPGRADE_HOTEL,
            confidence=1.0,
        )

    if any(phrase in normalized for phrase in ("adventure", "scuba diving")) and any(
        phrase in normalized for phrase in ("add", "more", "want", "include")
    ):
        return AssistantIntentResult(
            intent=AssistantIntent.ADD_ADVENTURE,
            confidence=1.0,
        )

    if any(phrase in normalized for phrase in ("avoid crowded", "less crowded", "don't want crowded", "do not want crowded")):
        return AssistantIntentResult(
            intent=AssistantIntent.AVOID_CROWDS,
            confidence=1.0,
        )

    if any(phrase in normalized for phrase in ("itinerary", "modify day", "change day", "make day", "remove this activity", "change my activities")):
        day_match = DAY_PATTERN.search(normalized)
        return AssistantIntentResult(
            intent=AssistantIntent.CHANGE_ITINERARY,
            day=int(day_match.group(1)) if day_match else None,
            confidence=1.0 if day_match else 0.8,
        )

    if any(phrase in normalized for phrase in ("why did you choose", "why this hotel", "why this activity", "explain this recommendation")):
        return AssistantIntentResult(
            intent=AssistantIntent.EXPLAIN_RECOMMENDATION,
            confidence=1.0,
        )

    if amount_requested or any(
        phrase in normalized
        for phrase in (
            "make it cheaper",
            "make my trip cheaper",
            "reduce my cost",
            "reduce the trip",
            "make it affordable",
            "spend less",
            "less expensive",
            "save money",
            "save on my trip",
        )
    ):
        return AssistantIntentResult(
            intent=AssistantIntent.MAKE_CHEAPER,
            amount=amount,
            amount_requested=amount_requested,
            confidence=1.0,
            parse_error=parse_error,
        )

    if normalized in {"help", "what can you do", "what do you support"}:
        return AssistantIntentResult(
            intent=AssistantIntent.HELP,
            confidence=1.0,
        )

    return AssistantIntentResult(
        intent=AssistantIntent.UNKNOWN,
        confidence=0.0,
    )