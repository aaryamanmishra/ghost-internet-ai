import asyncio
import logging
import os
import re
from typing import List

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

    def _do_search() -> List[str]:
        found: List[str] = []
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

                    candidates = [
                        _normalize_org_name((org.get("login") or "").strip()),
                    ]
                    for name in candidates:
                        if not name or len(name) < 3:
                            continue
                        if name.lower() in _GENERIC_STOP:
                            continue
                        key = name.lower()
                        if key in seen:
                            continue
                        seen.add(key)
                        found.append(name)
                        break

                    if len(found) >= limit:
                        break
                if len(found) >= limit:
                    break
        except Exception as e:
            logger.warning(f"Company search failed: {e}")
            return []
        return found

    return await asyncio.to_thread(_do_search)
