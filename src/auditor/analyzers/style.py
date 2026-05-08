from __future__ import annotations

import re

from auditor.extractors.terminology import capitalization_variants, terminology_frequency
from auditor.models import PageRecord, StyleFinding


def analyse_style(docs_pages: list[PageRecord], app_pages: list[PageRecord]) -> list[StyleFinding]:
    findings: list[StyleFinding] = []
    findings.extend(_compare_typography(docs_pages, app_pages))
    findings.extend(_compare_colors(docs_pages, app_pages))
    findings.extend(_compare_spacing(docs_pages, app_pages))
    findings.extend(_compare_terminology(docs_pages, app_pages))
    findings.extend(_compare_capitalisation(docs_pages, app_pages))
    findings.extend(_compare_tone(docs_pages, app_pages))
    return findings


def _compare_typography(docs_pages: list[PageRecord], app_pages: list[PageRecord]) -> list[StyleFinding]:
    docs_fonts = _collect_fonts(docs_pages)
    app_fonts = _collect_fonts(app_pages)
    if docs_fonts == app_fonts:
        return []
    return [
        StyleFinding(
            category="typography",
            description="Font family inventory differs between docs and app.",
            docs_example=", ".join(sorted(docs_fonts)) or "none",
            app_example=", ".join(sorted(app_fonts)) or "none",
            severity="medium",
        )
    ]


def _compare_colors(docs_pages: list[PageRecord], app_pages: list[PageRecord]) -> list[StyleFinding]:
    docs_colors = _collect_colors(docs_pages)
    app_colors = _collect_colors(app_pages)
    unique_docs = sorted(docs_colors - app_colors)
    unique_app = sorted(app_colors - docs_colors)
    if not unique_docs and not unique_app:
        return []
    return [
        StyleFinding(
            category="color",
            description="Top color palettes are inconsistent.",
            docs_example=", ".join(unique_docs[:5]) or "none",
            app_example=", ".join(unique_app[:5]) or "none",
            severity="medium",
        )
    ]


def _compare_spacing(docs_pages: list[PageRecord], app_pages: list[PageRecord]) -> list[StyleFinding]:
    docs_spacing = _collect_spacing(docs_pages)
    app_spacing = _collect_spacing(app_pages)
    if docs_spacing == app_spacing:
        return []
    return [
        StyleFinding(
            category="spacing",
            description="Common spacing rhythm differs.",
            docs_example=", ".join(sorted(docs_spacing)) or "none",
            app_example=", ".join(sorted(app_spacing)) or "none",
            severity="low",
        )
    ]


def _compare_terminology(docs_pages: list[PageRecord], app_pages: list[PageRecord]) -> list[StyleFinding]:
    docs_terms = terminology_frequency([p.visible_text for p in docs_pages])
    app_terms = terminology_frequency([p.visible_text for p in app_pages])
    docs_only = [term for term in docs_terms if term not in app_terms][:5]
    app_only = [term for term in app_terms if term not in docs_terms][:5]
    if not docs_only and not app_only:
        return []
    return [
        StyleFinding(
            category="terminology",
            description="Frequent terms differ between docs and app.",
            docs_example=", ".join(docs_only) or "none",
            app_example=", ".join(app_only) or "none",
            severity="medium",
        )
    ]


def _compare_capitalisation(docs_pages: list[PageRecord], app_pages: list[PageRecord]) -> list[StyleFinding]:
    docs_variants = capitalization_variants([p.visible_text for p in docs_pages])
    app_variants = capitalization_variants([p.visible_text for p in app_pages])
    shared = sorted(set(docs_variants) & set(app_variants))
    if not shared:
        return []
    key = shared[0]
    return [
        StyleFinding(
            category="capitalisation",
            description="Capitalisation variants detected across both sites.",
            docs_example=str(docs_variants[key]),
            app_example=str(app_variants[key]),
            severity="low",
        )
    ]


def _compare_tone(docs_pages: list[PageRecord], app_pages: list[PageRecord]) -> list[StyleFinding]:
    docs_text = " ".join(p.visible_text for p in docs_pages)
    app_text = " ".join(p.visible_text for p in app_pages)
    docs_text_lower = docs_text.lower()
    app_text_lower = app_text.lower()
    docs_second_person = len(re.findall(r"\b(?:you|your)\b", docs_text_lower))
    app_first_person = len(re.findall(r"\b(?:i|my)\b", app_text_lower))
    if docs_second_person == 0 and app_first_person == 0:
        return []
    return [
        StyleFinding(
            category="tone",
            description="Pronoun usage suggests different voice between docs and app.",
            docs_example=f"Second-person references: {docs_second_person}",
            app_example=f"First-person references: {app_first_person}",
            severity="low",
        )
    ]


def _collect_fonts(pages: list[PageRecord]) -> set[str]:
    fonts: set[str] = set()
    for page in pages:
        fonts.update(page.computed_styles.font_families)
    return fonts


def _collect_colors(pages: list[PageRecord]) -> set[str]:
    colors: set[str] = set()
    for page in pages:
        colors.update(page.computed_styles.top_colors)
    return colors


def _collect_spacing(pages: list[PageRecord]) -> set[str]:
    spacing: set[str] = set()
    for page in pages:
        spacing.update(page.computed_styles.spacing_values)
    return spacing
