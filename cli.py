#!/usr/bin/env python3
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from engine import (
    LinkedInScraper,
    SessionExpiredError,
    BlockedError,
    extract_firefox_cookies,
    load_session_file,
    save_session_file,
    scrape_parallel,
)


def _slug_from_url(url: str) -> str:
    parsed = urlparse(url)
    parts = parsed.path.strip("/").split("/")
    if "in" in parts:
        idx = parts.index("in")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    if parts:
        return parts[-1].rstrip("/")
    return "unknown"


def _setup_logging(verbose: int) -> None:
    if verbose == 0:
        level = logging.WARNING
    elif verbose == 1:
        level = logging.INFO
    else:
        level = logging.DEBUG

    logging.basicConfig(
        level=level,
        format="%(message)s",
    )


def _load_cookies(session_file: str | None) -> dict[str, str]:
    if session_file:
        return load_session_file(session_file)

    session_path = Path.home() / ".linkedin-scraper" / "session.json"
    if session_path.is_file():
        try:
            return load_session_file(str(session_path))
        except Exception:
            pass

    try:
        return extract_firefox_cookies()
    except Exception:
        return {}


def _scrape_single(
    url: str,
    cookies: dict[str, str],
    headless: bool,
) -> tuple[str, str | None, str | None]:
    scraper = LinkedInScraper(cookies=cookies, headless=headless)
    try:
        markdown = scraper.scrape(url)
        return url, markdown, None
    except SessionExpiredError as e:
        return url, None, str(e)
    except BlockedError as e:
        return url, None, str(e)
    except Exception as e:
        return url, None, str(e)


def _write_output(
    output_dir: Path, url: str, markdown: str | None, error: str | None
) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    slug = _slug_from_url(url)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"linkedin-{slug}-{timestamp}.md"
    filepath = output_dir / filename

    content = f"# Source: {url}\n\n"
    if error:
        content += f"**Error**: {error}\n\n"
    if markdown:
        content += markdown

    filepath.write_text(content, encoding="utf-8")
    return filepath


def _interactive_input() -> list[str]:
    print("Enter URLs (one per line), empty line to finish:")
    urls: list[str] = []
    while True:
        try:
            line = input().strip()
            if not line:
                break
            urls.append(line)
        except EOFError:
            break
    return urls


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="linkedin-scrape",
        description="LinkedIn profile scraper",
    )
    parser.add_argument("url", nargs="?", help="Single LinkedIn profile URL")
    parser.add_argument("--input", metavar="FILE", help="File with URLs (one per line)")
    parser.add_argument("--session", metavar="FILE", help="JSON session file path")
    parser.add_argument(
        "--output-dir",
        default="./output",
        metavar="DIR",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=3,
        metavar="N",
        help="Concurrency level (default: 3)",
    )
    parser.add_argument(
        "-v", "--verbose", action="count", help="Print each URL as processed"
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Errors only")
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run browser headless (default: True)",
    )
    parser.add_argument(
        "--export-session",
        metavar="PATH",
        help="Extract cookies from Firefox and save to PATH, then exit",
    )

    args = parser.parse_args()

    verbose = 0
    if args.quiet:
        verbose = -1
    elif args.verbose:
        verbose = args.verbose

    _setup_logging(verbose)
    logger = logging.getLogger()

    if args.export_session:
        cookies = extract_firefox_cookies()
        if not cookies:
            print("Error: No LinkedIn cookies found in Firefox", file=sys.stderr)
            return 2
        save_session_file(args.export_session, cookies)
        print(f"Exported {len(cookies)} cookies to {args.export_session}")
        return 0

    output_dir = Path(args.output_dir)

    urls: list[str] = []
    if args.input:
        input_path = Path(args.input)
        if not input_path.is_file():
            print(f"Error: Input file not found: {input_path}", file=sys.stderr)
            return 2
        content = input_path.read_text(encoding="utf-8")
        urls = [line.strip() for line in content.splitlines() if line.strip()]
    elif args.url:
        urls = [args.url]
    else:
        urls = _interactive_input()

    if not urls:
        print("Error: No URLs provided", file=sys.stderr)
        return 2

    cookies = _load_cookies(args.session)
    if not cookies:
        print("Error: No session cookies available", file=sys.stderr)
        return 2

    ok_count = 0
    error_count = 0

    if len(urls) == 1 and args.parallel <= 1:
        url = urls[0]
        _, markdown, error = _scrape_single(url, cookies, args.headless)
        filepath = _write_output(output_dir, url, markdown, error)
        if error:
            error_count = 1
            print(f"ERROR: {error}")
        else:
            ok_count = 1
            print(f"OK {url} -> {filepath}")
    else:
        raw_results = scrape_parallel(
            urls=urls,
            cookies=cookies,
            concurrency=args.parallel,
            verbose=(verbose >= 1),
        )

        for r in raw_results:
            url = r["url"]
            markdown = r.get("markdown")
            error = r.get("error")
            status = r["status"]

            filepath = _write_output(output_dir, url, markdown, error)

            if status == "ok":
                ok_count += 1
                if verbose >= 1:
                    print(f"OK {url} -> {filepath}")
            else:
                error_count += 1
                print(f"ERROR {url}: {error}")

    total = len(urls)
    print(f"\n{ok_count}/{total} succeeded, {error_count}/{total} failed")

    if error_count == 0:
        return 0
    elif ok_count == 0:
        return 2
    else:
        return 1


if __name__ == "__main__":
    sys.exit(main())
