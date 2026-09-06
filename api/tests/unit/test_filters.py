import pytest

from app.domain.filters import (
    EmployeeFilter,
    SortDirection,
    SortField,
    SortSpec,
    UnknownSortField,
)


def test_sorting_defaults_to_name_ascending():
    spec = SortSpec.parse(None, None)

    assert spec == SortSpec(SortField.NAME, SortDirection.ASC)


def test_sort_field_is_case_and_whitespace_forgiving():
    assert SortSpec.parse(" Salary_USD ", "DESC") == SortSpec(
        SortField.SALARY_USD, SortDirection.DESC
    )


def test_an_unknown_sort_field_is_refused_not_passed_through():
    with pytest.raises(UnknownSortField) as exc:
        SortSpec.parse("salary_usd; drop table employees", "asc")

    assert "allowed" in str(exc.value)


def test_an_unknown_direction_is_refused():
    with pytest.raises(UnknownSortField):
        SortSpec.parse("name", "sideways")


def test_filter_uppercases_country_codes():
    assert EmployeeFilter.build(countries=["in", "de"]).countries == ("IN", "DE")


def test_filter_drops_blanks_and_duplicates_but_keeps_order():
    filters = EmployeeFilter.build(departments=["Engineering", "  ", "Sales", "Engineering"])

    assert filters.departments == ("Engineering", "Sales")


def test_a_whitespace_only_search_is_no_search():
    assert EmployeeFilter.build(search="   ").search is None


def test_search_is_trimmed():
    assert EmployeeFilter.build(search="  ada  ").search == "ada"


def test_an_untouched_filter_is_empty():
    assert EmployeeFilter.build().is_empty is True
    assert EmployeeFilter.build(roles=["Engineer"]).is_empty is False
