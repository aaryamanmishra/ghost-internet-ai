import os
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from duckduckgo_search import DDGS
from bs4 import BeautifulSoup
import requests
import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import asyncio
import sqlite3
from datetime import datetime, timezone
from dotenv import load_dotenv

from backend.paper_search import search_papers
from backend.patent_search import search_patents
from backend.company_search import search_companies

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="Ghost Internet - AI Future Lab")

# Add CORS Middleware to allow the frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def _env_first(*names: str) -> Optional[str]:
    for name in names:
        value = os.getenv(name)
        if value and value.strip():
            return value.strip()
    return None


# Current DigitalOcean serverless inference config
GRADIENT_MODEL_ACCESS_KEY = _env_first("GRADIENT_MODEL_ACCESS_KEY", "GRADIENT_ACCESS_TOKEN")
GRADIENT_WORKSPACE_ID = _env_first("GRADIENT_WORKSPACE_ID", "DigitalOcean Managed")
GRADIENT_BASE_URL = _env_first("GRADIENT_BASE_URL") or "https://inference.do-ai.run/v1"

# Gradient configuration
# Prefer the documented current env names, but preserve compatibility with older local setup.
GRADIENT_ACCESS_TOKEN = _env_first("GRADIENT_ACCESS_TOKEN", "pdjVWLm4wSD_yHRZl-wGA9dNi5AEbF0_")
GRADIENT_BASE_MODEL_SLUG = _env_first("GRADIENT_BASE_MODEL_SLUG") or "llama3-8b-instruct"

class DiscoverRequest(BaseModel):
    topic: str


class SaveRequest(BaseModel):
    topic: str
    analysis: Dict[str, Any]

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

DB_PATH = os.path.join(os.path.dirname(__file__), "ghost_internet.db")


def _init_db() -> None:
    """
    Initializes SQLite tables if they don't exist.
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS saved_ideas (
              id INTEGER PRIMARY KEY AUTOINCREMENT,
              topic TEXT NOT NULL,
              analysis TEXT NOT NULL,
              timestamp TEXT NOT NULL
            )
            """
        )
        conn.commit()
        conn.close()
    except Exception as e:
        # Never crash the server for local persistence issues
        logger.warning(f"Failed to initialize DB: {e}")


@app.on_event("startup")
def _startup() -> None:
    _init_db()


def _safe_get_json(url: str, params: Dict[str, Any], timeout_s: int = 12) -> Optional[Dict[str, Any]]:
    try:
        resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=timeout_s)
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        logger.warning(f"GET JSON failed: {url} params={params} err={e}")
        return None


def _safe_get_text(url: str, params: Dict[str, Any], timeout_s: int = 12) -> Optional[str]:
    try:
        resp = requests.get(url, params=params, headers=DEFAULT_HEADERS, timeout=timeout_s)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        logger.warning(f"GET text failed: {url} params={params} err={e}")
        return None


def wikipedia_sources_and_context(topic: str, max_results: int = 3) -> Tuple[List[str], str]:
    """
    Free, stable source provider.
    Uses Wikipedia search + extract (no scraping required) and returns:
      - sources: page URLs
      - context: concatenated extracts
    """
    api = "https://en.wikipedia.org/w/api.php"
    data = _safe_get_json(
        api,
        params={
            "action": "query",
            "list": "search",
            "srsearch": topic,
            "utf8": 1,
            "format": "json",
            "srlimit": max_results,
        },
    )
    if not data:
        return ([], "")

    titles: List[str] = []
    for item in (data.get("query", {}) or {}).get("search", []) or []:
        title = (item.get("title") or "").strip()
        if title:
            titles.append(title)

    if not titles:
        return ([], "")

    extracts_data = _safe_get_json(
        api,
        params={
            "action": "query",
            "prop": "extracts|info",
            "explaintext": 1,
            "exintro": 0,
            "inprop": "url",
            "titles": "|".join(titles),
            "utf8": 1,
            "format": "json",
        },
    )
    if not extracts_data:
        return ([], "")

    pages = ((extracts_data.get("query") or {}).get("pages") or {}) if isinstance(extracts_data, dict) else {}
    sources: List[str] = []
    chunks: List[str] = []
    for _, page in pages.items():
        if not isinstance(page, dict):
            continue
        fullurl = (page.get("fullurl") or "").strip()
        title = (page.get("title") or "").strip()
        extract = (page.get("extract") or "").strip()
        if fullurl:
            sources.append(fullurl)
        if extract:
            label = title or "Wikipedia"
            chunks.append(f"[WIKIPEDIA: {label}]\n{extract}\n")

    return (sources[:max_results], "\n".join(chunks).strip())


