## Run & Test Guide – Smart Buyer Web App

Follow these steps to run the full Smart Buyer experience locally.

### 1. Backend (FastAPI)
```bash
pip install -r requirements.txt
cd apps/api
uvicorn main:app --reload
```
- Backend runs at `http://localhost:8000` (default).  
- Ensure `.env` or environment variables include any required credentials.

### 2. Frontend (Next.js)
```bash
cd apps/web-app
npm install
npm run lint

cp .env.local.example .env.local  # If hidden files are unavailable, use env.local.example
# edit .env.local if your API is elsewhere
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
# SMART_BUYER_API_BASE_URL=http://localhost:8000
npm run dev
```
- App is served at `http://localhost:3000`.

### 3. Manual Testing Flow
1. Open `http://localhost:3000`.
2. Click **Start Chatting** to create a conversation (`/chat/<session-id>`).
3. Send a prompt (e.g., “Find me budget laptops”).
   - Chat history is saved locally and listed in the sidebar.
   - While the backend works, the UI shows a “Thinking…” state and disables Send.
   - Assistant responses include Smart Buyer metadata (top recommendations, summaries).
4. Use the sidebar to switch between existing chats or start new ones; history persists automatically.

### 4. Useful Commands
```bash
# Lint frontend (from repo root)
npm run lint

# Backend Smart Buyer E2E tests
pytest tests/e2e/test_http_smart_buyer.py
```
- Stop servers with `Ctrl+C` in their respective terminals.

With both services running you get the same flow as end users: the Next.js UI calls `POST /v1/smart-buyer/chat` in the FastAPI backend and renders Smart Buyer’s streaming responses in real time.

### 5. Docker (optional)
Use Docker for a quick start without installing local runtimes.

```bash
# From repo root
docker compose -f infra/docker-compose.yml up --build
```

- API is exposed on `http://localhost:8000`, Web UI on `http://localhost:3000`.
- Rebuild after code changes: `docker compose -f infra/docker-compose.yml up --build`.
- Stop everything with `docker compose -f infra/docker-compose.yml down`.
