from decimal import Decimal

import pytest

from app.domain.money import BASE_CURRENCY, ExchangeRate, Money


def test_money_keeps_the_amount_the_employee_is_actually_paid():
    salary = Money(Decimal("8500000"), "IDR")

    assert salary.amount == Decimal("8500000")
    assert salary.currency == "IDR"


def test_money_normalises_the_currency_code():
    assert Money(Decimal("100"), "usd").currency == "USD"
    assert Money(Decimal("100"), " eur ").currency == "EUR"


@pytest.mark.parametrize("code", ["", "US", "USDD", "12A"])
def test_money_rejects_a_currency_that_is_not_three_letters(code):
    with pytest.raises(ValueError):
        Money(Decimal("100"), code)


def test_money_rejects_a_negative_salary():
    with pytest.raises(ValueError):
        Money(Decimal("-1"), "USD")


def test_money_rounds_to_two_places_half_up():
    assert Money(Decimal("100.005"), "USD").amount == Decimal("100.01")
    assert Money(Decimal("100.004"), "USD").amount == Decimal("100.00")


def test_rate_converts_a_native_salary_to_the_base_currency():
    rate = ExchangeRate("INR", Decimal("0.01200000"))

    assert rate.to_base(Money(Decimal("2500000"), "INR")) == Money(Decimal("30000.00"), "USD")


def test_rate_rounds_the_converted_amount_to_cents():
    rate = ExchangeRate("JPY", Decimal("0.00666000"))

    assert rate.to_base(Money(Decimal("7000000"), "JPY")).amount == Decimal("46620.00")


def test_base_currency_rate_is_the_identity():
    rate = ExchangeRate(BASE_CURRENCY, Decimal("1"))
    salary = Money(Decimal("142000.00"), "USD")

    assert rate.to_base(salary) == salary


def test_rate_refuses_a_salary_in_a_different_currency():
    rate = ExchangeRate("INR", Decimal("0.012"))

    with pytest.raises(ValueError, match="INR"):
        rate.to_base(Money(Decimal("100"), "GBP"))


@pytest.mark.parametrize("value", ["0", "-0.5"])
def test_rate_must_be_positive(value):
    with pytest.raises(ValueError):
        ExchangeRate("INR", Decimal(value))