def internet_archive_sources_and_context(topic: str, max_results: int = 3) -> Tuple[List[str], str]:
    """
    Free metadata search (no key required). Great for "forgotten" documents.
    We include item metadata as context since full text extraction varies by item type.
    """
    api = "https://archive.org/advancedsearch.php"
    text = _safe_get_text(
        api,
        params={
            "q": topic,
            "fl[]": ["identifier", "title", "year", "creator", "mediatype"],
            "sort[]": "year asc",
            "rows": max_results,
            "page": 1,
            "output": "json",
        },
        timeout_s=15,
    )
    if not text:
        return ([], "")
    try:
        data = json.loads(text)
    except Exception:
        return ([], "")

    docs = (((data.get("response") or {}).get("docs")) or []) if isinstance(data, dict) else []
    sources: List[str] = []
    chunks: List[str] = []
    for d in docs:
        if not isinstance(d, dict):
            continue
        ident = (d.get("identifier") or "").strip()
        if not ident:
            continue
        url = f"https://archive.org/details/{ident}"
        sources.append(url)
        title = (d.get("title") or "").strip()
        year = (d.get("year") or "")
        creator = (d.get("creator") or "")
        mediatype = (d.get("mediatype") or "")
        chunks.append(
            "[INTERNET_ARCHIVE_ITEM]\n"
            f"Title: {title}\n"
            f"Year: {year}\n"
            f"Creator: {creator}\n"
            f"MediaType: {mediatype}\n"
            f"URL: {url}\n"
        )

    return (sources[:max_results], "\n".join(chunks).strip())


