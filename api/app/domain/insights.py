"""What the dashboard says about pay beyond the averages: how it spreads, and who sits well under
the people doing the same job in the same country."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from app.domain.employee import Employee
from app.domain.money import CENTS, to_cents

MAX_BANDS = 10
_ROUND_STEPS = (Decimal(1), Decimal(2), Decimal("2.5"), Decimal(5), Decimal(10))

# under 80% of the peer median is where a pay review usually starts asking questions
PEER_GAP_THRESHOLD_PERCENT = 80
# a median of three people is one person's salary, so small groups are left out rather than guessed
MIN_PEERS = 5
DEFAULT_PEER_GAP_LIMIT = 25
MAX_PEER_GAP_LIMIT = 100


@dataclass(frozen=True)
class PayBand:
    lower: Decimal
    upper: Decimal
    headcount: int


@dataclass(frozen=True)
class BandLayout:
    """Equal bands from zero, each [lower, upper), wide enough that the top earner fits."""

    width: Decimal
    count: int

    @classmethod
    def covering(cls, highest: Decimal, most: int = MAX_BANDS) -> BandLayout:
        target = highest / most
        # never below a cent, the smallest step money has
        power = max(Decimal(1).scaleb(target.adjusted()), CENTS) if target else CENTS
        # strictly wider than highest / most, or the top earner would open band most + 1
        width = next(step * power for step in _ROUND_STEPS if step * power > target)
        width = to_cents(width)
        return cls(width=width, count=int(highest // width) + 1)

    def upper_edges(self) -> list[Decimal]:
        return [self.width * (index + 1) for index in range(self.count)]

    def bands(self, counts: Mapping[int, int]) -> list[PayBand]:
        return [
            PayBand(
                lower=self.width * index,
                upper=self.width * (index + 1),
                headcount=counts.get(index, 0),
            )
            for index in range(self.count)
        ]


@dataclass(frozen=True)
class PeerGap:
    employee: Employee
    peer_median: Decimal
    peers: int

    @property
    def percent_of_median(self) -> int:
        # rounded down, so someone flagged under 80% never reads as 80
        return int(self.employee.salary_in_base.amount * 100 // self.peer_median)


@dataclass(frozen=True)
class PeerGapReport:
    total: int
    items: list[PeerGap] = field(default_factory=list)
    threshold_percent: int = PEER_GAP_THRESHOLD_PERCENT
    min_peers: int = MIN_PEERS
