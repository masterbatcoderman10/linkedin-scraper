from __future__ import annotations

import logging
from typing import Optional

from bs4 import BeautifulSoup, Tag
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

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

    @retry(
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    def scrape(self, url: str) -> str:
        import curl_cffi.requests as cfreq

        logger.info("Fetching %s (curl_cffi Firefox impersonation)", url)

        session = cfreq.Session(impersonate="firefox135")
        for name, value in self.cookies.items():
            session.cookies.set(name, value)

        resp = session.get(url, timeout=30)
        content = resp.text
        final_url = resp.url

        # Detect redirect to login
        if resp.status_code in (301, 302, 303, 307, 308):
            loc = resp.headers.get("Location", "")
            if loc and "login" in loc.lower():
                raise SessionExpiredError(
                    "Session expired — redirected to login page"
                )

        if resp.status_code == 999:
            raise BlockedError("LinkedIn rate-limited or IP blocked (status 999)")

        logger.info("Got %d bytes from %s", len(content), final_url)
        return self._html_to_markdown(content)

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
