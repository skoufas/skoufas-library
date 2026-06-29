"""Fetch book cover images from external providers (Google Books, OpenLibrary)."""

import logging
from dataclasses import dataclass
from typing import Optional

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

_TIMEOUT = 10  # seconds


@dataclass
class CoverResult:
    """A successfully fetched cover image."""

    image_bytes: bytes
    content_type: str  # e.g. "image/jpeg"
    source: str  # e.g. "Google Books" or "OpenLibrary"


def _fetch_google_books(isbn: str) -> Optional[CoverResult]:
    """Try to fetch a cover image from the Google Books API."""
    api_key = getattr(settings, "GOOGLE_BOOKS_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = requests.get(
            "https://www.googleapis.com/books/v1/volumes",
            params={"q": f"isbn:{isbn}", "key": api_key},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Google Books API error for ISBN %s: %s", isbn, exc)
        return None

    data = resp.json()
    items = data.get("items")
    if not items:
        return None

    image_links = items[0].get("volumeInfo", {}).get("imageLinks", {})
    for size in ("extraLarge", "large", "medium", "small", "thumbnail", "smallThumbnail"):
        url = image_links.get(size)
        if not url:
            continue
        try:
            img_resp = requests.get(url, timeout=_TIMEOUT)
            img_resp.raise_for_status()
            content_type = img_resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
            return CoverResult(
                image_bytes=img_resp.content,
                content_type=content_type,
                source="Google Books",
            )
        except requests.RequestException as exc:
            logger.warning("Failed to download Google Books image for ISBN %s: %s", isbn, exc)

    return None


def _fetch_openlibrary_by_key(key_type: str, key_value: str) -> Optional[CoverResult]:
    """Fetch from OpenLibrary using a given key type (isbn, ean, etc.)."""
    url = f"https://covers.openlibrary.org/b/{key_type}/{key_value}-L.jpg"
    try:
        resp = requests.get(url, timeout=_TIMEOUT)
        resp.raise_for_status()
        # OpenLibrary returns a tiny placeholder GIF when there is no cover
        if len(resp.content) < 1000:
            return None
        content_type = resp.headers.get("Content-Type", "image/jpeg").split(";")[0].strip()
        return CoverResult(
            image_bytes=resp.content,
            content_type=content_type,
            source="OpenLibrary",
        )
    except requests.RequestException as exc:
        logger.warning("OpenLibrary error for %s %s: %s", key_type, key_value, exc)
        return None


def _is_book_ean(ean: str) -> bool:
    """Return True if the EAN is a book EAN (starts with 978 or 979)."""
    return ean.startswith("978") or ean.startswith("979")


def fetch_cover(isbn: str = "", ean: str = "") -> Optional[CoverResult]:
    """Try Google Books then OpenLibrary using ISBN, then EAN as fallback."""
    if isbn:
        result = _fetch_google_books(isbn)
        if result:
            return result
        result = _fetch_openlibrary_by_key("isbn", isbn)
        if result:
            return result
    if ean and _is_book_ean(ean):
        # EAN-13 starting with 978/979 is numerically identical to ISBN-13
        result = _fetch_google_books(ean)
        if result:
            return result
        result = _fetch_openlibrary_by_key("ean", ean)
        if result:
            return result
    return None
