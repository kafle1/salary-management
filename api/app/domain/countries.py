"""The countries this org pays people in, and what they are paid in.

A lookup table would be the right shape if HR could add countries. They cannot: adding one means
adding an exchange rate and a pay band, which is a deploy either way. So it lives in code, where
it is one import instead of a join.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Country:
    code: str
    name: str
    currency: str


COUNTRIES: tuple[Country, ...] = (
    Country("US", "United States", "USD"),
    Country("GB", "United Kingdom", "GBP"),
    Country("DE", "Germany", "EUR"),
    Country("IN", "India", "INR"),
    Country("NP", "Nepal", "NPR"),
    Country("JP", "Japan", "JPY"),
    Country("BR", "Brazil", "BRL"),
    Country("AU", "Australia", "AUD"),
)

BY_CODE: dict[str, Country] = {country.code: country for country in COUNTRIES}


def name_for(code: str) -> str:
    """Fall back to the code itself, so an unknown country shows up rather than crashing a page."""
    country = BY_CODE.get(code.upper())
    return country.name if country else code
