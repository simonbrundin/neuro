"""Tester för publiceringslogiken.

Vikterna på NeuroQuant-sajten räknas om löpande, så en viktändring ensam
betyder inte att portföljen har publicerats om. Bara en ny publicering
(datum/updatedAt) ska utlösa en jämförelse.
"""

from monitor import get_portfolio_changes, is_new_publication


def portfolio(date, rows, updated_at=""):
    data = {"date": date, "data": [["Bolag", "Datum", "Vikt"]] + rows}
    if updated_at:
        data["updated_at"] = updated_at
    return data


def row(name, weight):
    return [name, date_of(rows), weight]


def date_of(rows):
    return rows[0][1] if rows else ""


def test_same_date_is_not_a_new_publication():
    previous = portfolio("2026-10-29", [["AAPL", "2026-10-29", "10.0%"]])
    current = portfolio("2026-10-29", [["AAPL", "2026-10-29", "9.5%"]])

    assert is_new_publication(current, previous) is False


def test_new_date_is_a_new_publication():
    previous = portfolio("2026-10-29", [["AAPL", "2026-10-29", "10.0%"]])
    current = portfolio("2026-11-26", [["AAPL", "2026-11-26", "9.5%"]])

    assert is_new_publication(current, previous) is True


def test_updated_at_detects_republication_on_same_day():
    previous = portfolio(
        "2026-10-29", [["AAPL", "2026-10-29", "10.0%"]], "2026-10-29T12:00:00.000Z"
    )
    current = portfolio(
        "2026-10-29", [["AAPL", "2026-10-29", "9.5%"]], "2026-10-29T18:00:00.000Z"
    )

    assert is_new_publication(current, previous) is True


def test_same_updated_at_is_not_a_new_publication():
    previous = portfolio(
        "2026-10-29", [["AAPL", "2026-10-29", "10.0%"]], "2026-10-29T12:00:00.000Z"
    )
    current = portfolio(
        "2026-10-29", [["AAPL", "2026-10-29", "9.5%"]], "2026-10-29T12:00:00.000Z"
    )

    assert is_new_publication(current, previous) is False


def test_without_previous_state_it_is_not_a_publication():
    current = portfolio("2026-10-29", [["AAPL", "2026-10-29", "10.0%"]])

    assert is_new_publication(current, {}) is False


def test_daily_drift_below_threshold_gives_no_changes():
    previous = portfolio("2026-10-29", [["AAPL", "2026-10-29", "10.0%"]])
    current = portfolio("2026-10-29", [["AAPL", "2026-10-29", "9.9%"]])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert not any(changes.values())


def test_daily_drift_above_threshold_shows_up_as_change():
    # Detta hände 2026-11-03: vikterna räknades om utan ny publicering.
    # Storleksordningen är korrekt, men is_new_publication() ska ändå
    # stoppa en notis eftersom ingen ny publicering skedde.
    previous = portfolio("2026-10-29", [["AAPL", "2026-10-29", "3.4%"]])
    current = portfolio("2026-10-29", [["AAPL", "2026-10-29", "3.1%"]])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert changes["decreased"]
    assert is_new_publication(current, previous) is False
