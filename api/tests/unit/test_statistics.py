from decimal import Decimal

from app.domain.statistics import median


def test_median_of_nothing_is_none():
    assert median([]) is None


def test_median_of_one_value_is_that_value():
    assert median([Decimal("42.00")]) == Decimal("42.00")


def test_median_of_an_odd_count_is_the_middle_value():
    assert median([Decimal("10"), Decimal("30"), Decimal("20")]) == Decimal("20")


def test_median_of_an_even_count_averages_the_two_middle_values():
    values = [Decimal("10"), Decimal("20"), Decimal("30"), Decimal("40")]

    assert median(values) == Decimal("25.00")


def test_median_of_an_even_count_rounds_to_cents():
    assert median([Decimal("10.00"), Decimal("10.01")]) == Decimal("10.01")


def test_median_does_not_care_about_input_order():
    ascending = [Decimal(n) for n in (1, 2, 3, 4, 5)]
    shuffled = [Decimal(n) for n in (5, 1, 4, 2, 3)]

    assert median(ascending) == median(shuffled)


def test_median_is_not_the_mean():
    # one huge outlier is exactly why the dashboard shows both
    values = [Decimal("50000"), Decimal("52000"), Decimal("54000"), Decimal("5000000")]

    assert median(values) == Decimal("53000.00")
