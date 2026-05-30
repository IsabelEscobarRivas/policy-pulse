import json
import logging
import re
from datetime import datetime
from typing import List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

BRIEF_SYSTEM_PROMPT = """
You are a senior regulatory intelligence analyst specializing in US immigration law.
You synthesize the latest public regulatory content into concise attorney-facing briefs.

Your brief must:
- Summarize the current regulatory climate in plain language
- Identify active topics by visa category
- Highlight any procedural or evidentiary shifts
- List concrete attorney action items
- Be factual and grounded only in the provided content

You must NOT:
- Provide legal advice
- Make autonomous legal conclusions
- Fabricate regulatory content not present in the source material
- Use speculative language

Always respond with valid JSON only. No preamble, no explanation outside JSON.
"""

_BRIEF_SAFE_DEFAULT = {
    "climate": "Regulatory brief unavailable due to a processing error.",
    "active_topics": [],
    "federal_register_summary": "Unable to summarize Federal Register activity.",
    "visa_bulletin_status": "Unable to summarize visa bulletin status.",
    "attorney_action_items": [],
    "generated_at": "",
    "source_count": 0,
}


def _empty_brief() -> dict:
    return {
        "climate": "No regulatory content available yet. Run a retrieval first.",
        "active_topics": [],
        "federal_register_summary": "No recent Federal Register activity retrieved.",
        "visa_bulletin_status": "Visa bulletin not yet retrieved.",
        "attorney_action_items": [],
        "generated_at": datetime.utcnow().isoformat(),
        "source_count": 0,
    }


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _normalize_brief(parsed: dict, source_count: int) -> dict:
    result = dict(_BRIEF_SAFE_DEFAULT)
    result.update(parsed)
    result["generated_at"] = result.get("generated_at") or datetime.utcnow().isoformat()
    result["source_count"] = result.get("source_count", source_count)
    if not isinstance(result.get("active_topics"), list):
        result["active_topics"] = []
    if not isinstance(result.get("attorney_action_items"), list):
        result["attorney_action_items"] = []
    return result


def _profile_is_empty(attorney_profile: Optional[dict]) -> bool:
    if not attorney_profile:
        return True
    return not (
        attorney_profile.get("practice_areas")
        or attorney_profile.get("client_nationalities")
        or attorney_profile.get("active_concern")
    )


def _build_profile_prompt(attorney_profile: dict) -> str:
    return f"""
ATTORNEY PROFILE:
Primary visa type filter: {", ".join(attorney_profile.get("practice_areas", ["All"]))}
Client nationalities: {", ".join(attorney_profile.get("client_nationalities", ["All"]))}
Active concern: {attorney_profile.get("active_concern", "None specified")}

STRICT FILTERING RULES:
- ONLY surface intelligence directly relevant to the specified visa type(s)
- If visa type is H-1B: focus ONLY on H-1B cap, RFE trends, specialty occupation
  standards, employer compliance, wage levels, LCA requirements, H-1B to green
  card transition timing
- If visa type is O-1: focus ONLY on extraordinary ability standards, evidentiary
  criteria, RFE patterns, peer review requirements
- If visa type is EB-1: focus ONLY on priority date movement, evidentiary
  standards, retrogression impact, adjustment of status timing
- If visa type is EB-2: focus ONLY on priority date movement, NIW criteria,
  India/China retrogression, PERM labor certification
- If visa type is EB-3: focus ONLY on priority date movement, PERM,
  skilled worker criteria
- If visa type is Family-based: focus ONLY on family preference categories,
  priority date movement, NVC processing
- If visa type is K-1: focus ONLY on K-1 processing times, interview waits,
  country-specific delays
- Do NOT include information about other visa categories not selected
- Do NOT include EB green card backlog data when attorney has filtered for H-1B
- active_topics must ONLY contain topics relevant to the filtered visa type
- If no specific intelligence exists for the filtered visa type in the source
  material, explicitly state that in the climate field and return empty
  active_topics rather than substituting other categories

"""


async def generate_brief(
    documents: List[dict], attorney_profile: Optional[dict] = None
) -> dict:
    if not documents:
        return _empty_brief()

    content_summary = ""
    for document in documents[:5]:
        title = document.get("title") or "Untitled"
        content = document.get("content") or ""
        content_summary += f"SOURCE: {title}\nCONTENT: {content[:2000]}\n\n"

    generated_at = datetime.utcnow().isoformat()
    profile_section = ""
    if not _profile_is_empty(attorney_profile):
        profile_section = _build_profile_prompt(attorney_profile)

    user_prompt = f"""
{profile_section}Analyze the following regulatory content retrieved from public immigration sources.
Generate a current regulatory intelligence brief for immigration attorneys.

Content retrieved at: {generated_at}
Number of sources: {len(documents)}

{content_summary}

When legal commentary or attorney analysis is present in the source
content (look for ILW Immigration News Headlines), use it to:
- Provide legal context for regulatory changes
- Reference attorney perspectives on policy implications
- Add substantive legal analysis beyond raw regulatory data
- Strengthen the 'What This Means' intelligence in active_topics
Ground all analysis in the provided source content only.

Respond with JSON only in this exact format:
{{
  "climate": "string (2-3 sentences on overall regulatory posture)",
  "active_topics": [
    {{
      "visa_category": "string",
      "topic": "string",
      "urgency": "High|Medium|Low"
    }}
  ],
  "federal_register_summary": "string (1-2 sentences on recent FR activity)",
  "visa_bulletin_status": "string (1-2 sentences on current visa bulletin)",
  "attorney_action_items": ["string", "string", "string"],
  "generated_at": "{generated_at}",
  "source_count": {len(documents)}
}}
"""

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
                    "max_tokens": 1000,
                    "system": BRIEF_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            response_json = response.json()
            raw_text = response_json["content"][0]["text"]
            parsed = json.loads(_strip_json_fences(raw_text))
            return _normalize_brief(parsed, len(documents))
    except Exception as e:
        logger.error("Brief generation failed: %s", e)
        fallback = dict(_BRIEF_SAFE_DEFAULT)
        fallback["generated_at"] = datetime.utcnow().isoformat()
        fallback["source_count"] = len(documents)
        return fallback
