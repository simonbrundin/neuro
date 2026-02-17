import asyncio
import json
from datetime import datetime
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from config import config, STATE_FILE

BASE_DIR = Path(__file__).parent

TARGET_PORTFOLIO = "NQ Värde & Momentum"


class NeuroQuantScraper:
    def __init__(self):
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None

    async def __aenter__(self):
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
        )
        self.page = await self.context.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.browser:
            await self.browser.close()

    async def _save_cookies(self):
        if self.context:
            cookies = await self._get_cookies()
            if cookies:
                with open(BASE_DIR / "cookies.json", "w") as f:
                    json.dump(cookies, f)

    async def _get_cookies(self):
        if self.context:
            return await self.context.cookies()
        return []

    def _load_cookies(self):
        cookie_file = BASE_DIR / "cookies.json"
        if cookie_file.exists():
            with open(cookie_file) as f:
                return json.load(f)
        return []

    async def login(self) -> bool:
        assert self.context is not None
        assert self.page is not None

        cookies = self._load_cookies()
        if cookies:
            await self.context.add_cookies(cookies)

        await self.page.goto("https://app.neuroquant.ai/login")
        await self.page.wait_for_load_state("domcontentloaded")

        if await self._is_logged_in():
            print("Already logged in via cookies")
            return True

        print("Logging in...")
        email_selectors = [
            'input[type="email"]',
            'input[name="email"]',
            'input[id="email"]',
            'input[placeholder*="email"]',
            'input[placeholder*="E-post"]',
            "input",
        ]
        password_selectors = [
            'input[type="password"]',
            'input[name="password"]',
            'input[id="password"]',
            'input[placeholder*="password"]',
            'input[placeholder*="lösenord"]',
        ]

        email_filled = False
        password_filled = False

        for selector in email_selectors:
            try:
                await self.page.fill(selector, config.neuro_email, timeout=1000)
                email_filled = True
                break
            except Exception:
                continue

        for selector in password_selectors:
            try:
                await self.page.fill(selector, config.neuro_password, timeout=1000)
                password_filled = True
                break
            except Exception:
                continue

        if not email_filled or not password_filled:
            return False

        submit_selectors = [
            'button[type="submit"]',
            'button:has-text("Logga in")',
            'button:has-text("Login")',
            'button:has-text("Sign in")',
        ]

        for selector in submit_selectors:
            try:
                await self.page.click(selector, timeout=2000)
                break
            except Exception:
                continue

        await self.page.wait_for_load_state("domcontentloaded")
        await asyncio.sleep(4)

        if (
            await self._is_logged_in()
            or "/dashboard" in self.page.url
            or "/portfolios" in self.page.url
        ):
            print(f"Already logged in, URL: {self.page.url}")
            await self._save_cookies()
            return True

        return False

    async def _is_logged_in(self) -> bool:
        assert self.page is not None
        try:
            await self.page.wait_for_selector(
                'text="Modellportföljer", a:has-text("Modellportföljer"), text="Dashboard", a:has-text("Dashboard")',
                timeout=3000,
            )
            return True
        except Exception:
            return False

    async def _select_portfolio_with_retry(self, max_retries: int = 3) -> bool:
        """Select the correct portfolio with retry logic."""
        dropdown_selectors = [
            "div.css-1uccc91-singleValue",
            "[class*='singleValue']",
            "[class*='Value']",
            "[class*='dropdown']",
        ]

        for attempt in range(max_retries):
            for selector in dropdown_selectors:
                try:
                    dropdown = await self.page.wait_for_selector(selector, timeout=5000)
                    if dropdown:
                        current_value = await dropdown.text_content()
                        print(f"Current portfolio: {current_value}")

                        if current_value and TARGET_PORTFOLIO in current_value:
                            print(
                                f"Correct portfolio '{TARGET_PORTFOLIO}' already selected"
                            )
                            return True

                        await self.page.click(selector)
                        await self.page.wait_for_selector(
                            "[class*='menu'], [class*='option'], ul[role='listbox']",
                            timeout=3000,
                        )
                        await self.page.keyboard.type(TARGET_PORTFOLIO)
                        await self.page.wait_for_selector(
                            "[class*='option'], [class*='menu-item']",
                            timeout=2000,
                        )
                        await self.page.keyboard.press("Enter")

                        verified = await self._verify_portfolio_selection()
                        if verified:
                            print(
                                f"Successfully selected portfolio '{TARGET_PORTFOLIO}'"
                            )
                            return True

                        break
                except Exception:
                    continue

        return False

    async def _verify_portfolio_selection(self) -> bool:
        """Verify that the correct portfolio is selected."""
        dropdown_selectors = [
            "div.css-1uccc91-singleValue",
            "[class*='singleValue']",
            "[class*='Value']",
        ]

        for selector in dropdown_selectors:
            try:
                dropdown = await self.page.wait_for_selector(selector, timeout=3000)
                if dropdown:
                    current_value = await dropdown.text_content()
                    if current_value and TARGET_PORTFOLIO in current_value:
                        return True
            except Exception:
                continue
        return False

    async def get_portfolio_data(self) -> dict | None:
        assert self.page is not None
        try:
            if "/dashboard" in self.page.url:
                await self.page.goto("https://app.neuroquant.ai/portfolios")
                await self.page.wait_for_load_state("domcontentloaded")

            await self.page.wait_for_selector(
                "div.css-1uccc91-singleValue, [class*='singleValue'], [class*='Value']",
                timeout=10000,
            )

            await self._select_portfolio_with_retry()

            date_selector = "text=/\\d{4}-\\d{2}-\\d{2}/"
            try:
                date_element = await self.page.wait_for_selector(
                    date_selector, timeout=5000
                )
                if date_element:
                    date_text = await date_element.text_content()
                else:
                    date_text = None
            except Exception:
                date_text = None

            table_data = await self._extract_table_data()

            print(f"Successfully fetched portfolio data for '{TARGET_PORTFOLIO}'")

            return {
                "date": date_text,
                "data": table_data,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            print(f"Error fetching portfolio data: {e}")
            return None

    async def _extract_table_data(self) -> list[dict]:
        assert self.page is not None
        rows = []

        try:
            table_rows = await self.page.query_selector_all("table tbody tr, table tr")

            for row in table_rows:
                cells = await row.query_selector_all("td, th")
                if len(cells) >= 2:
                    row_data = []
                    for cell in cells:
                        text = await cell.text_content()
                        if text:
                            row_data.append(text.strip())
                    if row_data:
                        rows.append(row_data)
        except Exception as e:
            print(f"Error extracting table: {e}")

        return rows


async def fetch_portfolio() -> dict | None:
    async with NeuroQuantScraper() as scraper:
        if await scraper.login():
            return await scraper.get_portfolio_data()
        return None


if __name__ == "__main__":
    result = asyncio.run(fetch_portfolio())
    print(json.dumps(result, indent=2))
