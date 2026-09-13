"""Deterministic seed data.

Same seed, same 10,000 people, every run. That matters twice: a reviewer running this gets the
same dashboard I demoed, and a test can assert on a specific row without being flaky.

Pay is not uniform noise. It is a role band in USD, scaled by a country cost factor, jittered, and
only then expressed in the local currency. That gives the dashboard something real to show:
Engineering out-spends everyone, the US out-pays everyone per head, and the median sits well below
the mean because the seniority pyramid is a pyramid.
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from random import Random
from typing import Any

from sqlalchemy import delete, insert, select
from sqlalchemy.orm import Session

from app.domain.countries import BY_CODE
from app.infrastructure.models import Employee, ExchangeRate, SalaryChange

DEFAULT_SEED = 20260906
DEFAULT_COUNT = 10_000

RATES_AS_OF = date(2026, 8, 1)

# usd per one unit of the currency. seeded, never fetched, see the requirements doc.
# every rate here times 100 lands on at most two decimals, so a converted salary is always an
# exact number of cents. a rate that does not is a rounding policy question, not a seeding one.
USD_PER_UNIT: dict[str, Decimal] = {
    "USD": Decimal("1.00000000"),
    "GBP": Decimal("1.27500000"),
    "EUR": Decimal("1.08500000"),
    "AUD": Decimal("0.65800000"),
    "BRL": Decimal("0.18200000"),
    "INR": Decimal("0.01180000"),
    "NPR": Decimal("0.00740000"),
    "JPY": Decimal("0.00670000"),
}

# how expensive it is to hire the same person there, relative to the US
COUNTRY_COST: dict[str, float] = {
    "US": 1.00,
    "GB": 0.85,
    "DE": 0.80,
    "AU": 0.78,
    "JP": 0.72,
    "BR": 0.35,
    "IN": 0.28,
    "NP": 0.20,
}

COUNTRY_WEIGHTS: dict[str, float] = {
    "US": 0.28,
    "IN": 0.30,
    "NP": 0.10,
    "GB": 0.08,
    "DE": 0.08,
    "JP": 0.06,
    "BR": 0.06,
    "AU": 0.04,
}

DEPARTMENT_WEIGHTS: dict[str, float] = {
    "Engineering": 0.32,
    "Sales": 0.16,
    "Support": 0.12,
    "People": 0.10,
    "Marketing": 0.08,
    "Finance": 0.08,
    "Product": 0.08,
    "Design": 0.06,
}

# (role, us midpoint in usd, share of headcount). a pyramid, so the median lands under the mean.
ROLE_BANDS: tuple[tuple[str, int, float], ...] = (
    ("Intern", 24_000, 0.060),
    ("Associate", 45_000, 0.160),
    ("Analyst", 62_000, 0.180),
    ("Specialist", 80_000, 0.180),
    ("Senior Specialist", 105_000, 0.150),
    ("Team Lead", 135_000, 0.110),
    ("Manager", 155_000, 0.080),
    ("Senior Manager", 185_000, 0.050),
    ("Director", 230_000, 0.025),
    ("VP", 310_000, 0.005),
)

FIRST_NAMES = (
    "Aarav", "Ada", "Aiko", "Alan", "Amara", "Anika", "Bianca", "Bikash", "Camila", "Carlos",
    "Chloe", "Daniel", "Deepa", "Elena", "Emeka", "Erik", "Farah", "Felix", "Grace", "Hana",
    "Hiroshi", "Ines", "Isabel", "Jean", "Jonas", "Kabita", "Katherine", "Kenji", "Lars", "Leila",
    "Liam", "Lucia", "Maya", "Mira", "Naveen", "Nikhil", "Olivia", "Omar", "Priya", "Rahul",
    "Rita", "Samir", "Sofia", "Sunita", "Thomas", "Uma", "Victor", "Wei", "Yuki", "Zara",
)

LAST_NAMES = (
    "Adhikari", "Almeida", "Bakshi", "Bartik", "Becker", "Chen", "Costa", "Dhakal", "Dubois",
    "Fernandes", "Fischer", "Gurung", "Hansen", "Hopper", "Iyer", "Johnson", "Kapoor", "Khan",
    "Kimura", "Lovelace", "Martins", "Mehta", "Moreau", "Nakamura", "Novak", "Oliveira", "Pandey",
    "Patel", "Rana", "Reddy", "Ribeiro", "Rossi", "Sato", "Schmidt", "Sharma", "Shrestha",
    "Silva", "Singh", "Tamang", "Tanaka", "Turing", "Verma", "Walsh", "Weber", "Yamada",
)

# some people were hired cheap and never caught up. they are what the peer gap list is for
HIRED_CHEAP_SHARE = 0.03

HIRING_STARTED = date(2016, 1, 4)
HIRING_ENDED = date(2026, 8, 31)
_HIRING_WINDOW_DAYS = (HIRING_ENDED - HIRING_STARTED).days


def _weighted(rng: Random, weights: dict[str, float]) -> str:
    keys = list(weights)
    return rng.choices(keys, weights=[weights[key] for key in keys], k=1)[0]


def _round_to_hundred(value: float) -> Decimal:
    """Nobody is paid 87,431.19. Round the way an offer letter would."""
    return Decimal(int(round(value / 100.0)) * 100).quantize(Decimal("0.01"))


def generate_employees(
    count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED
) -> Iterator[dict[str, Any]]:
    """Pure generator, no database. Determinism is testable without touching SQL."""
    rng = Random(seed)
    role_names = [role for role, _, _ in ROLE_BANDS]
    role_weights = [share for _, _, share in ROLE_BANDS]
    midpoints = {role: midpoint for role, midpoint, _ in ROLE_BANDS}

    for index in range(count):
        first = rng.choice(FIRST_NAMES)
        last = rng.choice(LAST_NAMES)
        country_code = _weighted(rng, COUNTRY_WEIGHTS)
        country = BY_CODE[country_code]
        role = rng.choices(role_names, weights=role_weights, k=1)[0]

        cheap = rng.random() < HIRED_CHEAP_SHARE
        spread = rng.uniform(0.55, 0.75) if cheap else rng.uniform(0.85, 1.20)
        target_usd = midpoints[role] * COUNTRY_COST[country_code] * spread
        native = _round_to_hundred(target_usd / float(USD_PER_UNIT[country.currency]))

        yield {
            "full_name": f"{first} {last}",
            # the index is what guarantees uniqueness, so there is no retry loop on a collision
            "email": f"{first}.{last}{index}@acme.example".lower(),
            "country_code": country_code,
            "department": _weighted(rng, DEPARTMENT_WEIGHTS),
            "role": role,
            "hire_date": HIRING_STARTED + timedelta(days=rng.randint(0, _HIRING_WINDOW_DAYS)),
            "salary_amount": native,
            "currency_code": country.currency,
        }


def seed_exchange_rates(session: Session) -> int:
    session.execute(delete(ExchangeRate))
    rows = [
        {"currency_code": code, "usd_per_unit": rate, "as_of": RATES_AS_OF}
        for code, rate in USD_PER_UNIT.items()
    ]
    session.execute(insert(ExchangeRate), rows)
    return len(rows)


def insert_employees(
    session: Session, count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED, batch_size: int = 1_000
) -> int:
    """Appends. One executemany per batch, because building 10,000 ORM objects to throw them away
    is the slow way. Clearing is `seed_all`'s job, it has to happen before the rates go."""
    written = 0
    batch: list[dict[str, Any]] = []
    for row in generate_employees(count, seed):
        batch.append(row)
        if len(batch) >= batch_size:
            session.execute(insert(Employee), batch)
            written += len(batch)
            batch = []
    if batch:
        session.execute(insert(Employee), batch)
        written += len(batch)
    return written


def seed_all(session: Session, count: int = DEFAULT_COUNT, seed: int = DEFAULT_SEED) -> int:
    # children before parents: history points at employees, employees point at rates
    session.execute(delete(SalaryChange))
    session.execute(delete(Employee))
    seed_exchange_rates(session)
    written = insert_employees(session, count, seed)
    # everyone's history starts with what they were hired on, in one statement
    session.execute(
        insert(SalaryChange).from_select(
            ["employee_id", "changed_on", "new_amount", "new_currency"],
            select(Employee.id, Employee.hire_date, Employee.salary_amount, Employee.currency_code),
        )
    )
    return written
