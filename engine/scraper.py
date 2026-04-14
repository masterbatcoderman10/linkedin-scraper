from __future__ import annotations

import logging
import re
from typing import Optional

from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


class SessionExpiredError(Exception):
    pass


class BlockedError(Exception):
    pass


_HEADING_TAGS = {
    "h1": "#",
    "h2": "##",
    "h3": "###",
    "h4": "####",
    "h5": "#####",
    "h6": "######",
}
_STRIP_TAGS = {"script", "style", "nav", "footer", "noscript", "svg", "path", "img"}


class LinkedInScraper:
    def __init__(self, cookies: dict[str, str], headless: bool = True):
        self.cookies = cookies
        self.headless = headless

    def scrape(self, url: str) -> str:
        import camoufox

        logger.info("Launching browser (headless=%s)", self.headless)

        browser = camoufox.launch(headless=self.headless)
        try:
            context = browser.new_context()
            try:
                cookie_list = [
                    {
                        "name": name,
                        "value": value,
                        "domain": ".linkedin.com",
                        "path": "/",
                    }
                    for name, value in self.cookies.items()
                ]
                if cookie_list:
                    context.add_cookies(cookie_list)

                page = context.new_page()
                try:
                    logger.info("Navigating to %s", url)
                    page.goto(url, wait_until="networkidle", timeout=30000)

                    current_url = page.url
                    self._check_session(current_url, page)

                    content = page.content()
                    logger.debug("Page content length: %d chars", len(content))
                finally:
                    page.close()
            finally:
                context.close()
        finally:
            browser.close()

        return self._html_to_markdown(content)

    def _check_session(self, current_url: str, page) -> None:
        if re.search(r"/login|/checkpoint", current_url, re.IGNORECASE):
            raise SessionExpiredError(
                "Session expired \u2014 please re-authenticate in Firefox"
            )

        title = page.title() or ""
        lower_title = title.lower()
        if "access restricted" in lower_title or "blocked" in lower_title:
            raise BlockedError(f"Access blocked: {title}")

    def _html_to_markdown(self, html: str) -> str:
        soup = BeautifulSoup(html, "lxml")

        for tag_name in _STRIP_TAGS:
            for tag in soup.find_all(tag_name):
                tag.decompose()

        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else ""
        parts: list[str] = []

        if title:
            parts.append(f"# {title}")
            parts.append("")

        body = soup.find("body")
        if not body:
            body = soup

        self._walk_node(body, parts)

        return "\n".join(parts).strip()

    def _walk_node(self, node: Tag, parts: list[str]) -> None:
        for child in node.children:
            if isinstance(child, Tag):
                tag_name = child.name.lower() if child.name else ""

                if tag_name in _HEADING_TAGS:
                    text = child.get_text(strip=True)
                    if text:
                        parts.append(f"{_HEADING_TAGS[tag_name]} {text}")
                        parts.append("")

                elif tag_name == "p":
                    text = child.get_text(separator=" ", strip=True)
                    if text:
                        parts.append(text)
                        parts.append("")

                elif tag_name in ("ul", "ol"):
                    for i, li in enumerate(child.find_all("li", recursive=False)):
                        text = li.get_text(separator=" ", strip=True)
                        if text:
                            if tag_name == "ol":
                                parts.append(f"{i + 1}. {text}")
                            else:
                                parts.append(f"- {text}")
                    parts.append("")

                elif tag_name == "li":
                    text = child.get_text(separator=" ", strip=True)
                    if text:
                        parts.append(f"- {text}")

                elif tag_name == "br":
                    parts.append("")

                elif tag_name == "a":
                    text = child.get_text(strip=True)
                    if text:
                        parts.append(text)

                elif tag_name in (
                    "div",
                    "section",
                    "main",
                    "article",
                    "span",
                    "strong",
                    "em",
                    "b",
                    "i",
                ):
                    self._walk_node(child, parts)
