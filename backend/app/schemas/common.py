from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ProblemDetail(BaseModel):
    type: str
    title: str
    status: int
    detail: str
    instance: str | None = None
    code: str
    request_id: str
    errors: list[dict[str, Any]] | None = None


class Page(BaseModel, Generic[T]):  # noqa: UP046 (Pydantic v2 usa Generic)
    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)
