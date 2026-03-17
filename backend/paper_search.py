import asyncio
import logging
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

OPENALEX_API_URL = "https://api.openalex.org/works"
DEFAULT_HEADERS = {
    "User-Agent": "GhostInternet/1.0 (+https://github.com/)"
}


async def search_papers(topic: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Paper search using OpenAlex.

    Returns a list of:
      { "title": str, "authors": str, "year": int|None, "url": str }
    """
    if not topic or not topic.strip():
        return []

    query = topic.strip()

    def _do_request() -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                OPENALEX_API_URL,
                params={
                    "search": query,
                    "per-page": max(1, min(int(limit), 10)),
                },
                headers=DEFAULT_HEADERS,
                timeout=12,
            )
            resp.raise_for_status()
            payload = resp.json() or {}
            out: List[Dict[str, Any]] = []
            for item in (payload.get("results") or [])[:limit]:
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
                out.append(
                    {
                        "title": title or "Untitled",
                        "authors": authors or "Unknown",
                        "year": year,
                        "url": url or "",
                    }
                )
            return out
        except Exception as e:
            logger.warning(f"OpenAlex search failed: {e}")
            return []

    return await asyncio.to_thread(_do_request)
