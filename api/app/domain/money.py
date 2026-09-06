"""Money and currency conversion.

An employee is paid in their own currency and that is the number stored. Anything that compares
people across countries goes through the base currency, and the conversion is defined here so
there is one answer to "what is this salary worth in USD" rather than one per caller.

The SQL in the repository layer computes the same product for 10,000 rows at a time. These types
are the definition it has to agree with, and the tests pin the two together.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

BASE_CURRENCY = "USD"
CENTS = Decimal("0.01")

_CURRENCY_CODE = re.compile(r"^[A-Z]{3}$")


def to_cents(value: Decimal) -> Decimal:
    """Round to two places, half up. Bankers rounding surprises people reading a payroll total."""
    return value.quantize(CENTS, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class Money:
    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        code = self.currency.strip().upper()
        if not _CURRENCY_CODE.match(code):
            raise ValueError(f"currency must be a 3 letter ISO code, got {self.currency!r}")
        if self.amount < 0:
            raise ValueError(f"salary cannot be negative, got {self.amount}")
        object.__setattr__(self, "currency", code)
        object.__setattr__(self, "amount", to_cents(self.amount))


@dataclass(frozen=True)
class ExchangeRate:
    """How much one unit of `currency` is worth in the base currency."""

    currency: str
    usd_per_unit: Decimal

    def __post_init__(self) -> None:
        code = self.currency.strip().upper()
        if not _CURRENCY_CODE.match(code):
            raise ValueError(f"currency must be a 3 letter ISO code, got {self.currency!r}")
        if self.usd_per_unit <= 0:
            raise ValueError(f"rate must be positive, got {self.usd_per_unit}")
        object.__setattr__(self, "currency", code)

    def to_base(self, salary: Money) -> Money:
        if salary.currency != self.currency:
            raise ValueError(
                f"rate is for {self.currency}, cannot convert a salary in {salary.currency}"
            )
        return Money(salary.amount * self.usd_per_unit, BASE_CURRENCY)
