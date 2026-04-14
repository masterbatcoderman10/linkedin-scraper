from __future__ import annotations

import json
import logging
from pathlib import Path

import fastapi
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse

from engine import (
    LinkedInScraper,
    SessionExpiredError,
    BlockedError,
    extract_firefox_cookies,
    load_session_file,
    save_session_file,
    scrape_parallel,
)

from .schemas import ScrapeRequest, ScrapeResponse, ScrapeResult

app = FastAPI()
logger = logging.getLogger(__name__)

SESSION_DIR = Path.home() / ".linkedin-scraper"
SESSION_FILE = SESSION_DIR / "session.json"


def _get_session_path() -> Path:
    return SESSION_FILE


def _load_cookies() -> tuple[dict[str, str], str]:
    session_file = _get_session_path()
    if session_file.is_file():
        cookies = load_session_file(str(session_file))
        if cookies:
            return cookies, "file"

    try:
        cookies = extract_firefox_cookies()
        if cookies:
            return cookies, "firefox"
    except Exception as e:
        logger.warning("Could not extract Firefox cookies: %s", e)

    return {}, "none"


@app.get("/")
def serve_frontend() -> FileResponse:
    return FileResponse(Path(__file__).parent.parent / "frontend" / "index.html")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/session/status")
def session_status() -> dict[str, object]:
    session_file = _get_session_path()
    if session_file.is_file():
        cookies = load_session_file(str(session_file))
        if cookies:
            return {"has_session": True, "source": "file"}

    try:
        cookies = extract_firefox_cookies()
        if cookies:
            return {"has_session": True, "source": "firefox"}
    except Exception:
        pass

    return {"has_session": False, "source": "none"}


@app.post("/api/scrape")
def scrape(request: ScrapeRequest) -> ScrapeResponse:
    cookies, source = _load_cookies()
    if not cookies:
        raise HTTPException(status_code=401, detail="No session available")

    urls: list[str] = []
    if request.url:
        urls.append(request.url)
    if request.urls:
        urls.extend(request.urls)

    if not urls:
        raise HTTPException(status_code=400, detail="No URL provided")

    logging.basicConfig(level=logging.ERROR)
    for handler in logging.root.handlers:
        handler.setLevel(logging.ERROR)

    results: list[ScrapeResult] = []

    try:
        if len(urls) == 1 and request.parallel <= 1:
            scraper = LinkedInScraper(cookies=cookies, headless=True)
            try:
                markdown = scraper.scrape(urls[0])
                results.append(
                    ScrapeResult(url=urls[0], markdown=markdown, status="ok")
                )
            except SessionExpiredError as e:
                results.append(ScrapeResult(url=urls[0], status="error", error=str(e)))
            except BlockedError as e:
                results.append(ScrapeResult(url=urls[0], status="error", error=str(e)))
        else:
            raw_results = scrape_parallel(
                urls=urls,
                cookies=cookies,
                concurrency=request.parallel,
                verbose=False,
            )
            for r in raw_results:
                results.append(
                    ScrapeResult(
                        url=r["url"],
                        markdown=r.get("markdown"),
                        status=r["status"],
                        error=r.get("error"),
                    )
                )
    except SessionExpiredError as e:
        for url in urls:
            results.append(ScrapeResult(url=url, status="error", error=str(e)))
    except Exception as e:
        for url in urls:
            results.append(ScrapeResult(url=url, status="error", error=str(e)))

    return ScrapeResponse(results=results)


@app.post("/api/session/load")
async def load_session(file: fastapi.UploadFile) -> dict[str, str]:
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Must be a JSON file")

    try:
        content = await file.read()
        data = json.loads(content.decode("utf-8"))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {e}")

    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail="Session must be a JSON object")

    cookies: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, str):
            cookies[key] = value

    if not cookies:
        raise HTTPException(status_code=400, detail="No cookies found in session file")

    SESSION_DIR.mkdir(parents=True, exist_ok=True)
    save_session_file(str(_get_session_path()), cookies)

    return {"status": "ok", "message": f"Session loaded ({len(cookies)} cookies)"}


def run() -> None:
    uvicorn.run(app, host="0.0.0.0", port=8000)
