from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


class Heading(BaseModel):
    level: int
    text: str


class StyleFingerprint(BaseModel):
    by_selector: dict[str, dict[str, str]] = Field(default_factory=dict)
    top_colors: list[str] = Field(default_factory=list)
    font_families: list[str] = Field(default_factory=list)
    heading_scale: dict[str, str] = Field(default_factory=dict)
    button_variants: list[str] = Field(default_factory=list)
    spacing_values: list[str] = Field(default_factory=list)


class PageRecord(BaseModel):
    url: str
    site: Literal["docs", "app"]
    title: str = ""
    headings: list[Heading] = Field(default_factory=list)
    visible_text: str = ""
    ui_labels: list[str] = Field(default_factory=list)
    computed_styles: StyleFingerprint = Field(default_factory=StyleFingerprint)
    screenshot_path: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class CoverageFinding(BaseModel):
    feature: str
    severity: Literal["missing", "partial", "documented"]
    app_locations: list[str] = Field(default_factory=list)
    nearest_doc_match: str | None = None
    confidence: float = 0.0
    suggestion: str = ""


class StyleFinding(BaseModel):
    category: Literal["color", "typography", "spacing", "terminology", "capitalisation", "tone"]
    description: str
    docs_example: str
    app_example: str
    severity: Literal["low", "medium", "high"]


class AuditReport(BaseModel):
    coverage_findings: list[CoverageFinding] = Field(default_factory=list)
    style_findings: list[StyleFinding] = Field(default_factory=list)
