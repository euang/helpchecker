from __future__ import annotations

from pathlib import Path

from auditor.models import AuditReport


def write_markdown(report: AuditReport, output_path: Path) -> None:
    lines: list[str] = []
    lines.append("# 1. Documentation Shortfalls")
    lines.append("")
    if not report.coverage_findings:
        lines.append("No coverage findings.")
    else:
        for finding in report.coverage_findings:
            lines.append(f"- **{finding.severity.upper()}** `{finding.feature}`")
            lines.append(f"  - Confidence: {finding.confidence}")
            if finding.nearest_doc_match:
                lines.append(f"  - Nearest doc match: {finding.nearest_doc_match}")
            lines.append(f"  - Suggestion: {finding.suggestion}")
            if finding.app_locations:
                lines.append(f"  - App locations: {', '.join(finding.app_locations)}")

    lines.append("")
    lines.append("# 2. Style Inconsistencies")
    lines.append("")
    if not report.style_findings:
        lines.append("No style findings.")
    else:
        for finding in report.style_findings:
            lines.append(
                f"- **{finding.category}** ({finding.severity}) {finding.description}"
            )
            lines.append(f"  - Docs: {finding.docs_example}")
            lines.append(f"  - App: {finding.app_example}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
