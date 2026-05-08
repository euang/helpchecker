# helpchecker

`helpchecker` audits a documentation site against an authenticated application site.

## Features

- Coverage analysis: detect app features missing from docs.
- Style analysis: detect design and language inconsistencies between docs and app.
- Independent execution: run `coverage`, `style`, or both.

## Setup

1. Create a virtualenv and install dependencies:
   - `pip install -e .[dev]`
2. Install Playwright browser:
   - `playwright install chromium`
3. Copy `.env.example` to `.env` and fill values.

## CLI

- `auditor login --check`
- `auditor crawl docs`
- `auditor crawl app`
- `auditor analyse coverage`
- `auditor analyse style`
- `auditor run`
- `auditor run --only coverage`
- `auditor run --only style`

## Output

- `report.md` for human-readable findings.
- `report.json` for automation.
- `artifacts/` for crawl snapshots/screenshots.

## Notes

- If SSO/OAuth/MFA prevents scripted login, provide a manual `storage_state.json` via `STORAGE_STATE_PATH`.
- No secrets are committed; use `.env` only.
