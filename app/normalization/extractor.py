import hashlib
import logging
import re
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


_ILW_STRIP_CLASSES = ("advertisement", "sidebar", "footer", "header", "menu")


def _decompose_by_class_names(soup, class_names) -> None:
    for element in soup.find_all(class_=True):
        classes = element.get("class") or []
        if isinstance(classes, str):
            classes = [classes]
        if any(
            any(cls_name in cls or cls in cls_name for cls in classes)
            for cls_name in class_names
        ):
            element.decompose()


def _safe_html_defaults(source_url: str) -> dict:
    return {
        "title": "",
        "body": "",
        "timestamp": datetime.utcnow().isoformat(),
        "source_url": source_url,
    }


_BULLETIN_MONTH_RE = re.compile(
    r"\b(January|February|March|April|May|June|July|August|September|"
    r"October|November|December)\s+(20\d{2})\b",
    re.IGNORECASE,
)
_CATEGORY_RE = re.compile(
    r"\b(EB-[1235]|F-[1-4][AB]?|F-[12]|L-[12]|DV)\b",
    re.IGNORECASE,
)


def _normalize_category_label(text: str) -> str:
    if not text:
        return "UNKNOWN"
    match = _CATEGORY_RE.search(text)
    if match:
        return match.group(1).upper()
    cleaned = text.strip()
    return cleaned[:40].strip() if cleaned else "UNKNOWN"


def _extract_bulletin_period(soup) -> str:
    candidates = []
    if soup.title and soup.title.string:
        candidates.append(soup.title.string)
    h1 = soup.find("h1")
    if h1 is not None:
        candidates.append(h1.get_text(separator=" ", strip=True))
    for heading in soup.find_all(["h2", "h3"], limit=20):
        candidates.append(heading.get_text(separator=" ", strip=True))

    for text in candidates:
        match = _BULLETIN_MONTH_RE.search(text or "")
        if match:
            return f"{match.group(1).title()} {match.group(2)}"
    return "UNKNOWN PERIOD"


def _category_for_table(table) -> str:
    caption = table.find("caption")
    if caption is not None:
        category = _normalize_category_label(
            caption.get_text(separator=" ", strip=True)
        )
        if category != "UNKNOWN":
            return category

    for heading in table.find_all_previous(["h2", "h3"], limit=8):
        if heading is None:
            continue
        text = heading.get_text(separator=" ", strip=True) or ""
        if not text:
            continue
        category = _normalize_category_label(text)
        if category != "UNKNOWN":
            return category
    return "UNKNOWN"


def _column_map(header_cells: list[str]) -> dict[str, int]:
    mapping: dict[str, int] = {}
    for index, cell in enumerate(header_cells):
        lower = (cell or "").lower()
        if "country" in lower or "chargeability" in lower:
            mapping["country"] = index
        elif any(
            token in lower
            for token in ("new date", "final action", "current", "this month", "new ")
        ) or (lower.startswith("new") and "old" not in lower):
            mapping["new_date"] = index
        elif any(
            token in lower
            for token in ("old date", "prior", "previous", "last month")
        ) or lower.startswith("old"):
            mapping["old_date"] = index
        elif any(token in lower for token in ("movement", "change", "shift")):
            mapping["movement"] = index
    return mapping


def _is_header_row(cells: list[str]) -> bool:
    if not cells:
        return True
    joined = " ".join(cells).lower()
    return "country" in joined and (
        "new" in joined or "final" in joined or "movement" in joined
    )


def _cells_from_row(tr) -> list[str]:
    cells = []
    for cell in tr.find_all(["td", "th"]) or []:
        if cell is None:
            continue
        cells.append(cell.get_text(separator=" ", strip=True) or "")
    return cells


def _row_values(cells: list[str], col_map: dict[str, int]) -> tuple[str, str, str, str]:
    def at(key: str, default_index: int) -> str:
        if key in col_map and col_map[key] < len(cells):
            return cells[col_map[key]]
        if default_index < len(cells):
            return cells[default_index]
        return ""

    return (
        at("country", 0),
        at("new_date", 1),
        at("old_date", 2),
        at("movement", 3),
    )


