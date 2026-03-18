import asyncio
import logging
from typing import Any, Dict, List
from urllib.parse import quote_plus

logger = logging.getLogger(__name__)


async def search_patents(topic: str, limit: int = 3) -> List[Dict[str, Any]]:
    """
    Returns direct query URLs for Google Patents and WIPO PATENTSCOPE databases.
    """
    if not topic or not topic.strip():
        return []

    lim = max(1, min(int(limit), 5))
    encoded_topic = quote_plus(topic.strip())

    out: List[Dict[str, Any]] = [
        {
            "title": f"{topic} - Google Patents Search",
            "url": f"https://patents.google.com/?q={encoded_topic}"
        },
        {
            "title": f"{topic} - WIPO PATENTSCOPE Search",
            "url": f"https://patentscope.wipo.int/search/en/result.jsf?query={encoded_topic}"
        }
    ]
    
    return out[:lim]
