# Ghost Internet — AI Future Lab 👻

**A DigitalOcean Gradient AI Hackathon Project**

Ghost Internet — AI Future Lab is an AI-powered full-stack web application designed to uncover forgotten, abandoned, or overlooked ideas, evaluate why they failed, and simulate potential technological futures if revived today.

It preserves the original working pipeline:

User Query → Search → Gather/Scrape Text → AI Analysis → Structured Output

## 🛠️ Architecture Overview

- **Backend:** Python + FastAPI
- **Free Source Pipeline (default):**
  - **Wikipedia API** (stable extracts, no scraping required)
  - **Internet Archive Advanced Search** (historical artifacts + metadata)
  - **GitHub Search API** (engineering context + repo metadata)
  - Optional best-effort HTML extraction via **BeautifulSoup** for some URLs
- **Legacy Fallback Search:** DuckDuckGo (best-effort; may be blocked depending on network/bot gating)
- **AI Engine:** DigitalOcean Gradient AI integration (with a robust fallback response if not configured).
- **Frontend:** Vanilla JS + CSS3 + HTML5 with a card-based layout for structured sections. Fully responsive.
- **Deployment:** Dockerized and ready for DigitalOcean App Platform.

## ✨ What the Future Lab Generates

For each topic, the system returns structured sections:

- **Idea**
- **Historian Analysis**
- **Engineer Analysis**
- **Futurist Analysis**
- **Consensus Summary**

Plus metrics and simulations:

- **Revival Probability** (0–100%)
- **Feasibility Score** (1–10)
- **Impact Score** (1–10)
- **Key Breakthrough Needed**
- **Innovation Tree**
- **Future Timeline**

## 🚀 Setup Instructions

### 1. Requirements
Ensure you have Python 3.9+ and Docker installed on your machine.

### 2. Environment Variables
To connect to DigitalOcean Gradient AI, set:

Create a `.env` file in the root directory (or export them to your shell):
```env
GRADIENT_ACCESS_TOKEN=your_gradient_access_token_here
GRADIENT_WORKSPACE_ID=your_gradient_workspace_id_here
# Optional: override the base model slug
GRADIENT_BASE_MODEL_SLUG=llama3-8b-chat

# Optional but recommended (improves GitHub search rate limits)
GITHUB_TOKEN=your_github_token_here
```

### 3. How to Run Locally

**Using pure Python:**
1. Clone the repository and navigate to the root directory `ghost-internet/`.
2. Create and activate a Virtual Environment (Optional but recommended):
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Start the application using Uvicorn:
   ```bash
   python -m uvicorn backend.main:app --reload
   ```
5. Navigate to `http://127.0.0.1:8000` in your browser.

**Using Docker:**
```bash
docker build -t ghost-internet .
docker run -p 8080:8080 --env GRADIENT_ACCESS_TOKEN=your_token --env GRADIENT_WORKSPACE_ID=your_workspace ghost-internet
```

## ☁️ How to Deploy on DigitalOcean App Platform

This application is ready out-of-the-box for the DO App Platform.

1. Push your code to a GitHub repository.
2. In the DigitalOcean Control Panel, navigate to **Apps** -> **Create App**.
3. Select your repository provider (GitHub) and pick your repo.
4. DigitalOcean will automatically detect the `Dockerfile`.
5. Under **Environment Variables**, click **Edit** and add:
   - `GRADIENT_ACCESS_TOKEN`
   - `GRADIENT_WORKSPACE_ID`
6. Keep the HTTP Port at `8080`.
7. Click **Deploy**. The application will automatically build and become accessible via a public URL!

## 🔮 Demo Use Case

1. Navigate to the web application.
2. Enter `"abandoned transportation technologies"` (or any topic) in the input field.
3. Click **Unearth**.
4. The system gathers free sources (Wikipedia/Archive/GitHub), optionally extracts additional page text, and triggers the Future Lab analysis.
5. The UI displays the expert panel, revival metrics, an innovation tree, a future timeline, and clickable sources.
