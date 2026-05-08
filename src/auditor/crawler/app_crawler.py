from __future__ import annotations

import asyncio
import re
from collections import deque
from datetime import UTC, datetime
from urllib.parse import urljoin, urlparse

from playwright.async_api import BrowserContext

from auditor.auth import ensure_authenticated, login
from auditor.config import Settings
from auditor.extractors.styles import STYLE_KEYS, aggregate_styles
from auditor.models import PageRecord

_DYNAMIC_SEGMENT = re.compile(
    r"/(?:(?:[0-9]+)|(?:[0-9a-fA-F]{8}-[0-9a-fA-F-]{27,}))(?=/|$)"
)


async def crawl_app(context: BrowserContext, settings: Settings) -> list[PageRecord]:
    if not settings.storage_state.exists():
        await login(context, settings)

    seeds = [str(settings.app_base_url)] + _seed_routes(settings)
    queue: deque[str] = deque(seeds)
    visited_templates: set[str] = set()
    records: list[PageRecord] = []
    style_maps: list[dict[str, dict[str, str]]] = []

    while queue and len(records) < settings.max_pages_app:
        url = queue.popleft()
        await ensure_authenticated(context, settings, url)
        page = await context.new_page()
        try:
            await page.goto(url, wait_until="networkidle")
            await asyncio.sleep(settings.app_spa_hydration_delay)
            final_url = page.url
            template = normalize_route(final_url)
            if template in visited_templates:
                continue
            visited_templates.add(template)

            title = await page.title()
            screenshot = settings.artifacts_path / f"app-{len(records)+1}.png"
            await page.screenshot(path=str(screenshot), full_page=True)

            ui_labels = await page.eval_on_selector_all(
                "button, a, label, [aria-label], [role='tab'], [role='menuitem']",
                "els => [...new Set(els.map(e => e.getAttribute('aria-label') || e.textContent || '').map(t => t.trim()).filter(Boolean))]",
            )

            style_map = await _capture_styles(page)
            style_maps.append(style_map)

            records.append(
                PageRecord(
                    url=final_url,
                    site="app",
                    title=title,
                    visible_text=await page.inner_text("body"),
                    ui_labels=sorted(ui_labels),
                    computed_styles=aggregate_styles([style_map]),
                    screenshot_path=str(screenshot),
                    fetched_at=datetime.now(UTC),
                )
            )

            hrefs = await page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
            base_host = urlparse(str(settings.app_base_url)).netloc
            for href in hrefs:
                parsed = urlparse(href)
                if parsed.scheme in {"http", "https"} and parsed.netloc == base_host:
                    queue.append(urljoin(final_url, href))

        finally:
            await page.close()

    consolidated = aggregate_styles(style_maps)
    for record in records:
        record.computed_styles = consolidated

    return records


async def _capture_styles(page) -> dict[str, dict[str, str]]:
    selectors = [
        "body",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "p",
        "a",
        "button",
        "input",
        ".card",
    ]
    style_map: dict[str, dict[str, str]] = {}
    for selector in selectors:
        handle = await page.query_selector(selector)
        if not handle:
            continue
        result = await handle.evaluate(
            """
            (el, styleKeys) => {
              const computed = getComputedStyle(el);
              const out = {};
              for (const key of styleKeys) out[key] = computed.getPropertyValue(key);
              return out;
            }
            """,
            STYLE_KEYS,
        )
        style_map[selector] = result
    return style_map


def normalize_route(url: str) -> str:
    parsed = urlparse(url)
    normalized_path = _DYNAMIC_SEGMENT.sub("/{id}", parsed.path)
    return f"{parsed.scheme}://{parsed.netloc}{normalized_path}"


def _seed_routes(settings: Settings) -> list[str]:
    path = settings.seed_routes_file
    try:
        with open(path, encoding="utf-8") as file:
            return [line.strip() for line in file if line.strip() and not line.startswith("#")]
    except FileNotFoundError:
        return []
