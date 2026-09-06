"""What a caller is allowed to filter, sort and group by.

Sorting is an enum rather than a string because the alternative is putting a user-supplied column
name into an ORDER BY, and there is no safe way to do that. Anything not in this file is not
sortable.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SortField(StrEnum):
    NAME = "name"
    EMAIL = "email"
    COUNTRY = "country"
    DEPARTMENT = "department"
    ROLE = "role"
    HIRE_DATE = "hire_date"
    SALARY_USD = "salary_usd"
    SALARY_NATIVE = "salary_native"


class SortDirection(StrEnum):
    ASC = "asc"
    DESC = "desc"


class GroupBy(StrEnum):
    COUNTRY = "country"
    DEPARTMENT = "department"
    ROLE = "role"


class UnknownSortField(ValueError):
    pass


@dataclass(frozen=True)
class SortSpec:
    field: SortField = SortField.NAME
    direction: SortDirection = SortDirection.ASC

    @classmethod
    def parse(cls, field: str | None = None, direction: str | None = None) -> SortSpec:
        try:
            resolved_field = SortField(field.strip().lower()) if field else SortField.NAME
        except ValueError as exc:
            allowed = ", ".join(sorted(f.value for f in SortField))
            raise UnknownSortField(f"cannot sort by {field!r}. allowed: {allowed}") from exc
        try:
            resolved_dir = (
                SortDirection(direction.strip().lower()) if direction else SortDirection.ASC
            )
        except ValueError as exc:
            raise UnknownSortField(f"sort direction must be asc or desc, got {direction!r}") from exc
        return cls(resolved_field, resolved_dir)


def _clean(values: list[str] | tuple[str, ...] | None, *, upper: bool = False) -> tuple[str, ...]:
    if not values:
        return ()
    seen: dict[str, None] = {}
    for raw in values:
        value = raw.strip()
        if not value:
            continue
        seen.setdefault(value.upper() if upper else value)
    return tuple(seen)


@dataclass(frozen=True)
class EmployeeFilter:
    countries: tuple[str, ...] = ()
    departments: tuple[str, ...] = ()
    roles: tuple[str, ...] = ()
    search: str | None = None

    @classmethod
    def build(
        cls,
        countries: list[str] | None = None,
        departments: list[str] | None = None,
        roles: list[str] | None = None,
        search: str | None = None,
    ) -> EmployeeFilter:
        term = (search or "").strip()
        return cls(
            countries=_clean(countries, upper=True),
            departments=_clean(departments),
            roles=_clean(roles),
            search=term or None,
        )

    @property
    def is_empty(self) -> bool:
        return not (self.countries or self.departments or self.roles or self.search)
