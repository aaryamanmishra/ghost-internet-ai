# Ghost Internet — AI Archaeologist 👻

**A DigitalOcean Gradient AI Hackathon Project**

The Ghost Internet AI Archaeologist is an AI-powered full-stack web application designed to scour the web for forgotten, abandoned, or overlooked ideas, analyze them using a Gradient AI Agent, and propose modern technological revivals. 

## 🛠️ Architecture Overview

- **Backend:** Python + FastAPI
- **Web Scraping Pipeline:** duckduckgo-search + BeautifulSoup. Securely fetches real-time historical forum and internet context based on user queries.
- **AI Engine:** DigitalOcean Gradient AI Agent integration. Processes the scraped text and returns a highly structured analytical payload.
- **Frontend:** Vanilla JS + CSS3 + HTML5. Features dynamic Glassmorphism styling, clean animations, and structured rendering. Fully responsive.
- **Deployment:** Dockerized and ready for DigitalOcean App Platform.

## 🚀 Setup Instructions

### 1. Requirements
Ensure you have Python 3.9+ and Docker installed on your machine.

### 2. Environment Variables
To connect to DigitalOcean Gradient AI safely, you must set the following environment variables.

Create a `.env` file in the root directory (or export them to your shell):
```env
GRADIENT_ACCESS_TOKEN=your_gradient_access_token_here
GRADIENT_WORKSPACE_ID=your_gradient_workspace_id_here
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
   uvicorn backend.main:app --host 0.0.0.0 --port 8080 --reload
   ```
5. Navigate to `http://localhost:8080` in your browser.

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
2. Enter `"forgotten robotics inventions"` in the "e.g., forgotten renewable energy inventions" input field.
3. Click **Unearth**.
4. The system will search, scrape, and trigger the agent to analyze the findings.
5. The result card displays the original context, reasoning for failure, modern AI-driven revival ideas, and the potential impact of modernizing the solution!
