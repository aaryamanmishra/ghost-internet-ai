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

# Configure Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Ghost Internet - AI Archaeologist")

# Add CORS Middleware to allow the frontend to call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GRADIENT_ACCESS_TOKEN = os.getenv("pdjVWLm4wSD_yHRZl-wGA9dNi5AEbF0_")
GRADIENT_WORKSPACE_ID = os.getenv("DigitalOcean Managed")

class DiscoverRequest(BaseModel):
    topic: str

def web_search(query: str, max_results: int = 3):
    """Searches the open web using DuckDuckGo HTML search securely."""
    results = []
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        search_query = f"{query} history origin forgotten ideas"
        url = "https://html.duckduckgo.com/html/"
        data = {"q": search_query}
        
        resp = requests.post(url, headers=headers, data=data, timeout=10)
        resp.raise_for_status()
        
        soup = BeautifulSoup(resp.content, "html.parser")
        for a in soup.find_all('a', class_='result__url'):
            href = a.get('href')
            if href:
                # Resolve DDG redirect URL if necessary
                if 'uddg=' in href:
                    from urllib.parse import unquote
                    actual_url = unquote(href.split('uddg=')[1].split('&')[0])
                    results.append(actual_url)
                else:
                    results.append(href)
            
            if len(results) >= max_results:
                break
    except Exception as e:
        logger.error(f"Search API Error: {e}")
        
    return results[:max_results]

def scrape_text(url: str, max_length: int = 2000) -> str:
    """Extracts text content cleanly with timeout protection."""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }
        resp = requests.get(url, headers=headers, timeout=5)
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

def analyze_with_gradient_agent(topic: str, context_text: str):
    """
    Acts as the ghost-internet-archaeologist using the Gradient AI.
    """
    prompt = f"""You are 'ghost-internet-archaeologist', an AI research archaeologist agent.
Analyze the following internet text to identify forgotten, abandoned, or overlooked ideas regarding: {topic}

Context Text:
{context_text}

Return structured results EXACTLY matching the formatting below (do not include extra conversational text):

IDEA
[Short description of the discovered idea]

ORIGINAL CONTEXT
[Where the idea appeared and what problem it tried to solve]

WHY IT FAILED
[Possible reasons the idea did not succeed]

MODERN REVIVAL
[How modern technologies such as AI, robotics, biotechnology, or new materials could make the idea viable today]

POTENTIAL IMPACT
[How reviving this idea could benefit society]
"""

    if not GRADIENT_ACCESS_TOKEN or not GRADIENT_WORKSPACE_ID:
        logger.warning("Gradient configurations missing - using fallback response for demonstration")
        return (
            "IDEA\n"
            f"Automated / Autonomous variation of {topic} concept.\n\n"
            "ORIGINAL CONTEXT\n"
            "This concept was widely discussed in early internet forums and decentralized research blogs back in the early 2000s to solve massive efficiency problems, but stalled in prototypes.\n\n"
            "WHY IT FAILED\n"
            "Extremely high initial infrastructure costs, coupled with a severe lack of compute power needed for the necessary real-time automation.\n\n"
            "MODERN REVIVAL\n"
            "By integrating localized Edge AI models and autonomous drone maintenance networks, the core premise becomes both affordable and highly resilient today.\n\n"
            "POTENTIAL IMPACT\n"
            "It holds the potential to dramatically reinvent sustainable operations and drive autonomous technological renaissance across multiple sectors."
        )

    try:
        from gradientai import Gradient
        with Gradient(access_token=GRADIENT_ACCESS_TOKEN, workspace_id=GRADIENT_WORKSPACE_ID) as gradient:
            # Utilizing Llama 3 or Nous Hermes as the foundation for the Agent
            agent_model = gradient.get_base_model(base_model_slug="llama3-8b-chat")
            response = agent_model.complete(
                query=prompt,
                max_generated_token_count=600,
                temperature=0.7
            )
            return response.generated_output
    except Exception as e:
        logger.error(f"Gradient API Inference Failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI Agent failed to analyze the texts: {str(e)}")

@app.post("/discover")
def discover_endpoint(req: DiscoverRequest):
    try:
        logger.info(f"Received query topic: {req.topic}")
        
        urls = web_search(req.topic, max_results=3)
        valid_sources = []
        combined_text = ""
        
        for url in urls:
            extracted = scrape_text(url)
            if extracted and len(extracted) > 100:
                combined_text += f"\n[SOURCE: {url}]\n{extracted}\n"
                valid_sources.append(url)
                
            if len(valid_sources) >= 3:
                break
                
        # Add fallback text if scraping completely fails or returns too little text
        if len(combined_text) < 100:
            logger.warning("Failed to cleanly extract text from sources, using fallback text.")
            combined_text = f"Historical discussions about {req.topic} included experimental ideas that were abandoned due to technological or economic limitations."
            
        logger.info(f"Using context of length {len(combined_text)} across {len(valid_sources)} sources.")
        
        analysis_result = analyze_with_gradient_agent(req.topic, combined_text)
        
        return {
            "analysis": analysis_result,
            "sources": valid_sources
        }
    except Exception as e:
        logger.error(f"Server error during discover_endpoint: {e}")
        # Improve error handling by avoiding a crash
        raise HTTPException(status_code=500, detail="An internal server error occurred processing the discovery.")

# Mount Frontend application
app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")
