# Ghost Internet - AI Future Lab

**A DigitalOcean Gradient AI Hackathon Project**

Ghost Internet - AI Future Lab is a full-stack web app that uncovers overlooked or abandoned ideas, gathers public context about them, and simulates what their future could look like if modern technology revived them today.

The app follows this pipeline:

User Query -> Source Collection -> Context Extraction -> AI Analysis -> Structured Output

## Architecture Overview

- **Backend:** FastAPI + Python
- **Frontend:** Vanilla HTML, CSS, and JavaScript
- **Primary source collection:**
  - Wikipedia API
  - Internet Archive Advanced Search
  - GitHub Search API
- **Research enrichment:**
  - OpenAlex for research papers
  - Temporary best-effort Google-based patent discovery
  - GitHub organization search for company/startup-style signals
- **Persistence:** local SQLite database for saved ideas
- **AI engine:** DigitalOcean Gradient AI serverless inference when configured, with an explicit fallback response when credentials are missing or inference fails
- **Deployment:** Dockerized for local or platform deployment

## What the App Generates

For each discovery request, the app returns:

- Idea summary
- Historian analysis
- Engineer analysis
- Futurist analysis
- Consensus summary
- Revival probability
- Feasibility score
- Impact score
- Key breakthrough needed
- Technology readiness level
- Missing technologies
- Innovation tree
- Future timeline
- Source links
- Research papers
- Related patents
- Related companies/startups
- Provider status and detected issues

## Current Feature Set

### Discovery

- Accepts a topic from the UI
- Collects public sources
- Optionally scrapes additional plain text from collected URLs
- Runs AI analysis over the assembled context
- Returns structured results for the frontend

### Research Enrichment

- Looks up research papers via OpenAlex
- Looks up patents via a temporary free Google-based best-effort search path and patentscope.wipo.int
- Looks up company/startup signals using GitHub organization search

### Saved Ideas

- Saves a topic and its analysis to SQLite
- Displays the recent saved ideas list in the UI

### Issue Reporting

- Reports when the AI response came from fallback logic
- Reports when paper, patent, or company enrichment returns no results
- Exposes provider status data in the `/discover` response

## API Endpoints

### `POST /discover`

Request body:

```json
{
  "topic": "abandoned transportation technologies"
}
```

Response includes:

- `analysis`
- `sources`
- `research_papers`
- `related_patents`
- `related_companies`
- `issues`
- `provider_status`
- Backward-compatible top-level analysis fields

### `POST /save`

Request body:

```json
{
  "topic": "abandoned transportation technologies",
  "analysis": {
    "idea": "Example idea"
  }
}
```

### `GET /saved`

Returns the most recent saved ideas from local SQLite storage.

## Setup

### Requirements

- Python 3.9+
- Docker, if you want to run the containerized version

### Environment Variables

Create a `.env` file in the project root or export these variables in your shell:

```env
# Required for live DigitalOcean serverless inference
GRADIENT_MODEL_ACCESS_KEY=your_gradient_model_access_key_here

# Optional compatibility alias
GRADIENT_ACCESS_TOKEN=your_gradient_model_access_key_here

# Optional model override
GRADIENT_BASE_MODEL_SLUG=llama3-8b-instruct

# Optional base URL override
GRADIENT_BASE_URL=https://inference.do-ai.run/v1

# Optional but recommended for higher GitHub limits
GITHUB_TOKEN=your_github_token_here
```

### Run Locally

1. Clone the repository and move into the project folder.
2. Create a virtual environment.
3. Install dependencies.
4. Start Uvicorn.
5. Open the app in your browser.

Example:

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn backend.main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

### Run with Docker

```bash
docker build -t ghost-internet .
docker run -p 8080:8080 \
  --env GRADIENT_MODEL_ACCESS_KEY=your_model_access_key \
  ghost-internet
```

## Deployment Notes

For DigitalOcean App Platform or any similar deployment target:

1. Push the repo to GitHub.
2. Deploy from the included `Dockerfile`.
3. Set `GRADIENT_MODEL_ACCESS_KEY` for DigitalOcean serverless inference.
4. Optionally set `GITHUB_TOKEN` to reduce GitHub search rate limiting.
5. Keep the service port at `8080`.

## Known Limitations

- If `GRADIENT_MODEL_ACCESS_KEY` is missing or invalid, the app returns a built-in fallback analysis instead of live model output.
- Patent enrichment is still best-effort and can fail because Google blocks automated access patterns.
- Company/startup enrichment is best-effort and based on GitHub organization search, so results can be noisy or sparse.
- GitHub company search is more likely to degrade without `GITHUB_TOKEN` because of rate limiting.
- OpenAlex paper search works without a key, but broad topics can still return loosely related papers.
- HTML extraction from third-party pages is still best-effort and may fail depending on the target site.

## Demo Flow

1. Open the app.
2. Enter a topic such as `abandoned transportation technologies`.
3. Click `Unearth`.
4. Review the analysis, metrics, enrichment results, sources, and detected issues.
5. Click `Save` to store the result locally.
