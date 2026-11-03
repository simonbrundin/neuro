import pytest

from monitor import get_portfolio_changes, is_significant, parse_weight


def portfolio(rows):
    return {"date": "2026-11-03", "data": [["Bolag", "Datum", "Vikt"]] + rows}


def row(name, weight):
    return [name, "2026-11-03", weight]


def test_parse_weight_handles_percent_and_comma():
    assert parse_weight("3.8%") == 3.8
    assert parse_weight("3,8%") == 3.8
    assert parse_weight(3.8) == 3.8
    assert parse_weight("") is None
    assert parse_weight(None) is None


def test_is_significant_is_strictly_greater_than_threshold():
    assert is_significant("0.21%", 0.2) is True
    assert is_significant("0.2%", 0.2) is False
    assert is_significant("0.19%", 0.2) is False


def test_change_exactly_at_threshold_is_filtered():
    previous = portfolio([row("AAPL", "10.0%")])
    current = portfolio([row("AAPL", "10.2%")])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert changes["increased"] == []
    assert changes["decreased"] == []


def test_change_above_threshold_is_reported():
    previous = portfolio([row("AAPL", "10.0%")])
    current = portfolio([row("AAPL", "10.21%")])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert changes["increased"] == [
        {"name": "AAPL", "old_weight": "10.0%", "new_weight": "10.21%"}
    ]


def test_small_added_position_is_filtered():
    previous = portfolio([])
    current = portfolio([row("LILLEN", "0.1%")])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert changes["added"] == []


def test_large_added_position_is_reported():
    previous = portfolio([])
    current = portfolio([row("NYTT", "1.5%")])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert changes["added"] == [{"name": "NYTT", "new_weight": "1.5%"}]


def test_small_removed_position_is_filtered():
    previous = portfolio([row("LILLEN", "0.1%")])
    current = portfolio([])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert changes["removed"] == []


def test_large_removed_position_is_reported():
    previous = portfolio([row("GAMMAL", "2.0%")])
    current = portfolio([])

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert changes["removed"] == [{"name": "GAMMAL", "old_weight": "2.0%"}]


def test_unchanged_portfolio_gives_no_changes():
    rows = [row("AAPL", "10.0%"), row("MSFT", "5.0%")]
    previous = portfolio(rows)
    current = portfolio(rows)

    changes = get_portfolio_changes(current, previous, threshold=0.2)

    assert not any(changes.values())


@pytest.mark.parametrize("threshold", [0.2, 0.5, 1.0])
def test_threshold_is_applied_per_position(threshold):
    previous = portfolio([row("AAPL", "10.0%"), row("MSFT", "5.0%")])
    current = portfolio([row("AAPL", "10.1%"), row("MSFT", f"{5 + threshold + 0.1}%")])

    changes = get_portfolio_changes(current, previous, threshold=threshold)

    # AAPL ändrades för lite - filtreras bort.
    assert all(change["name"] != "AAPL" for change in changes["increased"])
    # MSFT ändrades mer än tröskeln - rapporteras.
    assert any(change["name"] == "MSFT" for change in changes["increased"])
