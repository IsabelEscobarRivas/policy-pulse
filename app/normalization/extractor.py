import hashlib
import logging
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from typing import Optional

from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

_TAGS_TO_REMOVE = ["script", "style", "nav", "header", "footer"]


def _utcnow_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_serp_response(response: dict, source_url: str) -> dict:
    """Normalize Bright Data SERP JSON. Unused for current sources (all use unlocker)."""
    logger.debug(f"SERP response keys: {list(response.keys())}")

    general = response.get("general") or {}
    if not isinstance(general, dict):
        general = {}

    title = general.get("page_title") or ""
    organic_results = response.get("organic") or []
    if not organic_results:
        organic_results = response.get("results") or []
    if not isinstance(organic_results, list):
        organic_results = []

    if not title and organic_results:
        first_result = organic_results[0]
        if isinstance(first_result, dict):
            title = first_result.get("title") or ""

    descriptions = []
    for result in organic_results:
        if not isinstance(result, dict):
            continue
        description = result.get("description")
        if description:
            descriptions.append(description)

    body = " ".join(descriptions)
    if not body:
        titles = []
        for result in organic_results:
            if not isinstance(result, dict):
                continue
            result_title = result.get("title")
            if result_title:
                titles.append(result_title)
        body = " ".join(titles)
    if not body:
        body = general.get("query") or ""

    timestamp = general.get("timestamp") or _utcnow_isoformat()

    return {
        "title": title,
        "body": body,
        "timestamp": timestamp,
        "source_url": source_url,
    }


def normalize_api_response(response: dict, source_url: str) -> dict:
    title = f"USCIS Federal Register Updates - {date.today().isoformat()}"

    parts = []
    results = response.get("results") or []
    if not isinstance(results, list):
        results = []
    for result in results:
        if not isinstance(result, dict):
            continue
        result_title = result.get("title") or ""
        abstract = result.get("abstract") or ""
        parts.append(f"{result_title} {abstract}".strip())

    body = " ".join(part for part in parts if part)

    return {
        "title": title,
        "body": body,
        "timestamp": _utcnow_isoformat(),
        "source_url": source_url,
    }


def _xml_local_tag(tag: str) -> str:
    return tag.split("}")[-1] if "}" in tag else tag


def _xml_find_text(element: Optional[ET.Element], local_name: str) -> str:
    if element is None:
        return ""
    for child in element:
        if _xml_local_tag(child.tag) == local_name and child.text:
            return child.text.strip()
    return ""


def normalize_rss_response(xml: str, source_url: str) -> dict:
    root = ET.fromstring(xml)
    channel = root.find("channel")
    if channel is None:
        for child in root:
            if _xml_local_tag(child.tag) == "channel":
                channel = child
                break

    title = _xml_find_text(channel, "title") or "USCIS Newsroom"

    parts = []
    for item in root.iter():
        if _xml_local_tag(item.tag) != "item":
            continue
        item_title = _xml_find_text(item, "title")
        description = _xml_find_text(item, "description")
        if item_title:
            parts.append(item_title)
        if description:
            parts.append(description)

    body = " ".join(parts)

    return {
        "title": title,
        "body": body,
        "timestamp": _utcnow_isoformat(),
        "source_url": source_url,
    }


def normalize_html_response(html: str, source_url: str) -> dict:
    soup = BeautifulSoup(html, "lxml")

    for tag_name in _TAGS_TO_REMOVE:
        for tag in soup.find_all(tag_name):
            tag.decompose()

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()

    body = soup.get_text(separator=" ", strip=True)

    return {
        "title": title,
        "body": body,
        "timestamp": _utcnow_isoformat(),
        "source_url": source_url,
    }


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
