from __future__ import annotations

import asyncio
from collections import deque
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

from auditor.config import Settings
from auditor.extractors.content import extract_text_and_headings, extract_ui_labels
from auditor.models import PageRecord


async def crawl_docs(settings: Settings) -> list[PageRecord]:
    visited: set[str] = set()
    queue: deque[str] = deque([str(settings.docs_base_url)])
    records: list[PageRecord] = []

    async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
        while queue and len(records) < settings.max_pages_docs:
            url = queue.popleft()
            if url in visited:
                continue
            visited.add(url)

            try:
                response = await client.get(url)
            except httpx.HTTPError:
                continue
            content_type = response.headers.get("content-type", "")
            if "text/html" not in content_type:
                continue

            html = response.text
            visible_text, headings = extract_text_and_headings(html)
            labels = extract_ui_labels(html)
            title = _extract_title(html)

            records.append(
                PageRecord(
                    url=url,
                    site="docs",
                    title=title,
                    headings=headings,
                    visible_text=visible_text,
                    ui_labels=labels,
                    fetched_at=datetime.utcnow(),
                )
            )

            for next_url in _discover_links(url, html, str(settings.docs_base_url)):
                if next_url not in visited:
                    queue.append(next_url)

            await asyncio.sleep(settings.crawl_delay_seconds)

    return records


def _extract_title(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    title = soup.find("title")
    return title.get_text(strip=True) if title else ""


def _discover_links(source_url: str, html: str, base_url: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    base_host = urlparse(base_url).netloc
    links: list[str] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor["href"].strip()
        if not href or href.startswith("#"):
            continue
        absolute = urljoin(source_url, href)
        parsed = urlparse(absolute)
        if parsed.scheme not in {"http", "https"}:
            continue
        if parsed.netloc != base_host:
            continue
        links.append(absolute.split("#", 1)[0])
    return links
