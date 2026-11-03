import asyncio
import json
from unittest.mock import AsyncMock, MagicMock

import pytest

import scraper as scraper_module
from scraper import AccountLockedError, InvalidCredentialsError, NeuroQuantScraper


@pytest.fixture(autouse=True)
def instant_sleep(monkeypatch):
    """Sparar tid - vänta inte på riktiga timeouts i testerna."""

    async def no_sleep(_seconds):
        return None

    monkeypatch.setattr(scraper_module.asyncio, "sleep", no_sleep)


def make_page(body_text="", url="https://app.neuroquant.ai/se/login"):
    page = MagicMock()
    page.url = url
    page.goto = AsyncMock()
    page.wait_for_load_state = AsyncMock()
    page.fill = AsyncMock()
    page.click = AsyncMock()
    page.type = AsyncMock()
    page.wait_for_selector = AsyncMock(return_value=None)
    page.inner_text = AsyncMock(return_value=body_text)
    page.keyboard = MagicMock()
    page.keyboard.press = AsyncMock()
    return page


def make_context(page):
    context = MagicMock()
    context.add_cookies = AsyncMock()
    context.cookies = AsyncMock(return_value=[])
    context.request = MagicMock()
    context.request.post = AsyncMock()
    return context


def make_scraper(page, context):
    instance = NeuroQuantScraper()
    instance.page = page
    instance.context = context
    return instance


def test_login_uses_valid_cookies_without_typing_password(monkeypatch):
    monkeypatch.setattr(scraper_module, "COOKIE_FILE", MagicMock(exists=MagicMock(return_value=True)))
    monkeypatch.setattr(
        scraper_module.NeuroQuantScraper,
        "_load_cookies",
        lambda self: [{"name": "__session", "value": "x"}],
    )
    monkeypatch.setattr(
        scraper_module.NeuroQuantScraper, "_save_cookies", AsyncMock()
    )

    page = make_page(body_text="Modellportföljer Start", url="https://app.neuroquant.ai/se/home")
    context = make_context(page)
    instance = make_scraper(page, context)

    assert asyncio.run(instance.login()) is True
    page.fill.assert_not_called()
    page.click.assert_not_called()


def test_login_falls_back_to_password_when_cookies_expired(monkeypatch):
    monkeypatch.setattr(
        scraper_module.NeuroQuantScraper, "_load_cookies", lambda self: []
    )
    monkeypatch.setattr(
        scraper_module.NeuroQuantScraper, "_save_cookies", AsyncMock()
    )

    page = make_page(body_text="Logga in Välkommen tillbaka")
    page.inner_text = AsyncMock(
        side_effect=[
            "Logga in Välkommen tillbaka",
            "Lösenordet är felaktigt.",
            "Lösenordet är felaktigt.",
        ]
    )
    context = make_context(page)
    instance = make_scraper(page, context)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(instance.login())

    page.fill.assert_any_call("input[type='email']", scraper_module.config.neuro_email)
    page.fill.assert_any_call(
        "input[type='password']", scraper_module.config.neuro_password
    )
    page.click.assert_called_once()


def test_login_raises_when_account_is_locked(monkeypatch):
    monkeypatch.setattr(
        scraper_module.NeuroQuantScraper, "_load_cookies", lambda self: []
    )

    page = make_page(body_text="Your account has been locked. Access restricted.")
    context = make_context(page)
    instance = make_scraper(page, context)

    with pytest.raises(AccountLockedError):
        asyncio.run(instance.login())


def test_login_raises_when_password_is_incorrect(monkeypatch):
    monkeypatch.setattr(
        scraper_module.NeuroQuantScraper, "_load_cookies", lambda self: []
    )

    page = make_page(body_text="Lösenordet är felaktigt.")
    context = make_context(page)
    instance = make_scraper(page, context)

    with pytest.raises(InvalidCredentialsError):
        asyncio.run(instance.login())


def api_response(payload):
    response = MagicMock()
    response.status = 200
    response.text = AsyncMock(return_value=json.dumps(payload))
    return response


def test_fetch_portfolio_selects_target_portfolio_and_formats_rows():
    listing = [
        {
            "result": {
                "data": [
                    {
                        "id": "other",
                        "title": "NQ Volatilitet & Kvalitet",
                        "updatedAt": "2026-10-15T21:00:00.000Z",
                        "tag": "Portfolio",
                    },
                    {
                        "id": "target",
                        "title": "NQ Värde & Momentum",
                        "updatedAt": "2026-10-29T12:00:00.000Z",
                        "tag": "Portfolio",
                        "descriptionSE": "beskrivning",
                    },
                ]
            }
        }
    ]
    holdings = [
        {
            "result": {
                "data": {
                    "items": [
                        {
                            "name": "Attendo",
                            "symbol": "ATT.ST",
                            "weight": 3.8,
                            "updated": "2026-10-29T12:00:00.000Z",
                        }
                    ],
                    "totalCount": 1,
                }
            }
        }
    ]

    page = make_page()
    context = make_context(page)
    context.request.post = AsyncMock(
        side_effect=[api_response(listing), api_response(holdings)]
    )
    instance = make_scraper(page, context)

    result = asyncio.run(instance.fetch_portfolio())

    assert result["date"] == "2026-10-29"
    assert result["data"][1][0] == "Attendo (ATT.ST)"
    assert result["data"][1][2] == "3.8%"

    second_payload = context.request.post.await_args_list[1].kwargs["data"]
    watchlist = second_payload["0"]["externalFilters"]["portfolioWatchlist"]
    assert watchlist["id"] == "target"
    assert watchlist["label"] == "NQ Värde & Momentum"


def test_fetch_portfolio_raises_when_portfolio_is_missing():
    listing = [{"result": {"data": [{"id": "x", "title": "NQ Volatilitet & Kvalitet"}]}}]

    page = make_page()
    context = make_context(page)
    context.request.post = AsyncMock(return_value=api_response(listing))
    instance = make_scraper(page, context)

    with pytest.raises(RuntimeError, match="NQ Värde & Momentum"):
        asyncio.run(instance.fetch_portfolio())
