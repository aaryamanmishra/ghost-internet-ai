import asyncio
import logging
import os
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

PATENTSEARCH_API_URL = "https://search.patentsview.org/api/v1/patent/"


async def search_patents(topic: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Patent discovery using the current PatentsView PatentSearch API.

    Returns:
      { "title": str, "url": str }

    Notes:
    - Requires `PATENTSVIEW_API_KEY`.
    - Returns [] on any error so the endpoint stays available.
    """
    if not topic or not topic.strip():
        return []

    api_key = os.getenv("PATENTSVIEW_API_KEY")
    if not api_key:
        logger.warning("Patent search skipped: PATENTSVIEW_API_KEY is not configured.")
        return []

    lim = max(1, min(int(limit), 5))

    def _do_search() -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        try:
            params = {
                "q": '{"_text_any":{"patent_title":"' + topic.strip().replace('"', '\\"') + '"}}',
                "f": '["patent_id","patent_title"]',
                "o": '{"size":' + str(lim) + '}',
                "s": '[{"patent_date":"desc"}]',
            }
            resp = requests.get(
                PATENTSEARCH_API_URL,
                params=params,
                headers={"X-Api-Key": api_key, "User-Agent": "GhostInternet/1.0 (+https://github.com/)"},
                timeout=12,
            )
            resp.raise_for_status()
            payload = resp.json() or {}
            for patent in payload.get("patents") or []:
                if not isinstance(patent, dict):
                    continue
                patent_id = (patent.get("patent_id") or "").strip()
                title = (patent.get("patent_title") or "").strip()
                if not patent_id and not title:
                    continue
                url = f"https://patents.google.com/patent/US{patent_id}" if patent_id else ""
                out.append({"title": title or "Patent result", "url": url})
                if len(out) >= lim:
                    break
        except Exception as e:
            logger.warning(f"Patent search failed: {e}")
            return []
        return out

    return await asyncio.to_thread(_do_search)
