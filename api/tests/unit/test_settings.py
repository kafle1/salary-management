from __future__ import annotations

import pytest

from app.settings import Settings


@pytest.mark.parametrize(
    "given",
    [
        "postgres://u:p@host/db?sslmode=require",
        "postgresql://u:p@host/db?sslmode=require",
        "postgresql+psycopg://u:p@host/db?sslmode=require",
    ],
)
def test_database_url_always_uses_psycopg(given):
    assert Settings(database_url=given).database_url == "postgresql+psycopg://u:p@host/db?sslmode=require"


def test_cors_origins_split_on_commas_and_skip_blanks():
    assert Settings(cors_origins=" https://a.example, ,https://b.example ").allowed_origins == [
        "https://a.example",
        "https://b.example",
    ]
