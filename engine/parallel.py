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


class RateLimitError(Exception):
    """LinkedIn rate-limited the session — back off and retry."""
    pass


class TransientError(Exception):
    pass


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, (SessionExpiredError, BlockedError)):
        return False
    return True


def _is_rate_limit(exc: BaseException) -> bool:
    """Detect LinkedIn rate-limit errors from curl_cffi or connection failures."""
    msg = str(exc).lower()
    # curl_cffi TLS/network errors that indicate rate limiting
    if "tls13_downgrade" in msg:
        return True
    if "too many redirects" in msg and "linkedin" in msg:
        return True
    # Connection reset/timeout after successful requests often means rate limit
    if isinstance(exc, (ConnectionResetError, TimeoutError)):
        return True
    return False


@retry(
    retry=retry_if_exception_type((TransientError, RateLimitError)),
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=2, min=3, max=60),
    reraise=True,
)
async def _scrape_one(
    scraper: LinkedInScraper, url: str, verbose: bool, attempt: int = 1
) -> dict[str, Any]:
    loop = asyncio.get_running_loop()
    t0 = time.monotonic()

    try:
        markdown = await loop.run_in_executor(None, scraper.scrape, url)
        elapsed = time.monotonic() - t0
        if verbose:
            logger.info("OK %s (%.1fs, attempt %d)", url, elapsed, attempt)
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
        if _is_rate_limit(e):
            if verbose:
                logger.warning("RATE_LIMIT %s (%.1fs, attempt %d): %s", url, elapsed, attempt, e)
            raise RateLimitError(str(e)) from e
        if verbose:
            logger.error("FAIL %s (%.1fs, attempt %d): %s", url, elapsed, attempt, e)
        raise TransientError(str(e)) from e


async def _run_all(
    urls: list[str],
    cookies: dict[str, str],
    concurrency: int,
    verbose: bool,
    stagger_delay: float,
) -> list[dict[str, Any]]:
    sem = asyncio.Semaphore(concurrency)
    results: list[dict[str, Any]] = []
    scraper = LinkedInScraper(cookies=cookies, headless=True)

    async def _bounded(url: str, index: int) -> dict[str, Any]:
        # Stagger: each task waits stagger_delay * index before acquiring the semaphore
        # This prevents all N concurrent requests from firing at the same instant
        if stagger_delay > 0 and index > 0:
            wait_time = stagger_delay * index
            if verbose:
                logger.info("Stagger: waiting %.1fs before %s", wait_time, url)
            await asyncio.sleep(wait_time)

        async with sem:
            try:
                return await _scrape_one(scraper, url, verbose)
            except (TransientError, RateLimitError) as e:
                return {
                    "url": url,
                    "markdown": None,
                    "status": "error",
                    "error": str(e),
                }

    tasks = [_bounded(url, i) for i, url in enumerate(urls)]
    results = await asyncio.gather(*tasks)
    return list(results)


def scrape_parallel(
    urls: list[str],
    cookies: dict[str, str],
    concurrency: int = 3,
    verbose: bool = False,
    stagger_delay: float = 1.5,
) -> list[dict[str, Any]]:
    """
    Scrape multiple LinkedIn profile URLs in parallel with bounded concurrency
    and staggered request timing to avoid rate limits.

    Args:
        urls: List of LinkedIn profile URLs to scrape.
        cookies: Session cookies dict (from load_session_file or extract_firefox_cookies).
        concurrency: Max simultaneous requests (default 3).
        verbose: Print per-URL progress.
        stagger_delay: Seconds to wait between each request start (default 1.5).
                      With concurrency=3, stagger_delay=1.5:
                        URL0: starts immediately
                        URL1: starts at 1.5s
                        URL2: starts at 3.0s
    """
    return asyncio.run(_run_all(urls, cookies, concurrency, verbose, stagger_delay))
