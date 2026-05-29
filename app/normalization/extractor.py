import hashlib
from datetime import datetime, timezone

from bs4 import BeautifulSoup

_TAGS_TO_REMOVE = ["script", "style", "nav", "header", "footer"]


def _utcnow_isoformat() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_serp_response(response: dict, source_url: str) -> dict:
    general = response.get("general", {})
    title = general.get("page_title") or ""

    descriptions = []
    for result in response.get("organic", []):
        description = result.get("description")
        if description:
            descriptions.append(description)

    body = " ".join(descriptions)
    timestamp = general.get("timestamp") or _utcnow_isoformat()

    return {
        "title": title,
        "body": body,
        "timestamp": timestamp,
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
