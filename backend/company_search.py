import asyncio
import logging
import os
import re
from typing import Dict, List, Tuple

import requests

logger = logging.getLogger(__name__)

GITHUB_ORG_SEARCH_API_URL = "https://api.github.com/search/users"
DEFAULT_HEADERS = {
    "User-Agent": "GhostInternet/1.0 (+https://github.com/)"
}

_GENERIC_STOP = {
    "home",
    "about",
    "blog",
    "news",
    "careers",
    "pricing",
    "contact",
    "login",
    "sign in",
    "sign up",
}


_GENERIC_ORG_WORDS = {
    "official",
    "opensource",
    "open-source",
    "community",
    "org",
    "organization",
    "tech",
    "technology",
    "technologies",
    "group",
    "labs",
    "lab",
    "systems",
    "solutions",
}


def _build_company_queries(topic: str) -> List[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", topic or "")
    words = [w for w in cleaned.split() if len(w) > 3]
    queries = [f"{topic.strip()} type:org"]
    if words:
        queries.append(f"{' '.join(words[:3])} type:org")
        queries.append(f"{words[0]} technology type:org")
    return queries


def _extract_company_name_from_title(title: str) -> str:
    # Common separators in search result titles
    for sep in [" - ", " | ", " — ", " – "]:
        if sep in title:
            title = title.split(sep)[0]
            break
    name = re.sub(r"\s+", " ", title).strip()
    # Remove trailing generic words
    name = re.sub(r"\b(Inc\.?|LLC|Ltd\.?|Company|Co\.?)\b", "", name, flags=re.IGNORECASE).strip()
    return name


def _normalize_org_name(raw_name: str) -> str:
    name = re.sub(r"[-_]+", " ", raw_name or "").strip()
    name = re.sub(r"\s+", " ", name).strip()
    return name


def _topic_terms(topic: str) -> List[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", topic.lower())
    return [w for w in cleaned.split() if len(w) > 3]


def _score_org(org: Dict[str, object], topic_terms: List[str]) -> Tuple[int, str]:
    login = _normalize_org_name(str(org.get("login") or ""))
    display_name = _normalize_org_name(str(org.get("name") or login))
    bio = str(org.get("description") or "").lower()
    blog = str(org.get("blog") or "").strip()
    location = str(org.get("location") or "").strip()

    haystacks = " ".join([login.lower(), display_name.lower(), bio])
    score = 0

    for term in topic_terms:
        if term in haystacks:
            score += 3

    login_words = {w for w in login.lower().split() if w}
    display_words = {w for w in display_name.lower().split() if w}
    generic_penalty = len((login_words | display_words) & _GENERIC_ORG_WORDS)
    score -= generic_penalty

    if blog:
        score += 2
    if location:
        score += 1
    if bio:
        score += 2

    followers = int(org.get("followers") or 0)
    public_repos = int(org.get("public_repos") or 0)
    if followers >= 20:
        score += 1
    if public_repos >= 3:
        score += 1

    chosen_name = display_name or login
    return score, chosen_name


def _fallback_names_from_topic(topic: str, limit: int) -> List[str]:
    cleaned = re.sub(r"[^a-zA-Z0-9\s-]", " ", topic or "")
    words = [w.capitalize() for w in cleaned.split() if len(w) > 3]
    if not words:
        return []
    suggestions = []
    suggestions.append(" ".join(words[:2]))
    if len(words) >= 3:
        suggestions.append(" ".join(words[:3]))
    suggestions.append(f"{words[0]} Labs")
    out: List[str] = []
    seen = set()
    for name in suggestions:
        normalized = name.strip()
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(normalized)
        if len(out) >= limit:
            break
    return out


async def search_companies(topic: str, limit: int = 5) -> List[str]:
    """
    Best-effort company/startup detection using GitHub organization search.

    Returns a list of company name strings. Returns [] on any error.
    """
    if not topic or not topic.strip():
        return []

    lim = max(1, min(int(limit), 10))
    token = os.getenv("GITHUB_TOKEN")
    queries = _build_company_queries(topic)
    topic_terms = _topic_terms(topic)

    def _do_search() -> List[str]:
        candidates: List[Tuple[int, str]] = []
        seen = set()
        try:
            headers = dict(DEFAULT_HEADERS)
            if token:
                headers["Authorization"] = f"Bearer {token}"
            for query in queries:
                resp = requests.get(
                    GITHUB_ORG_SEARCH_API_URL,
                    params={
                        "q": query,
                        "per_page": max(lim, 5),
                    },
                    headers=headers,
                    timeout=12,
                )
                resp.raise_for_status()
                payload = resp.json() or {}

                for org in payload.get("items") or []:
                    if not isinstance(org, dict):
                        continue
                    org_type = (org.get("type") or "").strip().lower()
                    if org_type != "organization":
                        continue
                    detail_url = str(org.get("url") or "").strip()
                    details = org
                    if detail_url:
                        try:
                            detail_resp = requests.get(detail_url, headers=headers, timeout=12)
                            detail_resp.raise_for_status()
                            detail_payload = detail_resp.json()
                            if isinstance(detail_payload, dict):
                                details = detail_payload
                        except Exception:
                            details = org

                    score, name = _score_org(details, topic_terms)
                    if not name or len(name) < 3:
                        continue
                    if name.lower() in _GENERIC_STOP:
                        continue
                    if score < 3:
                        continue
                    key = name.lower()
                    if key in seen:
                        continue
                    seen.add(key)
                    candidates.append((score, name))
        except Exception as e:
            logger.warning(f"Company search failed: {e}")
            if "rate limit" in str(e).lower():
                return _fallback_names_from_topic(topic, lim)
            return []
        candidates.sort(key=lambda item: (-item[0], item[1].lower()))
        return [name for _, name in candidates[:limit]]

    return await asyncio.to_thread(_do_search)
