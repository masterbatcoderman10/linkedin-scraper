# LinkedIn Scraper — Tasks

## Sprint 1: Foundation

- [ ] `pyproject.toml` + virtual environment setup with uv
- [ ] `CLAUDE.md` with project conventions and model routing rules
- [ ] `engine/session.py` — Firefox cookie extraction + JSON session file read/write
- [ ] `engine/scraper.py` — camoufox browser engine, page→markdown extraction
- [ ] `engine/parallel.py` — asyncio pool runner with concurrency control
- [ ] `engine/__init__.py` — clean engine API export
- [ ] `cli.py` — standalone CLI with all input modes, verbosity, Tenacity retry
- [ ] `api/schemas.py` — Pydantic request/response models
- [ ] `api/main.py` — FastAPI server with scrape endpoint
- [ ] `frontend/index.html` + `main.js` + `style.css` — minimal UI
- [ ] Smoke test: single profile URL → verify markdown output
- [ ] Batch test: 3 URLs in parallel → verify concurrency + clean output
