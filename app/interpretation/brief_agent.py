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


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


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

"""


def _safe_default(source_count: int) -> dict:
    return {
        "climate": "Regulatory brief unavailable due to a processing error.",
        "federal_register_summary": "Unable to summarize Federal Register activity.",
        "visa_bulletin_status": "Unable to summarize visa bulletin status.",
        "attorney_action_items": [],
        "generated_at": datetime.utcnow().isoformat(),
        "source_count": source_count,
    }


async def generate_brief(
    documents: List[dict], attorney_profile: Optional[dict] = None
) -> dict:
    if not documents:
        return {
            "climate": "No regulatory content available yet. Run a retrieval first.",
            "federal_register_summary": "No recent Federal Register activity retrieved.",
            "visa_bulletin_status": "Visa bulletin not yet retrieved.",
            "attorney_action_items": [],
            "generated_at": datetime.utcnow().isoformat(),
            "source_count": 0,
        }

    try:
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

VERIFIED JUNE 2026 CUTOFF DATES:
EB-1 India: December 15, 2022 (retrogressed 3.5 months)
EB-2 India: September 1, 2013 (retrogressed 10.5 months)
EB-3 India: December 15, 2013 (advanced 1 month)
EB-3 China: August 1, 2021 (advanced 1.5 months)
All Other EB-1/EB-2: Current
Employment-based June 2026: Final Action Dates govern AOS
Family-based June 2026: Dates for Filing govern AOS

Use these exact dates in climate, visa_bulletin_status, and summaries when relevant.

{content_summary}

Respond with JSON only in this exact format:
{{
  "climate": "2-3 sentence summary string",
  "federal_register_summary": "1-2 sentence string",
  "visa_bulletin_status": "2-3 sentence string",
  "attorney_action_items": ["string", "string", "string"],
  "generated_at": "{generated_at}",
  "source_count": {len(documents)}
}}
"""

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
                    "max_tokens": 600,
                    "system": BRIEF_SYSTEM_PROMPT,
                    "messages": [{"role": "user", "content": user_prompt}],
                },
                timeout=60.0,
            )
            response.raise_for_status()
            response_json = response.json()
            raw_text = response_json["content"][0]["text"]
            parsed = json.loads(_strip_json_fences(raw_text))

        brief = {
            "climate": parsed.get("climate", ""),
            "federal_register_summary": parsed.get("federal_register_summary", ""),
            "visa_bulletin_status": parsed.get("visa_bulletin_status", ""),
            "attorney_action_items": parsed.get("attorney_action_items", []),
            "generated_at": parsed.get("generated_at") or generated_at,
            "source_count": parsed.get("source_count", len(documents)),
        }
        if not isinstance(brief["attorney_action_items"], list):
            brief["attorney_action_items"] = []
        return brief
    except Exception as e:
        logger.error("Brief generation failed: %s", e)
        return _safe_default(len(documents))
