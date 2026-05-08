from __future__ import annotations

from playwright.async_api import BrowserContext, Error as PlaywrightError

from auditor.config import Settings


class AuthError(RuntimeError):
    """Raised when login fails."""


async def login(context: BrowserContext, settings: Settings) -> BrowserContext:
    selectors = settings.selectors()
    page = await context.new_page()
    try:
        await page.goto(str(settings.app_login_url), wait_until="networkidle")
        await page.fill(selectors.username, settings.app_username)
        await page.fill(selectors.password, settings.app_password)
        await page.click(selectors.submit)
        await page.wait_for_load_state("networkidle")

        current = page.url
        if current.startswith(str(settings.app_login_url)):
            raise AuthError("Login appears to have failed; still on login page")

        await context.storage_state(path=str(settings.storage_state))
        return context
    except PlaywrightError as exc:
        raise AuthError(f"Playwright auth flow failed: {exc}") from exc
    finally:
        await page.close()


async def ensure_authenticated(context: BrowserContext, settings: Settings, target_url: str) -> None:
    page = await context.new_page()
    try:
        await page.goto(target_url, wait_until="networkidle")
        if page.url.startswith(str(settings.app_login_url)):
            await page.close()
            await login(context, settings)
    finally:
        if not page.is_closed():
            await page.close()
