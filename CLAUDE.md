# LinkedIn Scraper — Project Conventions

## Model Routing
| Task type | Model | Agent |
|-----------|-------|-------|
| Engine internals (browser, session, async) | `zai-coding-plan/glm-5-turbo` | opencode |
| Parallel runner, Tenacity integration | `zai-coding-plan/glm-5-turbo` | opencode |
| API scaffolding (FastAPI, Pydantic) | `sonnet` | opencode |
| Frontend (HTML/JS/CSS) | `sonnet` | opencode |
| CLI arg parsing, file I/O | `sonnet` | opencode |
| Smoke tests, edge cases | `sonnet` | opencode |

Rule: default to `sonnet` unless the task involves complex async, browser automation internals, or retry logic — then use `zai-coding-plan/glm-5-turbo`.

## Project Structure
```
linkedin-scraper/
├── engine/          # Core scraping engine (no external deps beyond browser/tenacity)
│   ├── __init__.py
│   ├── session.py    # Firefox cookie extraction, JSON session read/write
│   ├── scraper.py   # camoufox engine, page→markdown
│   └── parallel.py # asyncio pool runner
├── api/
│   ├── main.py      # FastAPI
│   └── schemas.py   # Pydantic
├── frontend/
│   ├── index.html
│   ├── main.js
│   └── style.css
├── cli.py           # CLI entry point
├── pyproject.toml
└── CLAUDE.md
```

## Conventions
- **uv** for all package management — no pip, no poetry
- Engine has zero FastAPI/web imports — pure Python library
- Markdown extraction: no LLM, use readability heuristic (title + text content)
- Session cookie: never log, never expose in API responses
- Verbosity levels: `-q` (errors only), default (warn+success), `-v` (+ each URL), `-vv` (+ timing/HTML size)
- Output filenames: `linkedin-{slugged-name}-{timestamp}.md`
- Graceful expiry: detect expired session via redirect to login wall, raise `SessionExpiredError`
