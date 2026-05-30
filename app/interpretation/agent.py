import json
import logging
import re
from typing import List, Tuple

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """
You are a regulatory intelligence analyst specializing in US immigration law.
You analyze detected changes in regulatory guidance and produce structured 
intelligence objects for attorney review.

You must:
- Identify which visa categories are affected
- Classify the type of change
- Summarize the change in plain language attorneys can act on
- Identify evidence implications for pending petitions
- Assign review priority based on urgency

You must NOT:
- Provide legal advice
- Make autonomous legal conclusions
- Fabricate regulatory content
- Override attorney judgment

Always respond with valid JSON only. No preamble, no explanation outside JSON.
"""

_SAFE_DEFAULT = {
    "visa_category": "Unknown",
    "change_type_label": "Unknown",
    "summary": "Interpretation unavailable.",
    "evidence_implications": [],
    "review_priority": "None",
}

_REQUIRED_KEYS = (
    "visa_category",
    "change_type_label",
    "summary",
    "evidence_implications",
    "review_priority",
)


def _no_change_result() -> dict:
    return {
        "visa_category": "N/A",
        "change_type_label": "No Change",
        "summary": "No meaningful regulatory change detected.",
        "evidence_implications": [],
        "review_priority": "None",
    }


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _normalize_interpretation(parsed: dict) -> dict:
    result = dict(_SAFE_DEFAULT)
    for key in _REQUIRED_KEYS:
        if key not in parsed:
            continue
        value = parsed[key]
        if key == "evidence_implications":
            result[key] = value if isinstance(value, list) else []
        elif value is not None:
            result[key] = value
    return result


def governance_check(interpretation: dict) -> bool:
    summary = (interpretation.get("summary") or "").lower()
    if any(
        phrase in summary
        for phrase in ("legal advice", "recommend", "guarantee")
    ):
        return True

    if (
        interpretation.get("review_priority") == "High"
        and interpretation.get("visa_category") == "Unknown"
    ):
        return True

    implications = interpretation.get("evidence_implications") or []
    if (
        interpretation.get("review_priority") == "High"
        and not implications
    ):
        return True

    return False


async def interpret_change(
    source_name: str,
    delta_summary: str,
    added_sentences: List[str],
    removed_sentences: List[str],
) -> Tuple[dict, str]:
    if not added_sentences and not removed_sentences:
        result = _no_change_result()
        return result, json.dumps(result)

    user_prompt = f"""
Analyze this regulatory change detected in: {source_name}

Added content:
{chr(10).join(added_sentences[:10])}

Removed content:
{chr(10).join(removed_sentences[:10])}

Delta summary: {delta_summary}

Respond with JSON only in this exact format:
{{
  "visa_category": "string (e.g. H-1B, O-1A, EB-2, All, Unknown)",
  "change_type_label": "string (e.g. Increased Evidentiary Scrutiny, Policy Clarification, Procedural Change, Fee Update, Unknown)",
  "summary": "string (2-3 sentences max, attorney-facing)",
  "evidence_implications": ["string", "string"],
  "review_priority": "High|Medium|Low|None"
}}
"""

    raw_response = ""

    try:
        settings = get_settings()
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 500,
                    "system": SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            response_json = response.json()
            raw_response = response_json["content"][0]["text"]
            parsed = json.loads(_strip_json_fences(raw_response))
            return _normalize_interpretation(parsed), raw_response
    except Exception as e:
        logger.error("Interpretation failed: %s", e)
        return dict(_SAFE_DEFAULT), raw_response
