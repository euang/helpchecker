from __future__ import annotations

from collections import Counter

from auditor.models import StyleFingerprint

STYLE_KEYS = [
    "font-family",
    "font-size",
    "font-weight",
    "line-height",
    "color",
    "background-color",
    "border-radius",
    "padding",
    "margin",
]


def aggregate_styles(style_maps: list[dict[str, dict[str, str]]]) -> StyleFingerprint:
    color_counter: Counter[str] = Counter()
    font_counter: Counter[str] = Counter()
    spacing: Counter[str] = Counter()
    heading_scale: dict[str, str] = {}
    button_variants: set[str] = set()

    merged: dict[str, dict[str, str]] = {}
    for style_map in style_maps:
        for selector, properties in style_map.items():
            merged[selector] = properties
            color = properties.get("color")
            if color:
                color_counter[color] += 1
            bg = properties.get("background-color")
            if bg:
                color_counter[bg] += 1
            font = properties.get("font-family")
            if font:
                font_counter[font] += 1
            for key in ["padding", "margin"]:
                val = properties.get(key)
                if val:
                    spacing[val] += 1
            if selector in {"h1", "h2", "h3", "h4", "h5", "h6"} and properties.get("font-size"):
                heading_scale[selector] = properties["font-size"]
            if "button" in selector:
                button_variants.add(
                    f"{properties.get('border-radius', '')}|{properties.get('font-size', '')}|"
                    f"{properties.get('background-color', '')}"
                )

    return StyleFingerprint(
        by_selector=merged,
        top_colors=[color for color, _ in color_counter.most_common(10)],
        font_families=[font for font, _ in font_counter.most_common()],
        heading_scale=heading_scale,
        button_variants=sorted(button_variants),
        spacing_values=[value for value, _ in spacing.most_common(10)],
    )
