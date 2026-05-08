from __future__ import annotations

import json
from pathlib import Path

from auditor.models import AuditReport


def write_json(report: AuditReport, output_path: Path) -> None:
    output_path.write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
