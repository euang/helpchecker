I'll write this as a markdown file you can drop into a repo as `PLAN.md` and hand to the coding agent.The file tool is erroring out, so here's the plan inline — copy this into a `PLAN.md` in your repo:

---

# Documentation Coverage & Style Consistency Auditor — Implementation Plan

## Goal

Build a Python CLI tool that audits a **documentation site** against a live **application site** (which requires login) and produces two separate reports:

1. **Documentation shortfalls** — features, UI elements, settings, or workflows that exist in the application but are missing, incomplete, or hard to find in the docs.
2. **Style inconsistencies** — visual style, typography, colour, terminology, capitalisation, and tone differences between the two sites.

The two analyses must run independently (`--only coverage` or `--only style`) as well as together.

---

## Configuration

All configuration via environment variables / `.env` (loaded with `python-dotenv`):

| Variable | Purpose |
|---|---|
| `DOCS_BASE_URL` | Root of the documentation site, `https://help.smartsurvey.co.uk` |
| `APP_BASE_URL` | Root of the application site, e.g. `https://app.smartsurvey.co.uk` |
| `APP_LOGIN_URL` | https://app.smartsurvey.co.uk |
| `APP_USERNAME` | euan_griffiths@btinternet.com |
| `APP_PASSWORD` | Login password |
| `APP_LOGIN_SELECTORS` | JSON of CSS selectors for username/password/submit fields, so the login flow is configurable not hardcoded |
| `MAX_PAGES_DOCS` | Crawl cap (default 500) |
| `MAX_PAGES_APP` | Crawl cap (default 200) |
| `ANTHROPIC_API_KEY` | Optional; enables semantic gap detection |

Secrets must never be committed. Provide a `.env.example` with placeholder values only.

---

## Tech Stack

- **Python 3.11+**
- **Playwright** — handles authenticated, JS-heavy app crawling and exposes computed styles
- **BeautifulSoup4 + lxml** — HTML parsing for the docs site
- **httpx** — plain HTTP for static docs pages
- **Pydantic v2** — data models (`PageRecord`, `Feature`, `StyleFingerprint`, `Finding`)
- **rapidfuzz** — fuzzy string matching for feature → doc topic resolution
- **tinycss2 / cssutils** — CSS parsing
- **rich** — CLI output and progress bars
- **typer** — CLI framework
- **pytest + pytest-playwright** — tests
- **anthropic** (optional) — semantic comparison via Claude API

---

## Repository Layout

```
docs-app-auditor/
├── pyproject.toml
├── .env.example
├── README.md
├── src/auditor/
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── auth.py
│   ├── crawler/
│   │   ├── docs_crawler.py
│   │   └── app_crawler.py
│   ├── extractors/
│   │   ├── content.py
│   │   ├── styles.py
│   │   └── terminology.py
│   ├── analyzers/
│   │   ├── coverage.py        # Step A
│   │   └── style.py           # Step B
│   ├── reporters/
│   │   ├── markdown.py
│   │   └── json_reporter.py
│   └── cli.py
└── tests/
```

---

## Phase 1 — Project setup
- [ ] Initialise `pyproject.toml` with dependencies above
- [ ] `playwright install chromium`
- [ ] Add `.env.example`, `.gitignore`, licence
- [ ] `pre-commit` config: `ruff`, `black`, `mypy`
- [ ] GitHub Actions workflow: `ruff` + `mypy` + `pytest` on PRs

## Phase 2 — Authentication
The application site requires login. Implement a robust auth helper.
- [ ] `auth.py` exposes `async def login(playwright_context) -> BrowserContext`
- [ ] Persist `storage_state.json` so subsequent runs reuse the session
- [ ] Detect failed login (still on login URL, error banner, redirect loop) → raise `AuthError`
- [ ] Detect expired session mid-crawl: if a request redirects to `APP_LOGIN_URL`, re-auth transparently and retry once
- [ ] Login selectors configurable via `APP_LOGIN_SELECTORS` so the tool isn't tied to one app's HTML
- [ ] **Out of scope but document**: SSO/OAuth/MFA. Provide a hook for manually-imported `storage_state.json`

**Acceptance:** `auditor login --check` confirms a session can be established and persisted.

## Phase 3 — Crawling
Both crawlers produce a normalised `PageRecord`:
```python
class PageRecord(BaseModel):
    url: str
    site: Literal["docs", "app"]
    title: str
    headings: list[Heading]              # level + text
    visible_text: str
    ui_labels: list[str]                 # buttons, links, form labels, menu items, tabs
    computed_styles: StyleFingerprint
    screenshot_path: str | None
    fetched_at: datetime
```

**3a. Docs crawler**
- [ ] Try `sitemap.xml` first; fall back to recursive same-origin link following
- [ ] Respect `robots.txt`
- [ ] Politeness: 1 req/sec default, configurable
- [ ] Skip non-HTML resources, anchor-only links, external domains

**3b. App crawler**
- [ ] Authenticated Playwright crawler using stored session
- [ ] Wait for `networkidle` plus a configurable extra delay for SPA hydration
- [ ] Normalise parameterised URLs (`/survey/123/edit` → `/survey/{id}/edit`) so we don't crawl thousands of duplicates — collapse numeric/UUID segments
- [ ] One screenshot per template route (used in the style report)
- [ ] Discover routes via rendered-DOM links and an optional `seed_routes.txt`

## Phase 4 — Extraction
For every `PageRecord` extract:

