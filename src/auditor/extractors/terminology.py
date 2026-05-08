from __future__ import annotations

import re
from collections import Counter

TERMINOLOGY_TOKEN_PATTERN = re.compile(r"[A-Za-z][A-Za-z0-9\-']+")


def terminology_frequency(texts: list[str]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for text in texts:
        for token in TERMINOLOGY_TOKEN_PATTERN.findall(text):
            if token[0].isupper():
                counter[token] += 1
    return dict(counter.most_common())


def capitalization_variants(texts: list[str]) -> dict[str, dict[str, int]]:
    grouped: dict[str, Counter[str]] = {}
    for text in texts:
        for token in TERMINOLOGY_TOKEN_PATTERN.findall(text):
            key = token.lower()
            grouped.setdefault(key, Counter())
            grouped[key][token] += 1
    return {k: dict(v) for k, v in grouped.items() if len(v) > 1}
