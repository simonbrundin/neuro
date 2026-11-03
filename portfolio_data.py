"""Formatering och tolkning av NeuroQuant-portföljdata.

Hålls separat från scraper.py (som gör webbläsaranrop) så att logiken kan
testas utan browser.
"""

from datetime import datetime
import re

LOCK_MARKERS = (
    "account locked",
    "account has been locked",
    "temporarily restricted",
    "åtkomst har begränsats",
    "kontot är låst",
    "kontot har låsts",
)

INVALID_MARKERS = (
    "invalid credentials",
    "incorrect password",
    "password is incorrect",
    "wrong password",
    "lösenordet är felaktigt",
    "felaktigt lösenord",
    "ogiltigt lösenord",
    "ogiltiga inloggningsuppgifter",
)

TABLE_HEADER = [
    "Bolag",
    "Datum",
    "Justerad vikt (InvVol 100%)",
    "Antal aktier (beräkning)",
    "Nominellt värde",
    "Öka/minska",
]


def select_portfolio(portfolios: list[dict], title: str) -> dict | None:
    """Returnerar portföljen med exakt matchande titel."""
    for portfolio in portfolios:
        if portfolio.get("title") == title:
            return portfolio
    return None


def portfolio_date(portfolio: dict) -> str:
    """Portföljens datumpunkt, t.ex. '2026-10-29'."""
    raw = portfolio.get("updatedAt", "")
    return raw[:10] if raw else ""


def format_weight(weight) -> str:
    """Formaterar vikt som i tabellen, t.ex. 3.8 -> '3.8%'."""
    if weight is None:
        return ""
    if isinstance(weight, str):
        return weight if weight.endswith("%") else f"{weight}%"
    return f"{weight}%"


def format_value(value) -> str:
    """Formaterar nominellt värde, t.ex. 32753.38 -> '32 753 SEK'."""
    if value is None:
        return ""
    try:
        return f"{float(value):,.0f} SEK".replace(",", " ")
    except (TypeError, ValueError):
        return str(value)


def build_table_rows(items: list[dict]) -> list[list[str]]:
    """Bygger tabellrader i samma format som monitorn historiskt använt.

    Varje rad: [namn (symbol), datum, vikt, antal aktier, nominellt värde, öka/minska]
    """
    rows: list[list[str]] = [list(TABLE_HEADER)]

    for item in items:
        name = item.get("name", "")
        symbol = item.get("symbol", "")
        label = f"{name} ({symbol})" if symbol else name
        date = (item.get("updated") or "")[:10]

        rows.append(
            [
                label,
                date,
                format_weight(item.get("weight")),
                str(item.get("calc_number") or ""),
                format_value(item.get("position_value")),
                str(item.get("increase_decrease") if item.get("increase_decrease") is not None else ""),
            ]
        )

    return rows


def parse_verification_code(text: str) -> str | None:
    """Plockar ut en 6-siffrig verifieringskod ur ett e-postbrev."""
    if not text:
        return None

    fallback = None
    for line in text.splitlines():
        matches = re.findall(r"(?<!\d)(\d{6})(?!\d)", line)
        if not matches:
            continue
        if "kod" in line.lower() or "code" in line.lower():
            return matches[0]
        if fallback is None:
            fallback = matches[0]

    return fallback


def is_locked_text(text: str) -> bool:
    """Sant om texten visar att kontot är låst."""
    lowered = (text or "").lower()
    return any(marker in lowered for marker in LOCK_MARKERS)


def is_invalid_credentials_text(text: str) -> bool:
    """Sant om texten visar att lösenordet inte stämmer."""
    lowered = (text or "").lower()
    return any(marker in lowered for marker in INVALID_MARKERS)


def parse_email_date(value: str) -> datetime | None:
    """Tolkar ett e-postdatum, returnerar None om det inte går."""
    if not value:
        return None
    try:
        from email.utils import parsedate_to_datetime

        return parsedate_to_datetime(value)
    except (TypeError, ValueError):
        return None
