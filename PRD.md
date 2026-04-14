# LinkedIn Profile Scraper — PRD

## What it is
A stealth-browser LinkedIn profile scraper that ingests the user's live Firefox `li_at` session cookie and outputs any public LinkedIn profile page as a markdown document. Ships as a reusable engine with three delivery surfaces: FastAPI server, simple React/Vite frontend, and a standalone CLI script.

## Core objectives
- [ ] Extract `li_at` cookie from the user's active Firefox profile automatically
- [ ] Fall back to manual session file (JSON) if Firefox is unavailable or user prefers
- [ ] Scrape any public LinkedIn profile URL via stealth Firefox (camoufox)
- [ ] Output the full page as clean markdown — no schema, just the page rendered as-is
- [ ] Parallel batch mode — multiple URLs concurrently with configurable concurrency
- [ ] Retry with Tenacity on transient failures (rate-limit, timeout, challenge page)
- [ ] Session expiry detection → clear error + login prompt
- [ ] Multiple input modes: single URL arg, file of URLs (one per line), interactive prompt

## Input modes
1. **Single URL** — `linkedin-scrape "https://www.linkedin.com/in/john-doe"`
2. **Batch file** — `linkedin-scrape --input urls.txt`
3. **Interactive** — `linkedin-scrape` (no args) prompts for URL(s)
4. **JSON session file** — `linkedin-scrape --session session.json`
5. **API mode** — POST to FastAPI endpoint with URL(s), receive markdown

## Output
- CLI: writes `.md` files to `--output-dir` (default: `./output`) or stdout
- API: JSON `{"url": "...", "markdown": "...", "status": "ok"|"error", "error": "..."}`

## Parallelism
- Default concurrency: 3
- Configurable via `--parallel N`
- Uses asyncio + camoufox tab pool pattern (bounded)
- Rate-limit handling: exponential backoff via Tenacity

## Verbosity
- `-v` / `--verbose`: print each URL as it's processed with status
- `-vv`: print full response HTML length, timing, cookie status
- `-q` / `--quiet`: only errors

## Session file format (JSON)
```json
{
  "li_at": "AQ...xxx",
  "JSESSIONID": "\"...",
  "li_theme": "light",
  "li_theme_set": "..."
}
```
All cookies from Firefox are exported, not just `li_at`.

## Tech stack
- **Runtime**: Python 3.9+, **uv** for package management
- **Browser**: camoufox (stealth Firefox automation)
- **HTTP retry**: Tenacity
- **API**: FastAPI + Uvicorn
- **Frontend**: Vite + vanilla JS (no framework), served by FastAPI static files
- **CLI**: Typer (or argparse if simpler)

## Project structure
```
linkedin-scraper/
├── engine/
│   ├── __init__.py
│   ├── session.py       # Firefox cookie extraction + JSON session file
│   ├── scraper.py       # camoufox browser engine + page→markdown
│   └── parallel.py      # asyncio pool runner
├── api/
│   ├── main.py          # FastAPI app
│   └── schemas.py        # Pydantic models
├── frontend/
│   ├── index.html
│   ├── main.js
│   └── style.css
├── cli.py               # Standalone CLI entry point
├── pyproject.toml
└── CLAUDE.md
```

## Constraints
- No external proxy services (direct from user's IP)
- No unofficial LinkedIn API calls (profile page scrape only)
- Session cookie never logged or transmitted beyond local execution
- Graceful degradation if Firefox profile is not found
