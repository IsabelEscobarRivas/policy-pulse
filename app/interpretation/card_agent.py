import asyncio
import logging

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

CARD_SYSTEM_PROMPT = """
You are a regulatory intelligence analyst specializing in US immigration law.
Answer questions about visa bulletin data precisely and concisely.
Base answers only on the provided context.
Never provide legal advice.
Always include specific dates and numbers when available.
Answer in 1-2 sentences maximum. Never exceed 50 words.
CRITICAL: Answer ONLY about the nationality specified in the question.
Do not mention or compare to other nationalities.
If the question is about China, answer ONLY about China.
If the question is about India, answer ONLY about India.
Never volunteer information about other countries.
"""

JUNE_2026_CONTEXT = """
June 2026 Visa Bulletin Key Facts:
- EB-1 India: retrogressed to December 15, 2022 (3.5 months backward)
- EB-1 China: current (no change)
- EB-1 All Other: current (no change)
- EB-2 India: retrogressed to September 1, 2013 (10.5 months backward)
- EB-2 China: unchanged at September 1, 2021
- EB-2 All Other: current (no change)
- EB-3 India: advanced to December 15, 2013 (1 month forward)
- EB-3 China: advanced to August 1, 2021 (1.5 months forward)
- EB-3 All Other: unchanged at June 1, 2024
- F-2B All: advanced to March 22, 2018 (2.5 months forward)
- F-4 All: advanced to December 22, 2009 (3.5 months forward)
- Employment-based June 2026: Final Action Dates govern AOS filings
- Family-based June 2026: Dates for Filing govern AOS filings
Source: U.S. Department of State Visa Bulletin June 2026
"""


async def ask_card_agent(question: str) -> str:
    try:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": settings.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 150,
                    "system": CARD_SYSTEM_PROMPT,
                    "messages": [
                        {
                            "role": "user",
                            "content": (
                                f"Context:\n{JUNE_2026_CONTEXT}\n\n"
                                f"Focus ONLY on: {question}\n\n"
                                "Important: Answer ONLY about the specific visa type and "
                                "nationality in the question. Do not compare to or mention "
                                "other nationalities unless explicitly asked."
                            ),
                        }
                    ],
                },
            )
            response.raise_for_status()
            return response.json()["content"][0]["text"].strip()
    except Exception as e:
        logger.error(f"Card agent failed: {e}")
        return "Data unavailable — verify directly at travel.state.gov"


async def generate_cards(
    visa_type: str = "All",
    nationality: str = "All",
) -> list:
    q1 = (
        f"For {visa_type} applicants from {nationality} ONLY: What is the current "
        "priority date situation in June 2026? Do NOT mention any other nationality. "
        "Include specific cutoff date and movement if applicable."
    )

    q2 = (
        f"For {visa_type} applicants in June 2026: Which filing methodology chart "
        "applies to adjustment of status? One sentence only."
    )

    q3 = (
        f"For {visa_type} applicants from {nationality} ONLY: In one sentence, what "
        "is the most important action for their attorney this month? Do NOT mention "
        "other nationalities."
    )

    results = await asyncio.gather(
        ask_card_agent(q1),
        ask_card_agent(q2),
        ask_card_agent(q3),
    )

    text1, text2, text3 = results

    has_retrogression = any(
        word in text1.lower()
        for word in ["retrogress", "backward", "moved back", "back to"]
    )

    is_current = any(
        word in text1.lower()
        for word in [
            "remains current",
            "remain current",
            "no retrogression",
            "no change",
            "current with",
        ]
    )

    card1_urgency = (
        "Low" if is_current else ("High" if has_retrogression else "Medium")
    )
    card3_urgency = "High" if has_retrogression else "Medium"

    cards = [
        {
            "visa_category": f"{visa_type} {nationality} — Priority Date".strip(),
            "topic": text1,
            "urgency": card1_urgency,
        },
        {
            "visa_category": f"{visa_type} — Filing Method",
            "topic": text2,
            "urgency": "Medium",
        },
        {
            "visa_category": f"{visa_type} {nationality} — Action Required".strip(),
            "topic": text3,
            "urgency": card3_urgency,
        },
    ]

    return cards
