"""Hämtar NQ Värde & Momentum från NeuroQuant.

NeuroQuant exponerar ett tRPC-API (app.neuroquant.ai/api/trpc) som ger
strukturerad portföljdata - det används i stället för DOM-skrapping.

Inloggning sker i två steg:
1. Finns giltiga cookies (cookies.json) används de direkt.
2. Annars loggas in med e-post/lösenord. Kontot kräver ett 6-siffrigt
   verifieringskode som skickas till e-post - koden hämtas automatiskt
   från inkorgen via IMAP (EMAIL_USER/EMAIL_PASSWORD).
"""

import asyncio
import imaplib
import json
import time
from datetime import datetime, timedelta
from email import message_from_bytes
from pathlib import Path

from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from config import config
from portfolio_data import (
    build_table_rows,
    is_invalid_credentials_text,
    is_locked_text,
    parse_email_date,
    parse_verification_code,
    portfolio_date,
    select_portfolio,
)

BASE_DIR = Path(__file__).parent
COOKIE_FILE = BASE_DIR / "cookies.json"

API_BASE = "https://app.neuroquant.ai/api/trpc"
PORTFOLIO_LIST_API = f"{API_BASE}/watchlist.get,strategy.getPortfolioData?batch=1"
PORTFOLIO_DATA_API = f"{API_BASE}/strategy.getPortfolioData?batch=1"

LOGIN_URL = "https://app.neuroquant.ai/se/login"
HOME_URL = "https://app.neuroquant.ai/se/home"

TARGET_PORTFOLIO = "NQ Värde & Momentum"

CODE_INPUT_SELECTORS = [
    "input[autocomplete='one-time-code']",
    "input[name='code']",
    "input[id*='code' i]",
    "input[inputmode='numeric']",
    "input[placeholder*='kod' i]",
    "input[type='text']",
]


class AccountLockedError(Exception):
    """Kontot är låst av NeuroQuant - inga fler inloggningsförsök får göras."""


class InvalidCredentialsError(Exception):
    """Inloggningen misslyckades - lösenordet stämmer inte."""


class VerificationCodeError(Exception):
    """Kunde inte hämta verifieringskoden från inkorgen."""


def fetch_verification_code(since: datetime, timeout: int = 120) -> str | None:
    """Hämtar den senaste 6-siffrig verifieringskoden ur inkorgen."""
    deadline = datetime.now().timestamp() + timeout
    while datetime.now().timestamp() < deadline:
        code = _search_inbox_for_code(since)
        if code:
            return code
        time.sleep(5)
    return None


def _search_inbox_for_code(since: datetime) -> str | None:
    """Ett IMAP-anrop som letar efter ett brev med verifieringskod."""
    try:
        mail = imaplib.IMAP4_SSL(config.imap_host)
        mail.login(config.email_user, config.email_password)
        mail.select("INBOX")
        _, data = mail.search(None, "ALL")
        ids = data[0].split()[-20:]

        for message_id in reversed(ids):
            _, response = mail.fetch(message_id, "(RFC822)")
            if not response or not response[0]:
                continue

            message = message_from_bytes(response[0][1])
            subject = str(message.get("Subject", ""))
            sender = str(message.get("From", ""))
            body = ""
            for part in message.walk():
                if part.get_content_type() == "text/plain":
                    body += part.get_payload(decode=True).decode(errors="replace")

            if "neuroquant" not in f"{subject} {sender}".lower():
                continue

            sent = parse_email_date(message.get("Date"))
            if since and sent and sent <= since:
                continue

            code = parse_verification_code(f"{subject}\n{body}")
            if code:
                mail.logout()
                return code

        mail.logout()
    except Exception as e:
        print(f"IMAP-fel: {e}")

    return None


