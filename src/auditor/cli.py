from __future__ import annotations

import asyncio
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

_STATE: dict[str, list[PageRecord]] = {"docs": [], "app": []}


@app.command()
def login_check(check: bool = typer.Option(True, "--check", help="Run login check")) -> None:
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

    if check:
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
    _STATE[target] = pages
    console.print(f"[green]Crawled {len(pages)} {target} pages.[/green]")


@analyse_app.command("coverage")
def analyse_coverage_cmd() -> None:
    findings = analyse_coverage(_STATE["app"], _STATE["docs"])
    table = Table(title="Coverage Findings")
    table.add_column("Severity")
    table.add_column("Feature")
    table.add_column("Confidence")
    for finding in findings:
        table.add_row(finding.severity, finding.feature, str(finding.confidence))
    console.print(table)


@analyse_app.command("style")
def analyse_style_cmd() -> None:
    findings = analyse_style(_STATE["docs"], _STATE["app"])
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
    _STATE["docs"], _STATE["app"] = docs_pages, app_pages

    report = AuditReport()
    if only in {"coverage", "all"}:
        report.coverage_findings = analyse_coverage(app_pages, docs_pages)
    if only in {"style", "all"}:
        report.style_findings = analyse_style(docs_pages, app_pages)

    write_markdown(report, Path("report.md"))
    write_json(report, Path("report.json"))

    if fail_on == "missing" and any(f.severity == "missing" for f in report.coverage_findings):
        raise typer.Exit(code=2)


if __name__ == "__main__":
    app()
