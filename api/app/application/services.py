from __future__ import annotations

from app.application.ports import EmployeeStore, SalaryAnalytics
from app.application.queries import DashboardQuery, EmployeeInput, EmployeeQuery
from app.domain.employee import (
    EmailAlreadyUsed,
    Employee,
    EmployeeDetail,
    EmployeeNotFound,
    FilterOptions,
)
from app.domain.employee_draft import EmployeeDraft
from app.domain.filters import EmployeeFilter, GroupBy, SortSpec
from app.domain.insights import BandLayout, PeerGapReport
from app.domain.pagination import Page, PageRequest
from app.domain.summary import DashboardSummary


class EmployeeService:
    def __init__(self, employees: EmployeeStore) -> None:
        self._employees = employees

    def get(self, employee_id: int) -> EmployeeDetail:
        return EmployeeDetail(
            employee=self._require(employee_id), history=self._employees.history(employee_id)
        )

    def create(self, form: EmployeeInput) -> Employee:
        draft = _draft(form)
        if self._employees.email_taken(draft.email):
            raise EmailAlreadyUsed(draft.email)
        return self._employees.create(draft)

    def update(self, employee_id: int, form: EmployeeInput) -> Employee:
        current = self._require(employee_id)
        draft = _draft(form)
        if self._employees.email_taken(draft.email, exclude_id=employee_id):
            raise EmailAlreadyUsed(draft.email)
        # only a real move in pay goes in the history, not a fixed typo in someone's name
        return self._employees.update(
            employee_id, draft, record_salary_change=draft.salary != current.salary
        )

    def delete(self, employee_id: int) -> None:
        if not self._employees.delete(employee_id):
            raise EmployeeNotFound(employee_id)

    def _require(self, employee_id: int) -> Employee:
        employee = self._employees.get(employee_id)
        if employee is None:
            raise EmployeeNotFound(employee_id)
        return employee

    def list(self, query: EmployeeQuery) -> Page[Employee]:
        filters = EmployeeFilter.build(
            countries=query.countries,
            departments=query.departments,
            roles=query.roles,
            search=query.search,
        )
        sort = SortSpec.parse(query.sort_by, query.sort_direction)
        page = PageRequest(page=query.page, page_size=query.page_size)
        return self._employees.list_employees(filters, sort, page)

    def filter_options(self) -> FilterOptions:
        return self._employees.filter_options()


def _draft(form: EmployeeInput) -> EmployeeDraft:
    return EmployeeDraft.build(
        full_name=form.full_name,
        email=form.email,
        country_code=form.country_code,
        department=form.department,
        role=form.role,
        hire_date=form.hire_date,
        salary_amount=form.salary_amount,
        salary_note=form.salary_note,
    )


class DashboardService:
    def __init__(self, analytics: SalaryAnalytics) -> None:
        self._analytics = analytics

    def summary(self, query: DashboardQuery) -> DashboardSummary:
        filters = _dashboard_filters(query)
        group_by = GroupBy.parse(query.group_by)
        # the cards, the breakdown and the bands answer the same question, so they see one filter
        overall = self._analytics.overall(filters)
        bands = (
            []
            if overall.highest_salary is None
            else self._analytics.distribution(filters, BandLayout.covering(overall.highest_salary))
        )
        return DashboardSummary(
            group_by=group_by,
            overall=overall,
            groups=self._analytics.by_group(filters, group_by),
            bands=bands,
        )

    def below_peers(self, query: DashboardQuery, limit: int) -> PeerGapReport:
        return self._analytics.below_peers(_dashboard_filters(query), limit)


def _dashboard_filters(query: DashboardQuery) -> EmployeeFilter:
    return EmployeeFilter.build(
        countries=query.countries,
        departments=query.departments,
        roles=query.roles,
        search=query.search,
    )
