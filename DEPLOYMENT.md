# OmniLearn AI - Vercel & Render Deployment Guide

This project is configured for deployment to **Vercel** (Frontend & Serverless Token API) and **Render** (Full Web Application + Background Voice Agent Worker).

---

## 🚀 1. Deploying to Vercel

Vercel hosts the responsive frontend and serverless API handlers (`/api/token`, `/api/status`, `/api/health`, `/api/ai/solve`, `/api/ai/chat`).

### Steps:
1. Push this repository to GitHub or GitLab.
2. Go to [vercel.com](https://vercel.com/) and click **"Add New Project"**.
3. Import your repository.
4. Set the **Framework Preset** to **Other** (Vercel automatically detects `vercel.json` and Python functions in `api/`).
5. Under **Environment Variables**, add:
   - `LIVEKIT_URL`: Your LiveKit Cloud URL (e.g. `wss://your-project.livekit.cloud`)
   - `LIVEKIT_API_KEY`: Your LiveKit API Key (`API...`)
   - `LIVEKIT_API_SECRET`: Your LiveKit API Secret
6. Click **Deploy**.

> **Note**: Vercel utilizes `api/requirements.txt` containing only `livekit-api>=0.8.0`, ensuring lightning-fast serverless builds within size limits.

---

## ⚡ 2. Deploying to Render

Render can run both the **OmniLearn Web Service** and the **OmniLearn Voice Agent Worker** using the included `render.yaml` Blueprint or manual service setup.

### Option A: 1-Click Blueprint (Recommended)
1. Push your repository to GitHub.
2. In your [Render Dashboard](https://dashboard.render.com/), click **New +** > **Blueprint**.
3. Connect your repository. Render will automatically parse `render.yaml` and configure:
   - **`omnilearn-web`**: Web Service on the Free plan running `python server.py`.
   - **`omnilearn-voice-worker`**: Worker Service running `python agent.py start`.
4. Enter your environment variables (`LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET`, and optional AI keys: `OPENAI_API_KEY`, `DEEPGRAM_API_KEY`, `CARTESIA_API_KEY`).
5. Click **Apply**.

### Option B: Free-Tier All-in-One (Single Web Service)
If you are on the Render Free plan and don't want a separate paid worker:
1. Create a **New Web Service** from your repository.
2. Set:
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python server.py`
3. Add Environment Variables:
   - `LIVEKIT_URL`: `wss://your-project.livekit.cloud`
   - `LIVEKIT_API_KEY`: `API...`
   - `LIVEKIT_API_SECRET`: `secret...`
   - `START_WORKER`: `true` *(This automatically launches `agent.py` in a background process within the web container!)*
4. Click **Create Web Service**.

---

## 🧪 Local Testing Verification

Test the local web server:
```bash
python server.py
# Web server starts at http://localhost:7860
```

Test the agent worker:
```bash
python agent.py dev
# Connects to LiveKit room and handles speech and whiteboard actions
```