def _format_structured_row(
    category: str,
    country: str,
    new_date: str,
    old_date: str,
    movement: str,
) -> str:
    return (
        f"CATEGORY: {category} | COUNTRY: {country} | "
        f"FINAL ACTION DATE: {new_date} | PRIOR DATE: {old_date} | "
        f"MOVEMENT: {movement}"
    )


def _extract_table_rows(soup) -> list[str]:
    structured_rows = []
    for table in soup.find_all("table") or []:
        if table is None:
            continue

        category = _category_for_table(table)
        col_map: dict[str, int] = {}

        for tr in table.find_all("tr") or []:
            if tr is None:
                continue
            cells = _cells_from_row(tr)
            if not cells or not any(cell.strip() for cell in cells):
                continue

            if _is_header_row(cells):
                col_map = _column_map(cells)
                continue

            if not col_map and len(cells) >= 4:
                col_map = {
                    "country": 0,
                    "new_date": 1,
                    "old_date": 2,
                    "movement": 3,
                }

            country, new_date, old_date, movement = _row_values(cells, col_map)
            if not country.strip():
                continue
            if country.lower() in ("country", "chargeability"):
                continue

            structured_rows.append(
                _format_structured_row(
                    category,
                    country.strip(),
                    new_date.strip(),
                    old_date.strip(),
                    movement.strip(),
                )
            )

    return structured_rows


def _format_visa_bulletin_block(soup, rows: list[str]) -> str:
    period = _extract_bulletin_period(soup).upper()
    header = f"VISA BULLETIN PRIORITY DATE TABLE — {period}:\n"
    return header + "\n".join(rows)


def _normalize_generic_html(soup, source_url: str) -> dict:
    for tag_name in _TAGS_TO_REMOVE:
        for tag in soup.find_all(tag_name):
            if tag is not None:
                tag.decompose()

    title = ""
    if soup.title is not None and soup.title.string:
        title = soup.title.string.strip()

    body = soup.get_text(separator=" ", strip=True) or ""
    table_rows = _extract_table_rows(soup)
    if table_rows:
        body = body + "\n\n" + _format_visa_bulletin_block(soup, table_rows)

    return {
        "title": title,
        "body": body,
        "timestamp": _utcnow_isoformat(),
        "source_url": source_url,
    }


def _normalize_ilw_html(soup, source_url: str) -> dict:
    for tag_name in _TAGS_TO_REMOVE:
        for tag in soup.find_all(tag_name):
            if tag is not None:
                tag.decompose()

    _decompose_by_class_names(soup, _ILW_STRIP_CLASSES)

    extracted_items = []
    headings = soup.find_all(["h1", "h2", "h3", "h4"]) or []
    for heading in headings:
        if heading is None:
            continue
        headline = heading.get_text(separator=" ", strip=True) or ""
        if not headline or len(headline) < 10:
            continue

        lead = ""
        sibling = heading.find_next_sibling(["p", "div"])
        if sibling is not None:
            lead = sibling.get_text(separator=" ", strip=True) or ""
            if lead:
                lead = lead.split(". ")[0].strip()
                if len(lead) > 300:
                    lead = lead[:300].rstrip() + "..."

        if lead:
            item = f"{headline} — {lead}"
        else:
            item = headline

        if item and item.strip():
            extracted_items.append(item.strip())

        if len(extracted_items) >= 10:
            break

    extracted_items = [item for item in extracted_items if item]

    if extracted_items:
        body = "ILW Immigration News Headlines:\n" + "\n".join(extracted_items)
    else:
        body = (soup.get_text(separator=" ", strip=True) or "")[:3000]

    return {
        "title": "ILW Immigration News",
        "body": body or "",
        "timestamp": _utcnow_isoformat(),
        "source_url": source_url,
    }


def normalize_html_response(html: str, source_url: str) -> dict:
    try:
        soup = BeautifulSoup(html or "", "lxml")

        if "ilw.com" in source_url.lower():
            try:
                return _normalize_ilw_html(soup, source_url)
            except Exception:
                logger.exception("ILW HTML extraction failed; falling back to generic")
                return _normalize_generic_html(soup, source_url)

        return _normalize_generic_html(soup, source_url)
    except Exception:
        logger.exception("normalize_html_response failed for %s", source_url)
        return _safe_html_defaults(source_url)


def compute_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()
