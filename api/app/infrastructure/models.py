from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class ExchangeRate(Base):
    """One row per currency the org pays in. Seeded, never fetched, see the requirements doc."""

    __tablename__ = "exchange_rates"

    currency_code: Mapped[str] = mapped_column(String(3), primary_key=True)
    usd_per_unit: Mapped[Decimal] = mapped_column(Numeric(18, 8), nullable=False)
    as_of: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("usd_per_unit > 0", name="ck_exchange_rates_positive"),
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)
    department: Mapped[str] = mapped_column(String(60), nullable=False)
    role: Mapped[str] = mapped_column(String(80), nullable=False)
    hire_date: Mapped[date] = mapped_column(Date, nullable=False)
    # numeric, never float. a salary column that drifts by a cent is a support ticket.
    salary_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("exchange_rates.currency_code"), nullable=False
    )

    __table_args__ = (
        # the exact combination the employees page filters on
        Index("ix_employees_country_department_role", "country_code", "department", "role"),
        Index("ix_employees_currency_code", "currency_code"),
        Index("ix_employees_department", "department"),
        Index("ix_employees_role", "role"),
        CheckConstraint("salary_amount >= 0", name="ck_employees_salary_non_negative"),
    )


class SalaryChange(Base):
    """Append-only. One row for the salary someone was added on, one more each time it moves."""

    __tablename__ = "salary_changes"

    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False
    )
    changed_on: Mapped[date] = mapped_column(Date, nullable=False, default=date.today)
    previous_amount: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    previous_currency: Mapped[str | None] = mapped_column(String(3))
    new_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    new_currency: Mapped[str] = mapped_column(String(3), nullable=False)
    note: Mapped[str | None] = mapped_column(String(200))

    __table_args__ = (
        Index("ix_salary_changes_employee_changed_on", "employee_id", "changed_on"),
    )
