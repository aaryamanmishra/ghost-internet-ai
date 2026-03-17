import asyncio
import logging
from typing import Any, Dict, List

from duckduckgo_search import DDGS
logger = logging.getLogger(__name__)


def _build_queries(topic: str) -> List[str]:
    cleaned = " ".join((topic or "").split())
    words = [w for w in cleaned.split() if len(w) > 3]
    queries = [
        f'site:patents.google.com/patent "{cleaned}"',
        f'site:patents.google.com/patent {cleaned} patent',
    ]
    if words:
        queries.append(f'site:patents.google.com/patent {" ".join(words[:3])} patent')
        queries.append(f'site:patents.google.com/patent {words[0]} patent')
    return queries


async def search_patents(topic: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Temporary free patent discovery using web results that point to Google Patents.

    Returns:
      { "title": str, "url": str }

    Notes:
    - No API key required.
    - Best-effort only; search engines may throttle or return sparse results.
    - Returns [] on any error so the endpoint stays available.
    """
    if not topic or not topic.strip():
        return []

    lim = max(1, min(int(limit), 5))
    queries = _build_queries(topic)

    def _do_search() -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            seen = set()
            with DDGS() as ddgs:
                for query in queries:
                    for item in ddgs.text(query, max_results=max(lim * 4, 10)):
                        if not isinstance(item, dict):
                            continue
                        url = (item.get("href") or item.get("url") or "").strip()
                        title = (item.get("title") or "").strip()
                        if not url or "patents.google.com/patent/" not in url:
                            continue
                        if url in seen:
                            continue
                        seen.add(url)
                        out.append({"title": title or "Patent result", "url": url})
                        if len(out) >= lim:
                            return out
        except Exception as e:
            logger.warning(f"Patent search failed: {e}")
            return []
        return out

    return await asyncio.to_thread(_do_search)
