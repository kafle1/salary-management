from __future__ import annotations

from app.application.ports import EmployeeReader, SalaryAnalytics
from app.application.queries import DashboardQuery, EmployeeQuery
from app.domain.employee import Employee, FilterOptions
from app.domain.filters import EmployeeFilter, GroupBy, SortSpec
from app.domain.pagination import Page, PageRequest
from app.domain.summary import DashboardSummary


class EmployeeService:
    def __init__(self, employees: EmployeeReader) -> None:
        self._employees = employees

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


class DashboardService:
    def __init__(self, analytics: SalaryAnalytics) -> None:
        self._analytics = analytics

    def summary(self, query: DashboardQuery) -> DashboardSummary:
        filters = EmployeeFilter.build(
            countries=query.countries,
            departments=query.departments,
            roles=query.roles,
            search=query.search,
        )
        group_by = GroupBy.parse(query.group_by)
        # the cards and the breakdown answer the same question, so they see the same filter
        return DashboardSummary(
            group_by=group_by,
            overall=self._analytics.overall(filters),
            groups=self._analytics.by_group(filters, group_by),
        )
