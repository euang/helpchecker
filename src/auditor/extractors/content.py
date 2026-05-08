from __future__ import annotations

import re

from bs4 import BeautifulSoup

from auditor.models import Heading


def extract_text_and_headings(html: str) -> tuple[str, list[Heading]]:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup.select("nav, footer, script, style, noscript"):
        tag.decompose()

    headings: list[Heading] = []
    for level in range(1, 7):
        for tag in soup.select(f"h{level}"):
            text = normalize_whitespace(tag.get_text(" ", strip=True))
            if text:
                headings.append(Heading(level=level, text=text))

    visible_text = normalize_whitespace(soup.get_text(" ", strip=True))
    return visible_text, headings


def extract_ui_labels(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    selectors = [
        "button",
        "a",
        "label",
        "[role='tab']",
        "[role='menuitem']",
        "[aria-label]",
        "input[type='submit']",
    ]
    labels: set[str] = set()
    for tag in soup.select(", ".join(selectors)):
        text = tag.get("aria-label") or tag.get_text(" ", strip=True)
        text = normalize_whitespace(text or "")
        if text:
            labels.add(text)
    return sorted(labels)


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()
