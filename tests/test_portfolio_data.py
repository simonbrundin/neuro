import pytest

from portfolio_data import (
    build_table_rows,
    format_value,
    format_weight,
    is_invalid_credentials_text,
    is_locked_text,
    parse_verification_code,
    portfolio_date,
    select_portfolio,
)

PORTFOLIOS = [
    {"id": "a", "title": "NQ Volatilitet & Kvalitet", "updatedAt": "2026-10-15T21:00:00.000Z"},
    {"id": "b", "title": "NQ Värde & Momentum", "updatedAt": "2026-10-29T12:00:00.000Z"},
]


def test_select_portfolio_matches_title_exactly():
    assert select_portfolio(PORTFOLIOS, "NQ Värde & Momentum")["id"] == "b"
    assert select_portfolio(PORTFOLIOS, "NQ Värde") is None


def test_portfolio_date_is_updated_at_date():
    assert portfolio_date(PORTFOLIOS[1]) == "2026-10-29"


def test_build_table_rows_has_header_and_one_row_per_position():
    items = [
        {
            "name": "Attendo",
            "symbol": "ATT.ST",
            "weight": 3.8,
            "updated": "2026-10-29T12:00:00.000Z",
            "calc_number": 12,
            "position_value": 32753.38,
            "increase_decrease": 4,
        }
    ]

    rows = build_table_rows(items)

    assert rows[0][0] == "Bolag"
    assert rows[1] == [
        "Attendo (ATT.ST)",
        "2026-10-29",
        "3.8%",
        "12",
        "32 753 SEK",
        "4",
    ]


def test_build_table_rows_handles_missing_values():
    rows = build_table_rows([{"name": "Bolaget", "symbol": "", "weight": None}])

    assert rows[1][0] == "Bolaget"
    assert rows[1][2] == ""
    assert rows[1][4] == ""


def test_format_weight_adds_percent():
    assert format_weight(3.8) == "3.8%"
    assert format_weight("4.0%") == "4.0%"
    assert format_weight(None) == ""


def test_format_value_uses_space_thousands_separator():
    assert format_value(32753.3816) == "32 753 SEK"
    assert format_value(None) == ""


def test_parse_verification_code_finds_six_digits():
    assert parse_verification_code("303137 is your verification code") == "303137"
    assert parse_verification_code("Din kod är 008731") == "008731"
    assert parse_verification_code("ingen kod här") is None
    assert parse_verification_code("") is None


def test_locked_text_detection():
    assert is_locked_text("Your account has been locked.")
    assert is_locked_text("Kontot är låst")
    assert not is_locked_text("Logga in")


def test_invalid_credentials_detection():
    assert is_invalid_credentials_text("Lösenordet är felaktigt.")
    assert is_invalid_credentials_text("Password is incorrect")
    assert not is_invalid_credentials_text("Välkommen tillbaka")
