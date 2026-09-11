from typing import Generic, TypeVar, List, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int = Field(..., ge=0, description="Total number of items matching filters")
    page: int = Field(..., ge=1, description="Current page number")
    limit: int = Field(..., ge=1, description="Items per page")
    total_pages: int = Field(..., ge=0, description="Total pages available")


class MessageResponse(BaseModel):
    message: str
    id: str | None = None
