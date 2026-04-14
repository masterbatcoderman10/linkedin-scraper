from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from .scraper import BlockedError, LinkedInScraper, SessionExpiredError

logger = logging.getLogger(__name__)


class TransientError(Exception):
    pass


class _RetryableError(Exception):
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (SessionExpiredError, BlockedError)):
        return False
    return True


@retry(
    retry=retry_if_exception_type(_RetryableError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=30),
    reraise=True,
)
async def _scrape_one(
    scraper: LinkedInScraper, url: str, verbose: bool
) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    t0 = time.monotonic()

    try:
        markdown = await loop.run_in_executor(None, scraper.scrape, url)
        elapsed = time.monotonic() - t0
        if verbose:
            logger.info("OK %s (%.1fs)", url, elapsed)
        return {"url": url, "markdown": markdown, "status": "ok", "error": None}
    except SessionExpiredError as e:
        elapsed = time.monotonic() - t0
        if verbose:
            logger.error("EXPIRED %s (%.1fs): %s", url, elapsed, e)
        return {"url": url, "markdown": None, "status": "error", "error": str(e)}
    except BlockedError as e:
        elapsed = time.monotonic() - t0
        if verbose:
            logger.error("BLOCKED %s (%.1fs): %s", url, elapsed, e)
        return {"url": url, "markdown": None, "status": "error", "error": str(e)}
    except Exception as e:
        elapsed = time.monotonic() - t0
        if verbose:
            logger.error("FAIL %s (%.1fs): %s", url, elapsed, e)
        raise _RetryableError(str(e)) from e


async def _run_all(
    urls: list[str],
    cookies: dict[str, str],
    concurrency: int,
    verbose: bool,
) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)
    results: list[dict[str, Any]] = []
    scraper = LinkedInScraper(cookies=cookies, headless=True)

    async def _bounded(url: str) -> dict[str, Any]:
        async with sem:
            try:
                return await _scrape_one(scraper, url, verbose)
            except _RetryableError as e:
                return {
                    "url": url,
                    "markdown": None,
                    "status": "error",
                    "error": str(e),
                }

    tasks = [_bounded(url) for url in urls]
    results = await asyncio.gather(*tasks)
    return list(results)


def scrape_parallel(
    urls: list[str],
    cookies: dict[str, str],
    concurrency: int = 3,
    verbose: bool = False,
) -> list[dict[str, Any]]:
    return asyncio.run(_run_all(urls, cookies, concurrency, verbose))
