from typing import Optional

from pydantic import BaseModel, Field

from app.ai.assistant.intent import AssistantIntent


class AssistantIntentResult(BaseModel):
    intent: AssistantIntent
    amount: Optional[float] = Field(None, ge=0)
    amount_requested: bool = False
    day: Optional[int] = Field(None, ge=1)
    confidence: float = Field(..., ge=0, le=1)
    parse_error: Optional[str] = None