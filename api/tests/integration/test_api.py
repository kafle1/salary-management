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
        "lowest_salary",
        "highest_salary",
    }
    assert {group["key"] for group in body["groups"]} == {"Engineering", "Finance"}
    assert set(body["bands"][0]) == {"lower", "upper", "headcount"}
    assert sum(band["headcount"] for band in body["bands"]) == 5


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
    assert body["bands"] == []


def test_an_unknown_grouping_is_a_400(client: TestClient):
    response = client.get("/dashboard/summary", params={"group_by": "astrology"})

    assert response.status_code == 400


def test_people_paid_well_under_their_peers(client: TestClient, session: Session):
    for index, amount in enumerate(["100000.00"] * 4 + ["70000.00"]):
        add_employee(session, full_name=f"Engineer {index}", salary_amount=amount)
    session.commit()

    body = client.get("/dashboard/below-peers", params={"country": "US"}).json()

    assert body["threshold_percent"] == 80
    assert body["min_peers"] == 5
    assert body["total"] == 1
    [gap] = body["items"]
    assert gap["employee"]["full_name"] == "Engineer 4"
    assert gap["peer_median"] == {"amount": "100000.00", "currency": "USD"}
    assert gap["peers"] == 5
    assert gap["percent_of_median"] == 70


def test_the_peer_gap_list_refuses_a_silly_limit(client: TestClient):
    assert client.get("/dashboard/below-peers", params={"limit": 0}).status_code == 422
    assert client.get("/dashboard/below-peers", params={"limit": 1000}).status_code == 422


def new_hire(**overrides) -> dict:
    body = {
        "full_name": "Mary Jackson",
        "email": "mary@acme.test",
        "country_code": "DE",
        "department": "Engineering",
        "role": "Engineer",
        "hire_date": "2025-02-03",
        "salary_amount": "60000",
    }
    body.update(overrides)
    return body


def test_adding_someone_returns_them_in_the_currency_their_country_pays(client: TestClient):
    response = client.post("/employees", json=new_hire())

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "mary@acme.test"
    assert body["salary"] == {"amount": "60000.00", "currency": "EUR"}
    assert body["salary_in_base"] == {"amount": "120000.00", "currency": "USD"}


def test_a_bad_form_names_every_field_that_needs_fixing(client: TestClient):
    response = client.post(
        "/employees", json={"full_name": " ", "email": "nope", "salary_amount": "-5"}
    )

    assert response.status_code == 422
    errors = response.json()["errors"]
    assert set(errors) == {
        "full_name",
        "email",
        "country_code",
        "department",
        "role",
        "hire_date",
        "salary_amount",
    }


def test_an_email_already_on_file_is_a_409_pointing_at_the_email_field(client: TestClient):
    client.post("/employees", json=new_hire())

    response = client.post("/employees", json=new_hire(full_name="Someone Else"))

    assert response.status_code == 409
    assert "email" in response.json()["errors"]


def test_one_employee_comes_with_their_salary_history(client: TestClient):
    created = client.post("/employees", json=new_hire(salary_note="Offer")).json()

    body = client.get(f"/employees/{created['id']}").json()

    assert body["full_name"] == "Mary Jackson"
    assert body["history"] == [
        {
            "changed_on": body["history"][0]["changed_on"],
            "previous": None,
            "new": {"amount": "60000.00", "currency": "EUR"},
            "note": "Offer",
        }
    ]


def test_a_raise_shows_up_first_in_the_history(client: TestClient):
    created = client.post("/employees", json=new_hire()).json()

    response = client.put(
        f"/employees/{created['id']}", json=new_hire(salary_amount="65000", salary_note="Review")
    )

    assert response.status_code == 200
    assert response.json()["salary"]["amount"] == "65000.00"
    latest = client.get(f"/employees/{created['id']}").json()["history"][0]
    assert latest["previous"] == {"amount": "60000.00", "currency": "EUR"}
    assert latest["note"] == "Review"


def test_someone_who_does_not_exist_is_a_404_on_every_verb(client: TestClient):
    assert client.get("/employees/999").status_code == 404
    assert client.put("/employees/999", json=new_hire()).status_code == 404
    assert client.delete("/employees/999").status_code == 404


def test_deleting_someone_removes_them(client: TestClient):
    created = client.post("/employees", json=new_hire()).json()

    assert client.delete(f"/employees/{created['id']}").status_code == 204
    assert client.get(f"/employees/{created['id']}").status_code == 404


def test_the_form_gets_its_countries_and_currencies_from_the_api(client: TestClient):
    countries = client.get("/countries").json()

    assert {"code": "DE", "name": "Germany", "currency": "EUR"} in countries
    assert len(countries) == 8
