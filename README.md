# LinkedIn Profile Scraper

Extract any LinkedIn profile as clean markdown using your own Firefox session cookies. No LinkedIn login, no API keys, no Selenium grid — just bring your authenticated browser session.

```
linkedin-scrape https://linkedin.com/in/satya-nadella
```

```
linkedin-scrape --input profiles.txt --parallel 4 --output ./profiles/
```

## Features

- **Your session, your cookies** — authenticate once in Firefox, export with one command, scrape forever
- **Parallel scraping** — process multiple profiles concurrently with staggered requests to avoid rate limits
- **Graceful retry** — Tenacity-powered retry with exponential backoff on network errors and rate limits
- **Multiple interfaces** — CLI for scripts, FastAPI for server deployments, React frontend for local use
- **Session portability** — export on your Mac, use on any machine with `curl_cffi` impersonation
- **Session expiry handling** — clear error when `li_at` goes stale, prompts for re-auth

## Installation

Requires Python 3.9+ and `uv`.

```bash
git clone https://github.com/masterbatcoderman10/linkedin-scraper.git
cd linkedin-scraper
uv sync
```

That's it. No API keys, no browser drivers, no cloud services.

## Quick Start

### 1. Export your Firefox session

In Firefox, install the **EditThisCookie** extension, export your `li_at` cookie (and optionally others) as JSON, then:

```bash
linkedin-scrape --export-session ./my-session.json
```

Or use the browser-based approach — the extension is the easiest:

1. Go to linkedin.com and log in
2. Open EditThisCookie, click **Export** → **Export as JSON**
3. Save as `linkedin-session.json`

### 2. Scrape a profile

```bash
# Single profile
linkedin-scrape https://linkedin.com/in/satya-nadella --session ./linkedin-session.json

# Multiple profiles from a file (one URL per line)
linkedin-scrape --input urls.txt --parallel 4 --output ./profiles/

# Interactive mode
linkedin-scrape --interactive
```

### 3. Run the API server

```bash
uv run uvicorn api.main:app --reload
```

Then open `http://localhost:8000` in your browser for the web UI, or POST to the API:

```bash
curl -X POST http://localhost:8000/api/scrape \
  -H "Content-Type: application/json" \
  -d '{"url": "https://linkedin.com/in/satya-nadella"}'
```

## CLI Reference

```
linkedin-scrape [url] [options]

positional:
  url                      LinkedIn profile URL to scrape

options:
  --session PATH           Path to session JSON file (exported from Firefox)
  --input PATH             File with URLs to scrape (one per line)
  --parallel N             Number of concurrent requests (default: 1)
  --stagger-delay SECONDS  Delay between request starts in parallel mode (default: 1.5)
  --output DIR             Output directory for markdown files (default: ./output/)
  --export-session PATH    Extract cookies from Firefox and save to JSON, then exit
  -v, -vv                  Increase verbosity (-vv shows retry details)
  -q, --quiet              Suppress output except errors
  --interactive            Interactive prompt mode
```

## Session Management

### Export from Firefox

```bash
# Option 1: CLI export (reads your Firefox profile directly)
linkedin-scrape --export-session ./my-session.json

# Option 2: EditThisCookie browser extension
# 1. Go to linkedin.com and log in
# 2. Export cookies as JSON from EditThisCookie
# 3. Pass that file with --session
```

### Session JSON format

```json
{
  "cookies": [
    {"name": "li_at", "value": "AQEDAH..."},
    {"name": "JSESSIONID", "value": "..."}
  ],
  "exported_at": "2025-04-15T12:00:00Z"
}
```

### Refreshing a stale session

When sessions expire you'll see `SessionExpiredError` or "Sign in to view" responses. Re-authenticate:

```bash
# Re-export fresh cookies
linkedin-scrape --export-session ./my-session.json

# Or manually refresh via browser extension
# Then retry your scrape
linkedin-scrape --session ./my-session.json https://linkedin.com/in/target-profile
```

## Architecture

```
linkedin-scraper/
├── engine/
│   ├── session.py      # Firefox cookie extraction, session JSON read/write
│   ├── scraper.py      # HTTP scraping engine with curl_cffi + BeautifulSoup
│   └── parallel.py     # Async parallel runner with rate-limit handling
├── api/
│   ├── main.py         # FastAPI server + web frontend
│   └── schemas.py      # Pydantic request/response models
├── cli.py              # Standalone CLI with all input modes
└── frontend/           # Minimal React-style web UI
```

**Scraping engine**: Uses `curl_cffi` to impersonate Firefox's TLS fingerprint. This bypasses LinkedIn's bot detection without needing a real browser. BeautifulSoup converts the HTML response to clean markdown.

**Parallel runner**: Uses Python `asyncio` with a semaphore to bound concurrency. Each request starts with a stagger delay to avoid burst rate limits. `RateLimitError` triggers a dedicated 5-attempt exponential backoff retry (max 60s).

## Troubleshooting

### "Sign in to view" or redirect loop

Your session cookies are stale. Re-export fresh cookies from Firefox:

```bash
linkedin-scrape --export-session ./my-session.json
```

### TLS13_DOWNGRADE error

LinkedIn rate-limited you. The scraper retries automatically, but for large batches increase the stagger delay:

```bash
linkedin-scrape --input large_batch.txt --parallel 2 --stagger-delay 3.0
```

### Network timeout

Increase the request timeout:

```bash
# Edit engine/scraper.py — default is 30s
# Or run the API server and adjust via the web UI
```

## Development

```bash
# Activate venv
source .venv/bin/activate

# Run tests
python -m pytest

# Lint
ruff check .

# Format
ruff format .
```

## License

MIT. Use freely. LinkedIn's Terms of Service apply to your use of their platform.