class NeuroQuantScraper:
    def __init__(self):
        self.playwright = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()

    # ------------------------------------------------------------------
    # cookies
    # ------------------------------------------------------------------

    def _load_cookies(self) -> list:
        if COOKIE_FILE.exists():
            try:
                return json.loads(COOKIE_FILE.read_text())
            except (json.JSONDecodeError, OSError):
                return []
        return []

    async def _save_cookies(self) -> None:
        if not self.context:
            return
        cookies = await self.context.cookies()
        if cookies:
            COOKIE_FILE.write_text(json.dumps(cookies, indent=2))

    # ------------------------------------------------------------------
    # inloggning
    # ------------------------------------------------------------------

    async def _body_text(self) -> str:
        if not self.page:
            return ""
        try:
            return await self.page.inner_text("body")
        except Exception:
            return ""

    async def _is_logged_in(self) -> bool:
        text = await self._body_text()
        return "/login" not in self.page.url and "Modellportföljer" in text

    async def login(self) -> bool:
        """Loggar in (via cookies eller lösenord + verifieringskod)."""
        cookies = self._load_cookies()
        if cookies:
            await self.context.add_cookies(cookies)
            await self.page.goto(HOME_URL)
            await self.page.wait_for_load_state("domcontentloaded")
            await asyncio.sleep(3)
            if await self._is_logged_in():
                print("Already logged in via cookies")
                return True
            print("Cookies expired, logging in with password")

        await self.page.goto(LOGIN_URL)
        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(2)

        text = await self._body_text()
        if is_locked_text(text):
            raise AccountLockedError("NeuroQuant har låst kontot")

        await self.page.fill("input[type='email']", config.neuro_email)
        await self.page.fill("input[type='password']", config.neuro_password)
        await self.page.click("button[type='submit']")
        await asyncio.sleep(5)

        text = await self._body_text()
        if is_locked_text(text):
            raise AccountLockedError("NeuroQuant har låst kontot")

        if await self._is_logged_in():
            print("Logged in with password")
            await self._save_cookies()
            return True

        if is_invalid_credentials_text(text):
            raise InvalidCredentialsError("NeuroQuant avvisade inloggningsuppgifterna")

        await self._complete_verification()

        if await self._is_logged_in():
            print("Logged in with verification code")
            await self._save_cookies()
            return True

        raise InvalidCredentialsError("Inloggningen misslyckades trots verifieringskod")

    async def _complete_verification(self) -> None:
        """Hämtar och fyller i det 6-siffriga verifieringskoden."""
        selector = None
        for candidate in CODE_INPUT_SELECTORS:
            try:
                if await self.page.wait_for_selector(candidate, timeout=3000):
                    selector = candidate
                    break
            except Exception:
                continue

        if not selector:
            raise VerificationCodeError("Hittade inte fält för verifieringskod")

        code = await asyncio.to_thread(
            fetch_verification_code, datetime.now() - timedelta(minutes=5)
        )
        if not code:
            raise VerificationCodeError("Fick ingen verifieringskod från inkorgen")

        print(f"Using verification code from inbox ({len(code)} digits)")
        await self.page.fill(selector, "")
        await self.page.type(selector, code)
        await self.page.keyboard.press("Enter")
        await asyncio.sleep(6)

    # ------------------------------------------------------------------
    # data
    # ------------------------------------------------------------------

    async def _post(self, url: str, payload: dict) -> dict:
        response = await self.context.request.post(url, data=payload)
        body = await response.text()
        if response.status != 200:
            raise RuntimeError(f"NeuroQuant API svarade {response.status}: {body[:200]}")
        return json.loads(body)

    async def fetch_portfolio(self) -> dict | None:
        """Hämtar den valda portföljen via tRPC-API:t."""
        listing = await self._post(
            PORTFOLIO_LIST_API,
            {
                "1": {
                    "page": 0,
                    "limit": 100,
                    "sorting": [{"id": "name", "desc": False}],
                    "filters": [],
                    "tabIndex": "1",
                    "pagePrefix": "portfolios",
                    "useAdjustedWeight": True,
                }
            },
        )

        portfolios = listing[0]["result"]["data"]
        portfolio = select_portfolio(portfolios, TARGET_PORTFOLIO)
        if not portfolio:
            raise RuntimeError(f"Hittade inte portföljen '{TARGET_PORTFOLIO}'")

        watchlist_filter = {
            "id": portfolio["id"],
            "value": portfolio,
            "label": portfolio["title"],
            "tooltip": portfolio.get("descriptionSE", ""),
            "updatedAt": portfolio.get("updatedAt", ""),
            "group": portfolio.get("tag", ""),
        }

        payload = {
            "0": {
                "page": 0,
                "limit": 100,
                "sorting": [{"id": "name", "desc": False}],
                "filters": [],
                "externalFilters": {
                    "portfolioWatchlist": watchlist_filter,
                    "portfolioValue": 1000000,
                    "cashPercent": 0,
                },
                "tabIndex": "1",
                "pagePrefix": "portfolios",
                "useAdjustedWeight": True,
            }
        }

        data = await self._post(PORTFOLIO_DATA_API, payload)
        items = data[0]["result"]["data"]["items"]

        print(
            f"Successfully fetched portfolio data for '{TARGET_PORTFOLIO}' "
            f"({len(items)} positions)"
        )

        return {
            "date": portfolio_date(portfolio),
            "data": build_table_rows(items),
            "timestamp": datetime.now().isoformat(),
        }


async def fetch_portfolio() -> dict | None:
    async with NeuroQuantScraper() as scraper:
        if await scraper.login():
            return await scraper.fetch_portfolio()
        return None


if __name__ == "__main__":
    result = asyncio.run(fetch_portfolio())
    print(json.dumps(result, indent=2, ensure_ascii=False))
