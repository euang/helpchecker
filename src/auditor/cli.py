from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Literal

import typer
from rich.console import Console
from rich.table import Table
from playwright.async_api import async_playwright

from auditor.analyzers.coverage import analyse_coverage
from auditor.analyzers.style import analyse_style
from auditor.auth import AuthError, login
from auditor.config import get_settings
from auditor.crawler.app_crawler import crawl_app
from auditor.crawler.docs_crawler import crawl_docs
from auditor.models import AuditReport, PageRecord
from auditor.reporters.json_reporter import write_json
from auditor.reporters.markdown import write_markdown

app = typer.Typer(help="Documentation coverage and style consistency auditor")
analyse_app = typer.Typer(help="Run analyzers")
app.add_typer(analyse_app, name="analyse")
console = Console()


@app.command()
def login_check(perform_check: bool = typer.Option(True, "--check", help="Run login check")) -> None:
    settings = get_settings()

    async def _run() -> None:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            context = await browser.new_context(storage_state=str(settings.storage_state) if settings.storage_state.exists() else None)
            try:
                await login(context, settings)
                console.print("[green]Login success; storage state persisted.[/green]")
            finally:
                await context.close()
                await browser.close()

    if perform_check:
        try:
            asyncio.run(_run())
        except AuthError as exc:
            raise typer.Exit(code=1) from exc


@app.command("crawl")
def crawl(target: Literal["docs", "app"]) -> None:
    settings = get_settings()

    async def _run() -> list[PageRecord]:
        if target == "docs":
            return await crawl_docs(settings)

        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            context = await browser.new_context(
                storage_state=str(settings.storage_state) if settings.storage_state.exists() else None
            )
            try:
                return await crawl_app(context, settings)
            finally:
                await context.close()
                await browser.close()

    pages = asyncio.run(_run())
    _save_pages(target, pages)
    console.print(f"[green]Crawled {len(pages)} {target} pages.[/green]")


@analyse_app.command("coverage")
def analyse_coverage_cmd() -> None:
    findings = analyse_coverage(_load_pages("app"), _load_pages("docs"))
    table = Table(title="Coverage Findings")
    table.add_column("Severity")
    table.add_column("Feature")
    table.add_column("Confidence")
    for finding in findings:
        table.add_row(finding.severity, finding.feature, str(finding.confidence))
    console.print(table)


@analyse_app.command("style")
def analyse_style_cmd() -> None:
    findings = analyse_style(_load_pages("docs"), _load_pages("app"))
    table = Table(title="Style Findings")
    table.add_column("Category")
    table.add_column("Severity")
    table.add_column("Description")
    for finding in findings:
        table.add_row(finding.category, finding.severity, finding.description)
    console.print(table)


@app.command()
def run(
    only: Literal["coverage", "style", "all"] = typer.Option("all", "--only"),
    fail_on: Literal["missing", "none"] = typer.Option("none", "--fail-on"),
) -> None:
    settings = get_settings()

    async def _crawl_all() -> tuple[list[PageRecord], list[PageRecord]]:
        docs_pages = await crawl_docs(settings)
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            context = await browser.new_context(
                storage_state=str(settings.storage_state) if settings.storage_state.exists() else None
            )
            try:
                app_pages = await crawl_app(context, settings)
            finally:
                await context.close()
                await browser.close()
        return docs_pages, app_pages

    docs_pages, app_pages = asyncio.run(_crawl_all())
    _save_pages("docs", docs_pages)
    _save_pages("app", app_pages)

    report = AuditReport()
    if only in {"coverage", "all"}:
        report.coverage_findings = analyse_coverage(app_pages, docs_pages)
    if only in {"style", "all"}:
        report.style_findings = analyse_style(docs_pages, app_pages)

    write_markdown(report, Path("report.md"))
    write_json(report, Path("report.json"))

    if fail_on == "missing" and any(f.severity == "missing" for f in report.coverage_findings):
        raise typer.Exit(code=2)


def _state_file(target: Literal["docs", "app"]) -> Path:
    settings = get_settings()
    return settings.artifacts_path / f"{target}_pages.json"


def _save_pages(target: Literal["docs", "app"], pages: list[PageRecord]) -> None:
    payload = [page.model_dump(mode="json") for page in pages]
    _state_file(target).write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _load_pages(target: Literal["docs", "app"]) -> list[PageRecord]:
    path = _state_file(target)
    if not path.exists():
        raise typer.BadParameter(
            f"No cached {target} crawl found. Run `auditor crawl {target}` or `auditor run` first."
        )
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [PageRecord.model_validate(item) for item in payload]


if __name__ == "__main__":
    app()
