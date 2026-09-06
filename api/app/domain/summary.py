"""The four numbers on the dashboard, and the same four broken down by one dimension."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.filters import GroupBy
from app.domain.money import BASE_CURRENCY


@dataclass(frozen=True)
class SalaryStats:
    headcount: int = 0
    total_payroll: Decimal = Decimal("0.00")
    average_salary: Decimal | None = None
    median_salary: Decimal | None = None

    @property
    def is_empty(self) -> bool:
        return self.headcount == 0


@dataclass(frozen=True)
class GroupStats:
    key: str
    label: str
    stats: SalaryStats


@dataclass(frozen=True)
class DashboardSummary:
    group_by: GroupBy
    overall: SalaryStats = field(default_factory=SalaryStats)
    groups: list[GroupStats] = field(default_factory=list)
    base_currency: str = BASE_CURRENCY
