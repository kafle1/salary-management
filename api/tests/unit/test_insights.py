from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.domain.employee import Employee
from app.domain.insights import MAX_BANDS, BandLayout, PayBand, PeerGap
from app.domain.money import Money


def test_bands_use_a_round_width_a_person_can_read():
    layout = BandLayout.covering(Decimal("372000.00"))

    assert layout.width == Decimal("50000.00")
    assert layout.count == 8


@pytest.mark.parametrize(
    "highest", ["0.01", "9.99", "10", "99999.99", "100000", "100000.01", "372000", "1000000"]
)
def test_the_top_earner_always_lands_in_the_last_band_and_there_are_never_too_many(highest):
    top = Decimal(highest)

    layout = BandLayout.covering(top)

    assert layout.count <= MAX_BANDS
    assert layout.width * (layout.count - 1) <= top < layout.width * layout.count


def test_one_person_paid_nothing_still_gets_a_band():
    layout = BandLayout.covering(Decimal("0.00"))

    assert layout.count == 1
    assert layout.width > 0


def test_a_band_nobody_falls_in_is_reported_as_zero_so_the_chart_keeps_its_shape():
    layout = BandLayout(width=Decimal("10.00"), count=4)

    bands = layout.bands({0: 2, 3: 1})

    assert bands == [
        PayBand(lower=Decimal("0.00"), upper=Decimal("10.00"), headcount=2),
        PayBand(lower=Decimal("10.00"), upper=Decimal("20.00"), headcount=0),
        PayBand(lower=Decimal("20.00"), upper=Decimal("30.00"), headcount=0),
        PayBand(lower=Decimal("30.00"), upper=Decimal("40.00"), headcount=1),
    ]


def test_the_upper_edges_are_where_each_band_stops():
    assert BandLayout(width=Decimal("25.00"), count=3).upper_edges() == [
        Decimal("25.00"),
        Decimal("50.00"),
        Decimal("75.00"),
    ]


def paid(amount: str) -> Employee:
    return Employee(
        id=1,
        full_name="Ada Lovelace",
        email="ada@acme.example",
        country_code="US",
        country_name="United States",
        department="Engineering",
        role="Engineer",
        hire_date=date(2024, 1, 15),
        salary=Money(Decimal(amount), "USD"),
        salary_in_base=Money(Decimal(amount), "USD"),
    )


def test_the_share_of_the_peer_median_rounds_down_so_a_flagged_person_never_reads_80():
    gap = PeerGap(employee=paid("79999.00"), peer_median=Decimal("100000.00"), peers=5)

    assert gap.percent_of_median == 79
