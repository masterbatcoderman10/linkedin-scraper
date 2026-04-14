from __future__ import annotations

import json
import logging
import shutil
import sqlite3
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

FIREFOX_PROFILES_DIR = (
    Path.home() / "Library" / "Application Support" / "Firefox" / "Profiles"
)
FIREFOX_PROFILE = FIREFOX_PROFILES_DIR / "6rd2ksu0.default-release"


class FirefoxProfileNotFoundError(Exception):
    pass


class SessionNotFoundError(Exception):
    pass


def _mask_cookie_value(value: str) -> str:
    if len(value) <= 12:
        return "*" * len(value)
    return value[:8] + "..." + value[-4:]


def extract_firefox_cookies(profile_path: Optional[str] = None) -> dict[str, str]:
    profile = Path(profile_path) if profile_path else FIREFOX_PROFILE

    if not profile.is_dir():
        raise FirefoxProfileNotFoundError(f"Firefox profile not found: {profile}")

    cookies_db = profile / "cookies.sqlite"
    if not cookies_db.is_file():
        raise FirefoxProfileNotFoundError(
            f"cookies.sqlite not found in profile: {cookies_db}"
        )

    tmp = Path(tempfile.mktemp(suffix=".sqlite"))
    shutil.copy2(str(cookies_db), str(tmp))

    try:
        conn = sqlite3.connect(str(tmp))
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name, value FROM moz_cookies "
            "WHERE host LIKE '%linkedin%' OR host LIKE '%li.%'"
        )
        rows = cursor.fetchall()
        conn.close()
    finally:
        tmp.unlink(missing_ok=True)

    cookies: dict[str, str] = {}
    for name, value in rows:
        cookies[name] = value

    if not cookies:
        logger.warning("No LinkedIn cookies found in Firefox profile")

    for name, value in cookies.items():
        logger.debug("Cookie: %s=%s", name, _mask_cookie_value(value))

    return cookies


def load_session_file(path: str) -> dict[str, str]:
    p = Path(path)
    if not p.is_file():
        raise SessionNotFoundError(f"Session file not found: {p}")

    with open(p, "r", encoding="utf-8") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise SessionNotFoundError(f"Invalid session file format: {p}")

    cookies: dict[str, str] = {}
    for key, value in data.items():
        if isinstance(value, str):
            cookies[key] = value
            logger.debug("Loaded cookie: %s=%s", key, _mask_cookie_value(value))

    return cookies


def save_session_file(path: str, cookies: dict[str, str]) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)

    with open(p, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)

    for name, value in cookies.items():
        logger.debug("Saved cookie: %s=%s", name, _mask_cookie_value(value))

    logger.info("Session saved to %s (%d cookies)", p, len(cookies))