**Content**
- [ ] Cleaned visible text (strip nav/footer/repeated chrome via repetition detection across pages)
- [ ] Heading tree
- [ ] **UI label inventory** — buttons, `aria-label`s, link text, form labels, tab names, menu items, settings toggles. This is the primary "feature surface" for the app site

**Style fingerprint** (per page → aggregated per site)
- [ ] Run `getComputedStyle` via Playwright on a curated selector set: `body`, `h1-h6`, `p`, `a`, `button`, primary/secondary buttons, inputs, cards
- [ ] Extract: `font-family`, `font-size`, `font-weight`, `line-height`, `color`, `background-color`, `border-radius`, common `padding`/`margin` values
- [ ] Aggregate site-level: top 10 colours by frequency, font family inventory, heading size scale, button style variants

**Terminology**
- [ ] Tokenise visible text + UI labels
- [ ] Extract noun phrases (spaCy `en_core_web_sm`, or a regex-POS lightweight alternative)
- [ ] Per-site frequency map of capitalised product terms (likely entity names: "Survey", "Workspace", "Respondent")

## Phase 5 — STEP A: Documentation shortfall analysis
The "what's in the app but missing from the docs" report.
- [ ] Build a **feature index** from all app `PageRecord`s: every distinct UI label + every distinct route template. Deduplicate and group obvious variants
- [ ] Build a **topic index** from all docs `PageRecord`s: every heading, every page title, plus the first paragraph under each heading
- [ ] For each app feature, attempt to match against the topic index in order:
  1. Exact normalised match (lowercase, strip punctuation)
  2. Fuzzy match with `rapidfuzz.WRatio >= 85`
  3. (If `ANTHROPIC_API_KEY` set) semantic match — batch features and ask Claude to classify each as `DOCUMENTED` / `PARTIAL` / `MISSING` given the candidate doc topics
- [ ] Classify each feature:
  - **DOCUMENTED** — high-confidence match to a dedicated heading/page
  - **PARTIAL** — mentioned in body text but no dedicated section
  - **MISSING** — no match
- [ ] Emit findings sorted by severity with: feature name, app locations (URL + screenshot), nearest doc match if any, suggested doc location

```python
class CoverageFinding(BaseModel):
    feature: str
    severity: Literal["missing", "partial", "documented"]
    app_locations: list[str]
    nearest_doc_match: str | None
    confidence: float
    suggestion: str
```

## Phase 6 — STEP B: Style inconsistency analysis (separate, as requested)
Runs independently of Phase 5, produces its own report.

**Visual**
- Primary/secondary/accent colour deltas (flag if `ΔE > 5` in Lab colour space)
- Font-family mismatches (docs `Inter`, app `Helvetica Neue`)
- Heading scale mismatches (docs `h1` 32 px, app `h1` 28 px)
- Button shape/border-radius differences
- Spacing rhythm — compare common padding values

**Terminology**
- Same concept named differently across sites (fuzzy + optional semantic clustering): app "Project" vs docs "Survey"
- Capitalisation drift: "API key" vs "API Key" vs "api key" — report variants and counts
- Brand-name spelling variants

**Tone & voice**
- Person/voice detection: docs in 2nd-person imperative ("Click Save"), app microcopy in 1st person ("I agree") — flag
- Sentence length distribution per site as a rough readability signal

```python
class StyleFinding(BaseModel):
    category: Literal["color", "typography", "spacing", "terminology", "capitalisation", "tone"]
    description: str
    docs_example: str
    app_example: str
    severity: Literal["low", "medium", "high"]
```

## Phase 7 — Reporting
- [ ] **Markdown report** (`report.md`) with two independent top-level sections: `# 1. Documentation Shortfalls`, `# 2. Style Inconsistencies`
- [ ] **JSON report** (`report.json`) for CI / programmatic use
- [ ] Each finding links back to source URLs and embeds screenshots from `./artifacts/`

## Phase 8 — CLI (Typer)
```
auditor login --check
auditor crawl docs
auditor crawl app
auditor analyse coverage      # Step A only
auditor analyse style         # Step B only
auditor run                   # full pipeline
auditor run --only coverage
auditor run --only style
```
- [ ] Non-zero exit code with `--fail-on missing` if any `MISSING` coverage findings exist (CI gating)

## Phase 9 — Tests
- [ ] Unit tests for analyzers using fixture HTML in `tests/fixtures/`
- [ ] Mock the Playwright auth flow with a local test server in `conftest.py`
- [ ] Snapshot tests for the markdown reporter
- [ ] ≥ 80% coverage on `analyzers/` and `extractors/`

---

## Acceptance Criteria
- [ ] Authenticates against the app site and persists the session
- [ ] Crawls both sites within configurable limits
- [ ] `auditor run --only coverage` produces a documentation shortfall report listing every app feature and its documentation status
- [ ] `auditor run --only style` produces a separate style inconsistency report covering colour, typography, spacing, terminology, capitalisation, tone
- [ ] All secrets via env vars; nothing sensitive committed
- [ ] README covers setup, configuration, running, interpreting each report section
- [ ] CI runs lint + tests on PRs

## Notes for the Agent
- Phase 5 (Step A) and Phase 6 (Step B) share crawl/extraction output but must run independently — don't couple them.
- Prefer correctness over crawl speed. A 20-minute run with a clean report is fine.
- Parameterised routes: crawl one representative per template, not every record.
- If login uses SSO/OAuth/MFA: stop, document the limitation, and provide a manual `storage_state.json` import path.
- Treat the Anthropic-API semantic step as required.
