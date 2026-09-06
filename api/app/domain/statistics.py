"""The statistics the dashboard reports, defined in one place.

Median is the one that is worth writing down. Mean pay is easy to compute and easy to mislead
with, because a handful of executive salaries drag it away from what a typical person earns. So
the dashboard shows both, and this module is the definition of the median the SQL has to match.

Nothing in the request path calls this: aggregates run in the database so they stay server-side.
It exists so the SQL has an oracle to be tested against, which is cheaper than trusting a window
function by eye.
"""

from __future__ import annotations

from collections.abc import Sequence
from decimal import Decimal

from app.domain.money import to_cents


def median(values: Sequence[Decimal]) -> Decimal | None:
    if not values:
        return None
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return to_cents((ordered[middle - 1] + ordered[middle]) / 2)
