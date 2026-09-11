from pydantic import BaseModel, Field


class OptimizationRequest(BaseModel):
    request: str = Field(..., min_length=3)