"""Response shapes.

Money goes over the wire as a fixed two-place string rather than a JSON number. A payroll total
for 10,000 people does not survive a round trip through a float, and the UI only ever needs it for
display, so parsing it there is the cheap side of the trade.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, PlainSerializer

from app.domain.employee import Employee, FilterOptions
from app.domain.pagination import Page
from app.domain.summary import DashboardSummary, SalaryStats


def _as_fixed(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


MoneyAmount = Annotated[Decimal, PlainSerializer(_as_fixed, return_type=str)]
OptionalMoneyAmount = Annotated[Decimal | None, PlainSerializer(_as_fixed, return_type=str | None)]


class MoneyOut(BaseModel):
    amount: MoneyAmount
    currency: str


class EmployeeOut(BaseModel):
    id: int
    full_name: str
    email: str
    country_code: str
    country_name: str
    department: str
    role: str
    hire_date: date
    salary: MoneyOut
    salary_in_base: MoneyOut

    @classmethod
    def of(cls, employee: Employee) -> EmployeeOut:
        return cls(
            id=employee.id,
            full_name=employee.full_name,
            email=employee.email,
            country_code=employee.country_code,
            country_name=employee.country_name,
            department=employee.department,
            role=employee.role,
            hire_date=employee.hire_date,
            salary=MoneyOut(amount=employee.salary.amount, currency=employee.salary.currency),
            salary_in_base=MoneyOut(
                amount=employee.salary_in_base.amount, currency=employee.salary_in_base.currency
            ),
        )


class EmployeePageOut(BaseModel):
    items: list[EmployeeOut]
    page: int
    page_size: int
    total: int
    total_pages: int
    has_next: bool
    has_previous: bool

    @classmethod
    def of(cls, page: Page[Employee]) -> EmployeePageOut:
        return cls(
            items=[EmployeeOut.of(employee) for employee in page.items],
            page=page.page,
            page_size=page.page_size,
            total=page.total,
            total_pages=page.total_pages,
            has_next=page.has_next,
            has_previous=page.has_previous,
        )


class CountryOut(BaseModel):
    code: str
    name: str


class FilterOptionsOut(BaseModel):
    countries: list[CountryOut]
    departments: list[str]
    roles: list[str]

    @classmethod
    def of(cls, options: FilterOptions) -> FilterOptionsOut:
        return cls(
            countries=[CountryOut(code=code, name=name) for code, name in options.countries],
            departments=options.departments,
            roles=options.roles,
        )


class SalaryStatsOut(BaseModel):
    headcount: int
    total_payroll: MoneyAmount
    average_salary: OptionalMoneyAmount = None
    median_salary: OptionalMoneyAmount = None

    @classmethod
    def of(cls, stats: SalaryStats) -> SalaryStatsOut:
        return cls(
            headcount=stats.headcount,
            total_payroll=stats.total_payroll,
            average_salary=stats.average_salary,
            median_salary=stats.median_salary,
        )


class GroupStatsOut(SalaryStatsOut):
    key: str
    label: str


class DashboardSummaryOut(BaseModel):
    base_currency: str
    group_by: str
    overall: SalaryStatsOut
    groups: list[GroupStatsOut]

    @classmethod
    def of(cls, summary: DashboardSummary) -> DashboardSummaryOut:
        return cls(
            base_currency=summary.base_currency,
            group_by=summary.group_by.value,
            overall=SalaryStatsOut.of(summary.overall),
            groups=[
                GroupStatsOut(
                    key=group.key,
                    label=group.label,
                    headcount=group.stats.headcount,
                    total_payroll=group.stats.total_payroll,
                    average_salary=group.stats.average_salary,
                    median_salary=group.stats.median_salary,
                )
                for group in summary.groups
            ],
        )
