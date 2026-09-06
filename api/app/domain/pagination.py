"""Paging as a value object, so the rules live in one place instead of in every route."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

DEFAULT_PAGE_SIZE = 25
MAX_PAGE_SIZE = 200

T = TypeVar("T")


@dataclass(frozen=True)
class PageRequest:
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE

    def __post_init__(self) -> None:
        if self.page < 1:
            raise ValueError(f"page starts at 1, got {self.page}")
        if not 1 <= self.page_size <= MAX_PAGE_SIZE:
            raise ValueError(f"page_size must be between 1 and {MAX_PAGE_SIZE}, got {self.page_size}")

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        return self.page_size


@dataclass(frozen=True)
class Page(Generic[T]):
    items: list[T] = field(default_factory=list)
    total: int = 0
    request: PageRequest = field(default_factory=PageRequest)

    @property
    def page(self) -> int:
        return self.request.page

    @property
    def page_size(self) -> int:
        return self.request.page_size

    @property
    def total_pages(self) -> int:
        if self.total <= 0:
            return 0
        return -(-self.total // self.page_size)

    @property
    def has_next(self) -> bool:
        return self.page < self.total_pages

    @property
    def has_previous(self) -> bool:
        return self.page > 1 and self.total_pages > 0
