from auditor.analyzers.style import analyse_style
from auditor.models import PageRecord, StyleFingerprint


def test_analyse_style_detects_font_mismatch() -> None:
    docs = [
        PageRecord(
            url="https://docs",
            site="docs",
            computed_styles=StyleFingerprint(font_families=["Inter"], top_colors=["rgb(0,0,0)"]),
        )
    ]
    app = [
        PageRecord(
            url="https://app",
            site="app",
            computed_styles=StyleFingerprint(font_families=["Helvetica Neue"], top_colors=["rgb(1,1,1)"]),
        )
    ]

    findings = analyse_style(docs, app)
    assert any(f.category == "typography" for f in findings)