def github_sources_and_context(topic: str, max_results: int = 3) -> Tuple[List[str], str]:
    """
    Free source provider. Works without auth but rate-limited.
    Uses GitHub Search API for repos (and includes descriptions as context).
    """
    api = "https://api.github.com/search/repositories"
    token = os.getenv("GITHUB_TOKEN")
    headers = dict(DEFAULT_HEADERS)
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(
            api,
            params={"q": topic, "sort": "stars", "order": "desc", "per_page": max_results},
            headers=headers,
            timeout=12,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.warning(f"GitHub search failed: {e}")
        return ([], "")

    items = data.get("items") or []
    sources: List[str] = []
    chunks: List[str] = []
    for r in items:
        if not isinstance(r, dict):
            continue
        html_url = (r.get("html_url") or "").strip()
        full_name = (r.get("full_name") or "").strip()
        desc = (r.get("description") or "").strip()
        topics = r.get("topics") or []
        if html_url:
            sources.append(html_url)
        chunks.append(
            "[GITHUB_REPOSITORY]\n"
            f"Repo: {full_name}\n"
            f"Description: {desc}\n"
            f"Topics: {topics}\n"
            f"URL: {html_url}\n"
        )

    return (sources[:max_results], "\n".join(chunks).strip())


def ddg_fallback_urls(query: str, max_results: int = 3) -> List[str]:
    """
    Legacy fallback: may return 0 if DDG blocks automated traffic.
    Kept to avoid removing existing working functionality.
    """
    search_query = f"{query} history origin forgotten ideas"
    results: List[str] = []

    # Strategy 1: duckduckgo_search library
    try:
        with DDGS() as ddgs:
            for r in ddgs.text(search_query, max_results=max_results):
                href = (r.get("href") or r.get("url") or "").strip()
                if href:
                    results.append(href)
                if len(results) >= max_results:
                    break
        if results:
            return results[:max_results]
    except Exception as e:
        logger.warning(f"DDGS search failed: {e}")

    # Strategy 2: scrape DuckDuckGo HTML results
    try:
        resp = requests.post(
            "https://html.duckduckgo.com/html/",
            headers=DEFAULT_HEADERS,
            data={"q": search_query},
            timeout=10,
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.content, "html.parser")
        for a in soup.find_all("a", class_="result__a"):
            href = (a.get("href") or "").strip()
            if href:
                results.append(href)
            if len(results) >= max_results:
                break
    except Exception as e:
        logger.warning(f"DDG HTML fallback failed: {e}")

    return results[:max_results]


def collect_free_sources_and_context(topic: str, max_sources: int = 6) -> Tuple[List[str], str]:
    """
    Free "Option A" source collector:
      - Wikipedia extracts (text)
      - Internet Archive metadata (text)
      - GitHub repo metadata (text)

    Returns (sources, context_text). Never raises.
    """
    sources: List[str] = []
    chunks: List[str] = []

    # Wikipedia (best for stable extracts)
    w_sources, w_ctx = wikipedia_sources_and_context(topic, max_results=3)
    sources.extend(w_sources)
    if w_ctx:
        chunks.append(w_ctx)

    # Internet Archive (good for historical artifacts)
    a_sources, a_ctx = internet_archive_sources_and_context(topic, max_results=2)
    sources.extend(a_sources)
    if a_ctx:
        chunks.append(a_ctx)

    # GitHub (engineering context)
    g_sources, g_ctx = github_sources_and_context(topic, max_results=2)
    sources.extend(g_sources)
    if g_ctx:
        chunks.append(g_ctx)

    # Deduplicate while preserving order
    seen = set()
    deduped: List[str] = []
    for s in sources:
        if s in seen:
            continue
        seen.add(s)
        deduped.append(s)

    return (deduped[:max_sources], "\n\n".join([c for c in chunks if c]).strip())


def _build_discover_issues(
    *,
    sources: List[str],
    context_text: str,
    analysis_meta: Dict[str, Any],
    research_papers: List[Dict[str, Any]],
    related_patents: List[Dict[str, Any]],
    related_companies: List[str],
) -> List[str]:
    issues: List[str] = []

    if not sources:
        issues.append("No source URLs were collected from the upstream providers.")
    if len(context_text.strip()) < 100:
        issues.append("Context gathering returned very little text, so the analysis quality may be weak.")
    if analysis_meta.get("used_fallback"):
        issues.append(f"AI analysis used the built-in fallback response: {analysis_meta.get('reason')}.")
    if not research_papers:
        issues.append("Research paper enrichment returned no results.")
    if not related_patents:
        issues.append("Patent enrichment returned no results.")
    if not related_companies:
        issues.append("Company/startup enrichment returned no results.")

    return issues

def scrape_text(url: str, max_length: int = 2000) -> str:
    """Extracts text content cleanly with timeout protection."""
    try:
        resp = requests.get(url, headers=DEFAULT_HEADERS, timeout=5)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")
        
        # Remove scripts and styles
        for ele in soup(["script", "style", "nav", "footer", "header"]):
            ele.extract()
            
        # Extract readable text using soup.get_text()
        text = soup.get_text(separator=' ', strip=True)
        return text[:max_length]
    except Exception as e:
        logger.error(f"Skipping {url} due to scraping failure: {e}")
        return ""

def _extract_json_object(text: str) -> Optional[str]:
    """
    Best-effort extraction of a JSON object from model output.
    Some models sometimes wrap JSON in markdown fences or add a preamble.
    """
    if not text:
        return None

    cleaned = text.strip()
    cleaned = cleaned.replace("```json", "").replace("```", "").strip()

    # Try direct parse first.
    try:
        json.loads(cleaned)
        return cleaned
    except Exception:
        pass

    # Best-effort: locate the first {...} span.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = cleaned[start : end + 1].strip()
    try:
        json.loads(candidate)
        return candidate
    except Exception:
        return None


def _clamp_int(value: Any, min_v: int, max_v: int, default: int) -> int:
    try:
        v = int(round(float(value)))
        return max(min_v, min(max_v, v))
    except Exception:
        return default


def _ensure_str_list(value: Any, fallback: List[str]) -> List[str]:
    if isinstance(value, list):
        out: List[str] = []
        for item in value:
            if item is None:
                continue
            s = str(item).strip()
            if s:
                out.append(s)
        return out if out else fallback
    return fallback


def _normalize_future_lab_output(raw: Dict[str, Any], topic: str) -> Dict[str, Any]:
    """
    Normalizes model output to the API contract:
      - Top-level: analysis, sources, innovation_tree, revival_probability, timeline
      - analysis contains the expert panel sections + key_breakthrough_needed + scores
    Also keeps the prior flat keys for backward compatibility.
    """
    idea = (raw.get("idea") or "").strip() or f"Forgotten idea related to {topic}"
    historian = (raw.get("historian_analysis") or "").strip()
    engineer = (raw.get("engineer_analysis") or "").strip()
    futurist = (raw.get("futurist_analysis") or "").strip()
    consensus = (raw.get("consensus_summary") or raw.get("consensus") or "").strip()

    technology_readiness_level = (raw.get("technology_readiness_level") or "").strip()
    if not technology_readiness_level:
        technology_readiness_level = "TRL 3 – Experimental proof of concept"

    missing_technologies = _ensure_str_list(
        raw.get("missing_technologies"),
        fallback=["Advanced sensing/control systems", "Cost-effective manufacturing", "Reliable automation/safety validation"],
    )

    revival_probability = _clamp_int(raw.get("revival_probability"), 0, 100, 50)
    feasibility_score = _clamp_int(raw.get("feasibility_score"), 1, 10, 5)
    impact_score = _clamp_int(raw.get("impact_score"), 1, 10, 5)
    key_breakthrough_needed = (raw.get("key_breakthrough_needed") or "").strip() or "Unknown"

    innovation_tree = _ensure_str_list(
        raw.get("innovation_tree"),
        fallback=[f"Original {topic}", "Derived innovation 1", "Derived innovation 2", "Derived innovation 3"],
    )
    timeline = _ensure_str_list(
        raw.get("timeline"),
        fallback=["2026 - Prototype development begins", "2028 - Early experimental deployment", "2032 - Scale-up", "2040 - Broad adoption"],
    )

    analysis = {
        "idea": idea,
        "historian_analysis": historian or "Insufficient historical context available from scraped sources.",
        "engineer_analysis": engineer or "Insufficient engineering details available from scraped sources.",
        "futurist_analysis": futurist or "Insufficient future projections available from scraped sources.",
        "consensus_summary": consensus or "Consensus could not be confidently derived from available evidence.",
        "technology_readiness_level": technology_readiness_level,
        "missing_technologies": missing_technologies,
        "feasibility_score": feasibility_score,
        "impact_score": impact_score,
        "key_breakthrough_needed": key_breakthrough_needed,
    }

    # API contract + backward-compatible flat keys
    return {
        "analysis": analysis,
        "technology_readiness_level": technology_readiness_level,
        "missing_technologies": missing_technologies,
        "innovation_tree": innovation_tree,
        "revival_probability": revival_probability,
        "timeline": timeline,
        # Backward-compatible flat keys (existing frontend code used these)
        **analysis,
        "revival_probability": revival_probability,
        "technology_readiness_level": technology_readiness_level,
        "missing_technologies": missing_technologies,
        "innovation_tree": innovation_tree,
        "timeline": timeline,
    }


def analyze_with_gradient_agent(topic: str, context_text: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Acts as the multi-agent AI Future Lab using the Gradient AI.
    """
    prompt = f"""You are Ghost Internet — AI Future Lab.

You will simulate a 3-expert panel that analyzes a forgotten/abandoned/overlooked idea related to the user's topic.
Your experts are:
- Historian: origins + why it disappeared
- Engineer: technical barriers + why it failed at the time
- Futurist: how modern tech (AI/robotics/materials/biotech/etc.) could revive it today

User topic: {topic}

Context Text:
{context_text}

STRICT OUTPUT RULES:
- Output MUST be a single valid JSON object.
- Do not output markdown, code fences, or any non-JSON text.
- Use plain strings (no nested markdown).
- Keep each analysis section concise but high-signal (4–8 sentences each).
- YOUR SCORES MUST BE DYNAMIC integers based strictly on the following rubrics:
  * revival_probability (0-100): 0 = never coming back, 50 = 50/50 chance, 100 = actively being deployed today.
  * feasibility_score (1-10): 1 = physics/economics forbid it, 5 = possible but needs major trillions/breakthroughs, 10 = off-the-shelf parts exist today.
  * impact_score (1-10): 1 = trivial novelty, 5 = disrupts a single industry, 10 = existential paradigm shift for humanity.

Return EXACTLY this JSON schema (same keys, compatible types):
{{
  "idea": "Short description of the discovered idea",
  "historian_analysis": "Explain where the idea originated historically and why it disappeared.",
  "engineer_analysis": "Analyze the technical reasons the idea failed and what engineering barriers existed.",
  "futurist_analysis": "Explain how modern technologies like AI, robotics, materials science, or biotechnology could revive the idea today.",
  "consensus_summary": "A short, authoritative final summary of the expert panel.",
  "technology_readiness_level": "TRL X – short label (e.g., TRL 3 – Experimental proof of concept)",
  "missing_technologies": [
    "technology 1",
    "technology 2",
    "technology 3"
  ],
  "revival_probability": 0,
  "feasibility_score": 5,
  "impact_score": 5,
  "key_breakthrough_needed": "What technological breakthrough would make this idea viable.",
  "innovation_tree": [
    "Original idea name",
    "Derived idea 1",
    "Derived idea 2",
    "Derived idea 3"
  ],
  "timeline": [
    "2026 - Event description",
    "2028 - Event description",
    "2032 - Event description",
    "2040 - Event description"
  ]
}}
"""

    # Fallback response simulating the new JSON structure.
    # This guarantees the endpoint remains functional even if scraping/LLM fails.
    fallback_response = {
        "idea": f"Automated / Autonomous variation of {topic}",
        "historian_analysis": "This concept was widely discussed in early internet forums back in the early 2000s to solve massive efficiency problems, but stalled in prototypes.",
        "engineer_analysis": "Extreme initial infrastructure costs and a severe lack of compute power needed for real-time automation resulted in insurmountable engineering barriers at the time.",
        "futurist_analysis": "By integrating localized Edge AI models and autonomous drone networks, the core premise becomes both affordable and highly resilient today.",
        "consensus_summary": "While originally impossible to scale, modern AI and robotics make this a prime candidate for immediate technological trial runs.",
        "technology_readiness_level": "TRL 4 – Technology validated in lab",
        "missing_technologies": [
            "Low-cost high-density edge computing",
            "Certified multi-agent safety and verification tooling",
            "Standardized infrastructure interfaces"
        ],
        "revival_probability": 78,
        "feasibility_score": 6,
        "impact_score": 9,
        "key_breakthrough_needed": "Cheap, high-density edge computing and reliable multi-agent drone coordination algorithms.",
        "innovation_tree": [
            f"Original {topic}",
            "AI-Driven Infrastructure Grids",
            "Decentralized Drone Swarm Maintenance",
            "Self-Healing Autonomous Cities"
        ],
        "timeline": [
            "2025 - Initial Proof-of-Concept algorithms tested in simulation",
            "2027 - First closed-environment real-world trials succeed",
            "2030 - Limited commercial rollout begins in select tech hubs",
            "2035 - Widespread societal adoption and scaling"
        ]
    }

    if not GRADIENT_MODEL_ACCESS_KEY:
        logger.warning("Gradient configurations missing - using fallback response")
        return _normalize_future_lab_output(fallback_response, topic), {
            "provider": "gradient",
            "used_fallback": True,
            "reason": "GRADIENT_MODEL_ACCESS_KEY or GRADIENT_ACCESS_TOKEN is missing",
        }

    try:
        response = requests.post(
            f"{GRADIENT_BASE_URL}/chat/completions",
            headers={
                "Authorization": f"Bearer {GRADIENT_MODEL_ACCESS_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": GRADIENT_BASE_MODEL_SLUG,
                "messages": [
                    {"role": "system", "content": "You are Ghost Internet - AI Future Lab. Return a single valid JSON object only."},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.7,
                "max_completion_tokens": 1000,
            },
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json() or {}
        choices = payload.get("choices") or []
        if not choices or not isinstance(choices[0], dict):
            raise ValueError("Inference response did not include choices.")
        message = choices[0].get("message") or {}
        output = (message.get("content") or "").strip()

        extracted = _extract_json_object(output)
        if not extracted:
            raise ValueError("Model did not return valid JSON.")
        parsed = json.loads(extracted)
        if not isinstance(parsed, dict):
            raise ValueError("Model JSON was not an object.")
        return _normalize_future_lab_output(parsed, topic), {
            "provider": "gradient",
            "used_fallback": False,
            "reason": None,
        }
            
    except Exception as e:
        logger.error(f"Gradient API Inference Failed or Parse Error: {e}")
        # Return fallback on error to prevent crashing the endpoint during LLM hallucinations
        return _normalize_future_lab_output(fallback_response, topic), {
            "provider": "gradient",
            "used_fallback": True,
            "reason": str(e),
        }

@app.post("/discover")
async def discover_endpoint(req: DiscoverRequest):
    try:
        logger.info(f"Received query topic: {req.topic}")

        # Free "Option A" collection (Wikipedia + Archive + GitHub).
        # This avoids brittle DDG HTML scraping and bot-gating.
        sources, context_text = await asyncio.to_thread(collect_free_sources_and_context, req.topic, 7)

        # Optional extra enrichment: try scraping the URLs we found for additional plain text.
        # This is best-effort and will not break the pipeline if blocked.
        combined_text = context_text + ("\n\n" if context_text else "")
        scraped_count = 0
        for url in sources:
            extracted = await asyncio.to_thread(scrape_text, url)
            if extracted and len(extracted) > 100:
                combined_text += f"\n[SOURCE: {url}]\n{extracted}\n"
                scraped_count += 1
            if scraped_count >= 3:
                break

        # Add minimal context text if extraction completely fails or returns too little text.
        # We keep this local safeguard so the request still completes, but we expose it in `issues`.
        if len(combined_text.strip()) < 100:
            logger.warning("Failed to extract context from free sources, using fallback text.")
            combined_text = (
                f"Historical discussions about {req.topic} included experimental ideas that were abandoned "
                "due to technological, regulatory, or economic limitations."
            )

        logger.info(f"Using context of length {len(combined_text)} across {len(sources)} sources.")

        # Run independent research calls concurrently; never fail the endpoint if they fail.
        analysis_task = asyncio.to_thread(analyze_with_gradient_agent, req.topic, combined_text)
        papers_task = search_papers(req.topic, limit=5)
        patents_task = search_patents(req.topic, limit=3)
        companies_task = search_companies(req.topic, limit=5)

        analysis_result, research_papers, related_patents, related_companies = await asyncio.gather(
            analysis_task, papers_task, patents_task, companies_task, return_exceptions=True
        )

        if isinstance(analysis_result, Exception):
            logger.warning(f"Analysis task failed: {analysis_result}")
            analysis_dict = _normalize_future_lab_output({}, req.topic)
            analysis_meta = {
                "provider": "gradient",
                "used_fallback": True,
                "reason": str(analysis_result),
            }
        else:
            analysis_dict, analysis_meta = analysis_result
        if isinstance(research_papers, Exception):
            logger.warning(f"Paper search failed: {research_papers}")
            research_papers = []
        if isinstance(related_patents, Exception):
            logger.warning(f"Patent search failed: {related_patents}")
            related_patents = []
        if isinstance(related_companies, Exception):
            logger.warning(f"Company search failed: {related_companies}")
            related_companies = []
        
        # API response contract for Future Lab:
        #   analysis, sources, research_papers, related_patents, related_companies,
        #   technology_readiness_level, missing_technologies, innovation_tree, timeline
        # Plus backward-compatible flat keys for existing clients.
        issues = _build_discover_issues(
            sources=sources,
            context_text=context_text,
            analysis_meta=analysis_meta,
            research_papers=research_papers,
            related_patents=related_patents,
            related_companies=related_companies,
        )
        return {
            **analysis_dict,
            "sources": sources,
            "research_papers": research_papers,
            "related_patents": related_patents,
            "related_companies": related_companies,
            "issues": issues,
            "provider_status": {
                "analysis": analysis_meta,
                "papers": {"provider": "openalex", "result_count": len(research_papers)},
                "patents": {"provider": "google_patents", "result_count": len(related_patents)},
                "companies": {"provider": "github", "result_count": len(related_companies)},
            },
        }
    except Exception as e:
        logger.error(f"Server error during discover_endpoint: {e}")
        # Improve error handling by avoiding a crash
        raise HTTPException(status_code=500, detail="An internal server error occurred processing the discovery.")


@app.post("/save")
async def save_endpoint(req: SaveRequest):
    """
    Save an idea + analysis locally to SQLite. Never crashes on DB errors.
    """
    try:
        topic = (req.topic or "").strip()
        if not topic:
            raise HTTPException(status_code=400, detail="Missing topic.")

        analysis_json = json.dumps(req.analysis or {}, ensure_ascii=False)
        ts = datetime.now(timezone.utc).isoformat()

        def _write() -> int:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO saved_ideas (topic, analysis, timestamp) VALUES (?, ?, ?)",
                (topic, analysis_json, ts),
            )
            conn.commit()
            new_id = int(cur.lastrowid)
            conn.close()
            return new_id

        new_id = await asyncio.to_thread(_write)
        return {"ok": True, "id": new_id}
    except HTTPException:
        raise
    except Exception as e:
        logger.warning(f"Save failed: {e}")
        return {"ok": False, "id": None}


@app.get("/saved")
async def saved_endpoint():
    """
    Return saved ideas from SQLite. Never crashes on DB errors.
    """
    try:
        def _read() -> List[Dict[str, Any]]:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("SELECT id, topic, analysis, timestamp FROM saved_ideas ORDER BY id DESC LIMIT 50")
            rows = cur.fetchall()
            conn.close()
            out: List[Dict[str, Any]] = []
            for (id_, topic, analysis_text, timestamp) in rows:
                try:
                    analysis = json.loads(analysis_text) if analysis_text else {}
                except Exception:
                    analysis = {}
                out.append({"id": id_, "topic": topic, "analysis": analysis, "timestamp": timestamp})
            return out

        items = await asyncio.to_thread(_read)
        return {"items": items}
    except Exception as e:
        logger.warning(f"Read saved ideas failed: {e}")
        return {"items": []}

@app.delete("/saved/{item_id}")
async def delete_saved_endpoint(item_id: int):
    """
    Delete a saved idea from SQLite by ID.
    """
    try:
        def _delete() -> bool:
            conn = sqlite3.connect(DB_PATH)
            cur = conn.cursor()
            cur.execute("DELETE FROM saved_ideas WHERE id = ?", (item_id,))
            changes = conn.total_changes
            conn.commit()
            conn.close()
            return changes > 0

        success = await asyncio.to_thread(_delete)
        if not success:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"ok": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete saved idea: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete saved idea")

# Mount Frontend application
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
