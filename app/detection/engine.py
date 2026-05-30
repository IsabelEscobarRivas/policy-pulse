import re
from typing import List, Set, Tuple

_NAVIGATION_PHRASES = [
    "click here",
    "read more",
    "back to top",
    "skip to",
    "menu",
    "search",
]


def _split_sentences(content: str) -> Set[str]:
    if not content:
        return set()
    return {sentence.strip() for sentence in content.split(". ") if sentence.strip()}


def compare_snapshots(previous_content: str, current_content: str) -> dict:
    previous_sentences = _split_sentences(previous_content)
    current_sentences = _split_sentences(current_content)

    added = list(current_sentences - previous_sentences)
    removed = list(previous_sentences - current_sentences)

    return {
        "added": added,
        "removed": removed,
        "change_detected": bool(added or removed),
    }


def _is_numbers_or_dates_only(sentence: str) -> bool:
    stripped = sentence.strip()
    if re.fullmatch(r"[\d\s\-/.,:]+", stripped):
        return True
    if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{2,4}", stripped):
        return True
    return False


def _is_irrelevant_sentence(sentence: str) -> bool:
    stripped = sentence.strip()
    if len(stripped) < 20:
        return True
    if _is_numbers_or_dates_only(stripped):
        return True
    lower = stripped.lower()
    return any(phrase in lower for phrase in _NAVIGATION_PHRASES)


def _filter_sentences(sentences: List[str]) -> List[str]:
    return [sentence for sentence in sentences if not _is_irrelevant_sentence(sentence)]


def _compute_relevance_score(added: List[str], removed: List[str]) -> float:
    total = len(added) + len(removed)
    if total == 0:
        return 0.0
    if total <= 2:
        return 0.3
    if total <= 5:
        return 0.7
    return 1.0


def filter_relevance(delta: dict) -> Tuple[dict, float]:
    added = _filter_sentences(delta.get("added", []))
    removed = _filter_sentences(delta.get("removed", []))

    filtered_delta = {
        "added": added,
        "removed": removed,
        "change_detected": bool(added or removed),
    }
    relevance_score = _compute_relevance_score(added, removed)

    return filtered_delta, relevance_score


def summarize_delta(delta: dict, source_name: str) -> str:
    added = delta.get("added", [])
    removed = delta.get("removed", [])

    sample_additions = []
    for sentence in added[:2]:
        truncated = sentence[:100]
        if len(sentence) > 100:
            truncated += "..."
        sample_additions.append(truncated)

    samples_text = "; ".join(sample_additions) if sample_additions else "none"

    return (
        f"Source: {source_name}\n"
        f"Added: {len(added)} new passages\n"
        f"Removed: {len(removed)} passages\n"
        f"Sample additions: {samples_text}"
    )
