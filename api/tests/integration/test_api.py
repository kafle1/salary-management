from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.api.deps import get_session
from app.main import create_app
from tests.conftest import add_employee


@pytest.fixture
def client(session: Session) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def staffed(session: Session) -> Session:
    people = [
        ("Ada Lovelace", "US", "Engineering", "Engineer", "120000.00", "USD"),
        ("Grace Hopper", "US", "Engineering", "Manager", "180000.00", "USD"),
        ("Alan Turing", "GB", "Engineering", "Engineer", "90000.00", "EUR"),
        ("Katherine Johnson", "IN", "Finance", "Analyst", "2000000.00", "INR"),
        ("Jean Bartik", "IN", "Finance", "Manager", "3000000.00", "INR"),
    ]
    for name, country, department, role, amount, currency in people:
        add_employee(
            session,
            full_name=name,
            country_code=country,
            department=department,
            role=role,
            salary_amount=amount,
            currency_code=currency,
        )
    session.commit()
    return session


def test_health_is_a_plain_ok(client: TestClient):
    assert client.get("/health").json() == {"status": "ok"}


def test_employees_returns_a_page_envelope(client: TestClient, staffed: Session):
    body = client.get("/employees", params={"page": 1, "page_size": 2}).json()

    assert set(body) == {
        "items",
        "page",
        "page_size",
        "total",
        "total_pages",
        "has_next",
        "has_previous",
    }
    assert body["total"] == 5
    assert body["total_pages"] == 3
    assert body["has_next"] is True
    assert body["has_previous"] is False
    assert len(body["items"]) == 2


def test_the_second_page_is_a_different_slice(client: TestClient, staffed: Session):
    first = client.get("/employees", params={"page": 1, "page_size": 2}).json()
    second = client.get("/employees", params={"page": 2, "page_size": 2}).json()

    assert second["has_previous"] is True
    first_ids = {item["id"] for item in first["items"]}
    second_ids = {item["id"] for item in second["items"]}
    assert first_ids.isdisjoint(second_ids)


def test_money_crosses_the_wire_as_a_fixed_string_not_a_float(client: TestClient, staffed: Session):
    body = client.get(
        "/employees", params={"search": "ada", "page_size": 1}
    ).json()

    salary = body["items"][0]["salary"]
    assert salary == {"amount": "120000.00", "currency": "USD"}
    assert body["items"][0]["salary_in_base"] == {"amount": "120000.00", "currency": "USD"}


def test_filters_are_repeatable_query_parameters(client: TestClient, staffed: Session):
    body = client.get("/employees", params=[("country", "US"), ("country", "GB")]).json()

    assert body["total"] == 3


def test_sorting_by_converted_pay_is_available_over_http(client: TestClient, staffed: Session):
    """The two orders disagree, which is the whole reason conversion has to happen in the query.

    Turing is the lowest paid by the raw number (90,000 EUR) and mid table once it is USD.
    """
    by_usd = client.get(
        "/employees", params={"sort_by": "salary_usd", "sort_dir": "asc", "page_size": 1}
    ).json()
    by_native = client.get(
        "/employees", params={"sort_by": "salary_native", "sort_dir": "asc", "page_size": 1}
    ).json()

    assert by_usd["items"][0]["full_name"] == "Ada Lovelace"
    assert by_native["items"][0]["full_name"] == "Alan Turing"


def test_an_unknown_sort_field_is_a_400_with_a_readable_reason(client: TestClient):
    response = client.get("/employees", params={"sort_by": "wherever"})

    assert response.status_code == 400
    assert "allowed" in response.json()["detail"]


def test_a_page_size_above_the_cap_is_refused(client: TestClient):
    assert client.get("/employees", params={"page_size": 5000}).status_code == 422


def test_filter_options_are_served_from_the_data(client: TestClient, staffed: Session):
    body = client.get("/employees/filter-options").json()

    assert {"code": "IN", "name": "India"} in body["countries"]
    assert body["departments"] == ["Engineering", "Finance"]
    assert body["roles"] == ["Analyst", "Engineer", "Manager"]


def test_dashboard_summary_shape(client: TestClient, staffed: Session):
    body = client.get("/dashboard/summary", params={"group_by": "department"}).json()

    assert body["base_currency"] == "USD"
    assert body["group_by"] == "department"
    assert body["overall"]["headcount"] == 5
    assert set(body["overall"]) == {
        "headcount",
        "total_payroll",
        "average_salary",
        "median_salary",
    }
    assert {group["key"] for group in body["groups"]} == {"Engineering", "Finance"}


def test_dashboard_respects_the_same_filters_as_the_table(client: TestClient, staffed: Session):
    body = client.get("/dashboard/summary", params={"country": "IN"}).json()

    assert body["overall"]["headcount"] == 2
    # 2,000,000 and 3,000,000 INR at 0.5
    assert body["overall"]["total_payroll"] == "2500000.00"
    assert body["overall"]["median_salary"] == "1250000.00"


def test_an_empty_selection_returns_zeroes_rather_than_nulls_for_the_count(
    client: TestClient, staffed: Session
):
    body = client.get("/dashboard/summary", params={"search": "nobody"}).json()

    assert body["overall"]["headcount"] == 0
    assert body["overall"]["total_payroll"] == "0.00"
    assert body["overall"]["average_salary"] is None
    assert body["groups"] == []


def test_an_unknown_grouping_is_a_400(client: TestClient):
    response = client.get("/dashboard/summary", params={"group_by": "astrology"})

    assert response.status_code == 400
