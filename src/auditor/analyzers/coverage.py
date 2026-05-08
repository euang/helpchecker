from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass

from rapidfuzz import fuzz

from auditor.models import CoverageFinding, PageRecord


@dataclass
class Topic:
    name: str
    location: str


def analyse_coverage(app_pages: list[PageRecord], docs_pages: list[PageRecord]) -> list[CoverageFinding]:
    features = _feature_index(app_pages)
    topics = _topic_index(docs_pages)
    findings: list[CoverageFinding] = []

    for feature, locations in sorted(features.items()):
        nearest = _best_topic_match(feature, topics)
        if not nearest:
            findings.append(
                CoverageFinding(
                    feature=feature,
                    severity="missing",
                    app_locations=sorted(locations),
                    nearest_doc_match=None,
                    confidence=0.0,
                    suggestion="Add a dedicated documentation section for this feature.",
                )
            )
            continue

        score, topic = nearest
        if score >= 95:
            severity = "documented"
            suggestion = "No action required."
        elif score >= 75:
            severity = "partial"
            suggestion = "Expand docs with dedicated heading and workflow details."
        else:
            severity = "missing"
            suggestion = "Create new docs topic aligned to this app feature."

        findings.append(
            CoverageFinding(
                feature=feature,
                severity=severity,
                app_locations=sorted(locations),
                nearest_doc_match=topic.name,
                confidence=round(score / 100.0, 2),
                suggestion=suggestion,
            )
        )

    severity_rank = {"missing": 0, "partial": 1, "documented": 2}
    return sorted(findings, key=lambda f: (severity_rank[f.severity], f.feature.lower()))


def _feature_index(app_pages: list[PageRecord]) -> dict[str, set[str]]:
    features: dict[str, set[str]] = defaultdict(set)
    for page in app_pages:
        route_feature = _normalize_text(page.url)
        features[route_feature].add(page.url)
        for label in page.ui_labels:
            norm = _normalize_text(label)
            if norm:
                features[norm].add(page.url)
    return features


def _topic_index(docs_pages: list[PageRecord]) -> list[Topic]:
    topics: list[Topic] = []
    for page in docs_pages:
        if page.title:
            topics.append(Topic(name=_normalize_text(page.title), location=page.url))
        for heading in page.headings:
            topics.append(Topic(name=_normalize_text(heading.text), location=page.url))
    return topics


def _best_topic_match(feature: str, topics: list[Topic]) -> tuple[float, Topic] | None:
    exact = next((topic for topic in topics if topic.name == feature), None)
    if exact:
        return 100.0, exact

    best_score = -1.0
    best_topic: Topic | None = None
    for topic in topics:
        score = float(fuzz.WRatio(feature, topic.name))
        if score > best_score:
            best_score = score
            best_topic = topic

    if best_topic is None:
        return None
    return best_score, best_topic


def _normalize_text(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9\s/-]", "", value)
    return re.sub(r"\s+", " ", value)
