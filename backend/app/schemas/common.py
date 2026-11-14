"""Contratos compartidos por más de un recurso."""

from __future__ import annotations

from typing import Self

from pydantic import BaseModel, Field


class Pagina[T](BaseModel):
    """Envelope de paginación de la API (`{items, page, page_size, total, pages}`)."""

    items: list[T]
    page: int = Field(ge=1)
    page_size: int = Field(ge=1)
    total: int = Field(ge=0)
    pages: int = Field(ge=0)

    @classmethod
    def de(cls, items: list[T], *, page: int, page_size: int, total: int) -> Self:
        return cls(
            items=items,
            page=page,
            page_size=page_size,
            total=total,
            pages=(total + page_size - 1) // page_size if total else 0,
        )
