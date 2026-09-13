"""What the use cases are allowed to ask for.

The services depend on these, not on SQLAlchemy. That is the seam: the service tests use a
hand-written fake and never open a database, and swapping the storage engine is one class.
"""

from __future__ import annotations

from typing import Protocol

from app.domain.employee import Employee, FilterOptions, SalaryChange
from app.domain.employee_draft import EmployeeDraft
from app.domain.filters import EmployeeFilter, GroupBy, SortSpec
from app.domain.pagination import Page, PageRequest
from app.domain.summary import GroupStats, SalaryStats


class EmployeeReader(Protocol):
    def list_employees(
        self, filters: EmployeeFilter, sort: SortSpec, page: PageRequest
    ) -> Page[Employee]: ...

    def filter_options(self) -> FilterOptions: ...


class EmployeeStore(EmployeeReader, Protocol):
    def get(self, employee_id: int) -> Employee | None: ...

    def history(self, employee_id: int) -> list[SalaryChange]: ...

    def email_taken(self, email: str, exclude_id: int | None = None) -> bool: ...

    def create(self, draft: EmployeeDraft) -> Employee: ...

    def update(
        self, employee_id: int, draft: EmployeeDraft, *, record_salary_change: bool
    ) -> Employee: ...

    def delete(self, employee_id: int) -> bool: ...


class SalaryAnalytics(Protocol):
    def overall(self, filters: EmployeeFilter) -> SalaryStats: ...

    def by_group(self, filters: EmployeeFilter, group_by: GroupBy) -> list[GroupStats]: ...
