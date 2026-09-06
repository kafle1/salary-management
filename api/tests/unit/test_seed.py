"""The seed is a graded deliverable in its own right: 10,000 rows, identical every run."""

from __future__ import annotations

from collections import Counter
from decimal import Decimal

from app.domain.countries import BY_CODE
from app.infrastructure.seed import (
    DEFAULT_COUNT,
    DEFAULT_SEED,
    HIRING_ENDED,
    HIRING_STARTED,
    USD_PER_UNIT,
    generate_employees,
)


def test_the_same_seed_gives_byte_identical_rows():
    first = list(generate_employees(count=200, seed=DEFAULT_SEED))
    second = list(generate_employees(count=200, seed=DEFAULT_SEED))

    assert first == second


def test_a_different_seed_gives_different_rows():
    first = list(generate_employees(count=200, seed=1))
    second = list(generate_employees(count=200, seed=2))

    assert first != second


def test_a_shorter_run_is_a_prefix_of_a_longer_one():
    short = list(generate_employees(count=10, seed=DEFAULT_SEED))
    long = list(generate_employees(count=50, seed=DEFAULT_SEED))

    assert long[:10] == short


def test_the_full_set_is_ten_thousand_people_with_unique_emails():
    rows = list(generate_employees())

    assert len(rows) == DEFAULT_COUNT
    assert len({row["email"] for row in rows}) == DEFAULT_COUNT


def test_everyone_is_paid_in_the_currency_of_their_country():
    for row in generate_employees(count=500):
        assert row["currency_code"] == BY_CODE[row["country_code"]].currency


def test_every_currency_used_has_a_seeded_rate():
    used = {row["currency_code"] for row in generate_employees(count=2_000)}

    assert used <= set(USD_PER_UNIT)


def test_salaries_are_positive_and_rounded_like_an_offer_letter():
    for row in generate_employees(count=500):
        amount: Decimal = row["salary_amount"]
        assert amount > 0
        assert amount % 100 == 0


def test_hire_dates_stay_inside_the_hiring_window():
    for row in generate_employees(count=500):
        assert HIRING_STARTED <= row["hire_date"] <= HIRING_ENDED


def test_the_data_actually_spreads_across_countries_and_roles():
    rows = list(generate_employees(count=2_000))

    assert len(Counter(row["country_code"] for row in rows)) == 8
    assert len(Counter(row["department"] for row in rows)) == 8
    assert len(Counter(row["role"] for row in rows)) == 10


def test_seniority_is_a_pyramid_not_a_uniform_draw():
    roles = Counter(row["role"] for row in generate_employees(count=5_000))

    assert roles["Analyst"] > roles["Director"] * 5
