from auditor.analyzers.coverage import analyse_coverage
from auditor.models import Heading, PageRecord


def test_analyse_coverage_flags_missing_and_documented() -> None:
    app_pages = [
        PageRecord(url="https://app/surveys", site="app", ui_labels=["Create Survey", "Delete Survey"])
    ]
    docs_pages = [
        PageRecord(
            url="https://docs/surveys",
            site="docs",
            title="Create Survey",
            headings=[Heading(level=2, text="Create Survey")],
        )
    ]

    findings = analyse_coverage(app_pages, docs_pages)
    severities = {f.feature: f.severity for f in findings}
    assert severities.get("create survey") == "documented"
    assert severities.get("delete survey") in {"missing", "partial"}
