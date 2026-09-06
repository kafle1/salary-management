"""What a caller asked for, before it has been validated.

These carry raw strings straight off the wire. Turning them into domain value objects is the
services' job, which is why the routers can stay three lines long and why the validation is
covered by fast unit tests instead of HTTP tests.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.pagination import DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class EmployeeQuery:
    countries: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    search: str | None = None
    sort_by: str | None = None
    sort_direction: str | None = None
    page: int = 1
    page_size: int = DEFAULT_PAGE_SIZE


@dataclass(frozen=True)
class DashboardQuery:
    countries: list[str] = field(default_factory=list)
    departments: list[str] = field(default_factory=list)
    roles: list[str] = field(default_factory=list)
    search: str | None = None
    group_by: str | None = None
