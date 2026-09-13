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

from app.domain.countries import COUNTRIES
from app.domain.employee import Employee, EmployeeDetail, FilterOptions, SalaryChange
from app.domain.insights import PayBand, PeerGapReport
from app.domain.money import BASE_CURRENCY, Money
from app.domain.pagination import Page
from app.domain.summary import DashboardSummary, SalaryStats


def _as_fixed(value: Decimal | None) -> str | None:
    return None if value is None else f"{value:.2f}"


MoneyAmount = Annotated[Decimal, PlainSerializer(_as_fixed, return_type=str)]
OptionalMoneyAmount = Annotated[Decimal | None, PlainSerializer(_as_fixed, return_type=str | None)]


class EmployeeIn(BaseModel):
    """Every field optional and loosely typed on purpose: the domain checks them all at once and
    names each one that is wrong, which a pydantic failure on the first bad type would not."""

    full_name: str | None = None
    email: str | None = None
    country_code: str | None = None
    department: str | None = None
    role: str | None = None
    hire_date: str | None = None
    salary_amount: str | int | float | None = None
    salary_note: str | None = None


class MoneyOut(BaseModel):
    amount: MoneyAmount
    currency: str

    @classmethod
    def of(cls, money: Money) -> MoneyOut:
        return cls(amount=money.amount, currency=money.currency)


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
            salary=MoneyOut.of(employee.salary),
            salary_in_base=MoneyOut.of(employee.salary_in_base),
        )


class SalaryChangeOut(BaseModel):
    changed_on: date
    previous: MoneyOut | None
    new: MoneyOut
    note: str | None

    @classmethod
    def of(cls, change: SalaryChange) -> SalaryChangeOut:
        return cls(
            changed_on=change.changed_on,
            previous=MoneyOut.of(change.previous) if change.previous else None,
            new=MoneyOut.of(change.new),
            note=change.note,
        )


class EmployeeDetailOut(EmployeeOut):
    history: list[SalaryChangeOut]

    @classmethod
    def of_detail(cls, detail: EmployeeDetail) -> EmployeeDetailOut:
        return cls(
            **EmployeeOut.of(detail.employee).model_dump(),
            history=[SalaryChangeOut.of(change) for change in detail.history],
        )


class PayableCountryOut(BaseModel):
    code: str
    name: str
    currency: str

    @classmethod
    def all(cls) -> list[PayableCountryOut]:
        return [cls(code=c.code, name=c.name, currency=c.currency) for c in COUNTRIES]


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
    lowest_salary: OptionalMoneyAmount = None
    highest_salary: OptionalMoneyAmount = None

    @classmethod
    def of(cls, stats: SalaryStats) -> SalaryStatsOut:
        return cls(
            headcount=stats.headcount,
            total_payroll=stats.total_payroll,
            average_salary=stats.average_salary,
            median_salary=stats.median_salary,
            lowest_salary=stats.lowest_salary,
            highest_salary=stats.highest_salary,
        )


class GroupStatsOut(SalaryStatsOut):
    key: str
    label: str


class PayBandOut(BaseModel):
    lower: MoneyAmount
    upper: MoneyAmount
    headcount: int

    @classmethod
    def of(cls, band: PayBand) -> PayBandOut:
        return cls(lower=band.lower, upper=band.upper, headcount=band.headcount)


class DashboardSummaryOut(BaseModel):
    base_currency: str
    group_by: str
    overall: SalaryStatsOut
    groups: list[GroupStatsOut]
    bands: list[PayBandOut]

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
                    **SalaryStatsOut.of(group.stats).model_dump(),
                )
                for group in summary.groups
            ],
            bands=[PayBandOut.of(band) for band in summary.bands],
        )


class PeerGapOut(BaseModel):
    employee: EmployeeOut
    peer_median: MoneyOut
    peers: int
    percent_of_median: int


class PeerGapReportOut(BaseModel):
    threshold_percent: int
    min_peers: int
    total: int
    items: list[PeerGapOut]

    @classmethod
    def of(cls, report: PeerGapReport) -> PeerGapReportOut:
        return cls(
            threshold_percent=report.threshold_percent,
            min_peers=report.min_peers,
            total=report.total,
            items=[
                PeerGapOut(
                    employee=EmployeeOut.of(gap.employee),
                    peer_median=MoneyOut.of(Money(gap.peer_median, BASE_CURRENCY)),
                    peers=gap.peers,
                    percent_of_median=gap.percent_of_median,
                )
                for gap in report.items
            ],
        )
