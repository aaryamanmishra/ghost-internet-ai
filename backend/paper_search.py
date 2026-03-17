import asyncio
import logging
import re
from typing import Any, Dict, List, Tuple

import requests

logger = logging.getLogger(__name__)

OPENALEX_API_URL = "https://api.openalex.org/works"
DEFAULT_HEADERS = {
    "User-Agent": "GhostInternet/1.0 (+https://github.com/)"
}

_STOPWORDS = {
    "about",
    "abandoned",
    "and",
    "for",
    "forgotten",
    "idea",
    "ideas",
    "innovation",
    "innovations",
    "of",
    "overlooked",
    "related",
    "technologies",
    "technology",
    "the",
}
_NORMALIZED_STOPWORDS = set()


def _normalize_token(token: str) -> str:
    token = re.sub(r"[^a-z0-9]", "", token.lower())
    if token.endswith("ies") and len(token) > 4:
        token = token[:-3] + "y"
    for suffix in ("ation", "ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) > len(suffix) + 3:
            token = token[: -len(suffix)]
            break
    return token


for _word in _STOPWORDS:
    _NORMALIZED_STOPWORDS.add(_normalize_token(_word))


def _topic_terms(topic: str) -> List[str]:
    parts = re.split(r"[^a-zA-Z0-9]+", topic.lower())
    return [term for term in (_normalize_token(p) for p in parts) if len(term) > 3 and term not in _NORMALIZED_STOPWORDS]


def _paper_score(title: str, topic_terms: List[str], year: Any) -> Tuple[int, int]:
    title_terms = {_normalize_token(part) for part in re.split(r"[^a-zA-Z0-9]+", title.lower())}
    title_terms.discard("")

    match_score = 0
    for term in topic_terms:
        if term in title_terms:
            match_score += 4
            continue
        if any(t.startswith(term[:5]) or term.startswith(t[:5]) for t in title_terms if len(t) >= 5 and len(term) >= 5):
            match_score += 2

    try:
        year_num = int(year)
    except Exception:
        year_num = 0
    score = match_score
    if year_num >= 2018:
        score += 1
    return match_score, score


async def search_papers(topic: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Paper search using OpenAlex.

    Returns a list of:
      { "title": str, "authors": str, "year": int|None, "url": str }
    """
    if not topic or not topic.strip():
        return []

    query = topic.strip()
    topic_terms = _topic_terms(query)

    def _do_request() -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                OPENALEX_API_URL,
                params={
                    "search": query,
                    "per-page": max(10, min(int(limit) * 4, 25)),
                },
                headers=DEFAULT_HEADERS,
                timeout=12,
            )
            resp.raise_for_status()
            payload = resp.json() or {}
            ranked: List[Tuple[int, Dict[str, Any]]] = []
            for item in payload.get("results") or []:
                if not isinstance(item, dict):
                    continue
                title = (item.get("display_name") or item.get("title") or "").strip()
                year = item.get("publication_year", None)
                primary_location = item.get("primary_location") or {}
                best_oa_location = item.get("best_oa_location") or {}
                url = (
                    primary_location.get("landing_page_url")
                    or best_oa_location.get("landing_page_url")
                    or ""
                ).strip()
                authors_list = item.get("authorships") or []
                authors = ", ".join(
                    [
                        ((a.get("author") or {}).get("display_name") or "").strip()
                        for a in authors_list
                        if isinstance(a, dict) and ((a.get("author") or {}).get("display_name") or "").strip()
                    ]
                )
                if not title and not url:
                    continue
                paper = {
                    "title": title or "Untitled",
                    "authors": authors or "Unknown",
                    "year": year,
                    "url": url or "",
                }
                match_score, score = _paper_score(title, topic_terms, year)
                ranked.append((match_score, score, paper))

            if not ranked:
                return []

            ranked.sort(key=lambda item: (-item[1], -(item[2].get("year") or 0), item[2]["title"].lower()))
            filtered = [paper for match_score, _, paper in ranked if match_score > 0]
            chosen = filtered[:limit] if filtered else [paper for _, _, paper in ranked[:limit]]
            return chosen
        except Exception as e:
            logger.warning(f"OpenAlex search failed: {e}")
            return []

    return await asyncio.to_thread(_do_request)
