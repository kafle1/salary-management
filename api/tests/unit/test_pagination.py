import pytest

from app.domain.pagination import MAX_PAGE_SIZE, Page, PageRequest


def test_first_page_starts_at_offset_zero():
    request = PageRequest(page=1, page_size=50)

    assert request.offset == 0
    assert request.limit == 50


def test_offset_skips_the_pages_before_it():
    assert PageRequest(page=2, page_size=50).offset == 50
    assert PageRequest(page=200, page_size=50).offset == 9950


@pytest.mark.parametrize("page", [0, -1])
def test_page_numbers_start_at_one(page):
    with pytest.raises(ValueError):
        PageRequest(page=page, page_size=25)


@pytest.mark.parametrize("size", [0, -5, MAX_PAGE_SIZE + 1])
def test_page_size_is_capped_so_one_request_cannot_pull_the_table(size):
    with pytest.raises(ValueError):
        PageRequest(page=1, page_size=size)


def test_page_size_at_the_cap_is_allowed():
    assert PageRequest(page=1, page_size=MAX_PAGE_SIZE).limit == MAX_PAGE_SIZE


def test_total_pages_rounds_up_on_a_partial_last_page():
    page = Page(items=[], total=10_000, request=PageRequest(page=1, page_size=30))

    assert page.total_pages == 334


def test_an_empty_result_has_no_pages_and_no_next():
    page = Page(items=[], total=0, request=PageRequest(page=1, page_size=25))

    assert page.total_pages == 0
    assert page.has_next is False
    assert page.has_previous is False


def test_the_last_page_reports_no_next():
    request = PageRequest(page=400, page_size=25)
    page = Page(items=[object()], total=10_000, request=request)

    assert page.total_pages == 400
    assert page.has_next is False
    assert page.has_previous is True


def test_a_middle_page_has_both_neighbours():
    page = Page(items=[object()], total=10_000, request=PageRequest(page=2, page_size=50))

    assert page.has_next is True
    assert page.has_previous is True


def test_a_page_past_the_end_is_empty_rather_than_an_error():
    page = Page(items=[], total=10, request=PageRequest(page=99, page_size=25))

    assert page.items == []
    assert page.has_next is False
