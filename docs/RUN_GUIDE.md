# QuantumX AI - Run Guide

**Complete guide to get QuantumX AI running on your machine**

---

## 📋 Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start (5 minutes)](#quick-start)
3. [Detailed Setup](#detailed-setup)
4. [Running the Application](#running-the-application)
5. [Testing & Verification](#testing--verification)
6. [Development Workflow](#development-workflow)
7. [Common Commands](#common-commands)
8. [Troubleshooting](#troubleshooting)
9. [Project Structure](#project-structure)
10. [Next Steps](#next-steps)

---

## Prerequisites

### Required Software

| Software | Version | Check Command | Install Link |
|----------|---------|---------------|--------------|
| Python | 3.10+ | `python --version` | [python.org](https://python.org) |
| Node.js | 18+ | `node --version` | [nodejs.org](https://nodejs.org) |
| npm/yarn | Latest | `npm --version` | Comes with Node.js |
| Git | Any | `git --version` | [git-scm.com](https://git-scm.com) |

### Optional (for advanced features)

| Software | Purpose | Install Command |
|----------|---------|-----------------|
| Redis | Caching (Phase B) | `brew install redis` (Mac) |
| PostgreSQL | Database (Phase B) | `brew install postgresql` (Mac) |
| Docker | Containerization | [docker.com](https://docker.com) |

### API Keys Required

- **OpenAI API Key**: Get from [platform.openai.com](https://platform.openai.com)
- **Anthropic API Key** (optional): Get from [console.anthropic.com](https://console.anthropic.com)

---

## Quick Start

**Get running in 5 minutes:**

```bash
# 1. Clone the repository (if not already)
cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai

# 2. Setup Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# 3. Set PYTHONPATH (CRITICAL!)
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 4. Install backend dependencies
pip install -r apps/api/requirements.txt

# 5. Create .env file
cp apps/api/.env.example apps/api/.env
# Edit apps/api/.env and add your OpenAI API key

# 6. Install frontend dependencies
cd apps/web-app
npm install
cd ../..

# 7. Create frontend .env
cp apps/web-app/.env.local.example apps/web-app/.env.local

# 8. Run the application
# Terminal 1: Start API
cd apps/api && uvicorn src.main:app --reload --port 8000

# Terminal 2: Start Frontend
cd apps/web-app && npm run dev
```

**Access:**
- Frontend: http://localhost:3000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/v1/healthz

---

## Detailed Setup

### Step 1: Clone & Navigate

```bash
# If you don't have the repo yet
git clone <your-repo-url> quantumx-ai
cd quantumx-ai

# Or if you already have it
cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai
```

### Step 2: Python Environment Setup

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Verify activation (should show venv path)
which python
```

### Step 3: Set PYTHONPATH (CRITICAL!)

This ensures Python can find all your packages.

```bash
# For current session
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify it's set
echo $PYTHONPATH

# To make it permanent, add to your shell profile
# For Zsh (macOS default):
echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.zshrc
source ~/.zshrc

# For Bash:
echo 'export PYTHONPATH="${PYTHONPATH}:$(pwd)"' >> ~/.bashrc
source ~/.bashrc
```

**Alternative: Install packages in editable mode**

```bash
# This also works but PYTHONPATH is simpler
pip install -e .
# check import OK
python3 -c "import agent_core, memory_core, tools, decision_core, search_core; print('OK')"

### Step 4: Install Backend Dependencies

```bash
# Install from requirements.txt
pip install -r requirements.txt

# Verify installation
pip list | grep fastapi
pip list | grep uvicorn
pip list | grep pydantic
```

**What gets installed:**
- FastAPI - Web framework
- Uvicorn - ASGI server
- Pydantic - Data validation
- HTTPX - Async HTTP client
- OpenAI/Anthropic - LLM providers (optional)

### Step 5: Configure Backend

```bash
# Copy example environment file
cp apps/api/.env.example apps/api/.env

# Edit with your favorite editor
nano apps/api/.env
# or
code apps/api/.env
# or
vim apps/api/.env
```

**Required Configuration** (`apps/api/.env`):

```bash
# API Configuration
QX_ENV=dev
QX_HOST=0.0.0.0
QX_PORT=8000
QX_DEBUG=true

# LLM Provider - IMPORTANT!
QX_LLM_PROVIDER=openai
QX_OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxxx  # ← ADD YOUR KEY HERE

# Optional: Anthropic
# QX_ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxxx

# CORS - Allow frontend
QX_CORS_ORIGINS=http://localhost:3000,http://localhost:3001

# Features
QX_FEATURES__ENABLE_SMART_BUYER=true
QX_FEATURES__ENABLE_RAG=false
QX_FEATURES__ENABLE_SEARCH_CACHE=false

# Observability
QX_ENABLE_REQUEST_ID=true
```

**Getting your OpenAI API Key:**
1. Go to https://platform.openai.com
2. Sign in or create account
3. Navigate to API Keys section
4. Create new secret key
5. Copy and paste into `.env` file

### Step 6: Install Frontend Dependencies

```bash
# Navigate to frontend
cd apps/web-app

# Install dependencies
npm install

# Verify installation
npm list next react react-dom
```

**What gets installed:**
- Next.js 14 - React framework
- React 18 - UI library
- TypeScript - Type safety
- Tailwind CSS - Styling (configured)

### Step 7: Configure Frontend

```bash
# Create frontend environment file
cp .env.local.example .env.local

# Edit configuration
nano .env.local
```

**Required Configuration** (`apps/web-app/.env.local`):

```bash
# API URL - Backend location
NEXT_PUBLIC_API_URL=http://localhost:8000

# Optional features
NEXT_PUBLIC_ENABLE_STREAMING=true
NEXT_PUBLIC_ENABLE_MULTI_SESSION=true
```

### Step 8: Verify Configuration

```bash
# Check backend .env exists and has API key
cat apps/api/.env | grep OPENAI_API_KEY

# Check frontend .env.local exists
cat apps/web-app/.env.local | grep API_URL

# Check PYTHONPATH is set
echo $PYTHONPATH | grep quantumx-ai
```

---

## Running the Application

### Option 1: Using Startup Scripts (Recommended)

**First, create the startup scripts:**

Create `scripts/start-api.sh`:

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/.."

echo "🚀 Starting QuantumX API..."

# Activate venv if exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Check .env exists
if [ ! -f "apps/api/.env" ]; then
    echo "❌ Missing apps/api/.env file"
    echo "💡 Copy from .env.example and add your API keys"
    exit 1
fi

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start API
cd apps/api
echo "📡 API starting at http://localhost:8000"
echo "📚 Docs available at http://localhost:8000/docs"
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

Create `scripts/start-frontend.sh`:

```bash
#!/bin/bash
set -e

cd "$(dirname "$0")/../apps/web-app"

echo "🎨 Starting QuantumX Frontend..."

# Check .env.local exists
if [ ! -f ".env.local" ]; then
    echo "❌ Missing .env.local file"
    echo "💡 Copy from .env.local.example"
    exit 1
fi

# Install deps if needed
if [ ! -d "node_modules" ]; then
    echo "📦 Installing dependencies..."
    npm install
fi

# Start dev server
echo "🌐 Frontend starting at http://localhost:3000"
npm run dev
```

**Make scripts executable:**

```bash
chmod +x scripts/start-api.sh
chmod +x scripts/start-frontend.sh
```

**Run the application:**

```bash
# Terminal 1: Start Backend
./scripts/start-api.sh

# Terminal 2: Start Frontend (in new terminal)
./scripts/start-frontend.sh
```

### Option 2: Manual Commands

**Terminal 1 - Backend:**

```bash
# Navigate to project root
cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai

# Activate venv
source venv/bin/activate

# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Navigate to API
cd apps/api

# Start server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 - Frontend:**

```bash
# Navigate to frontend
cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai/apps/web-app

# Start Next.js dev server
npm run dev
```

### Option 3: Docker (Coming Soon - Phase C)

```bash
# Will be available after Phase C
docker-compose up
```

---

## Testing & Verification

### Backend Health Checks

```bash
# Test 1: Basic health check
curl http://localhost:8000/v1/healthz
# Expected: {"status": "ok"}

# Test 2: Readiness check (tools registered)
curl http://localhost:8000/v1/readyz
# Expected: {"status": "ready", "tools": ["price_compare", "decision_score"]}

# Test 3: API documentation
open http://localhost:8000/docs
# Should show interactive API docs

# Test 4: Root endpoint
curl http://localhost:8000/
# Expected: {"name": "QuantumX API", "version": "v1.0"}
```

### Frontend Health Check

```bash
# Open in browser
open http://localhost:3000

# Should see:
# - QuantumX AI homepage
# - "Start Chatting" button
# - Feature cards
```

### End-to-End Test

**Test Smart Buyer Feature:**

```bash
# Test query 1: Simple product search
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "iPhone 15",
    "top_k": 5
  }'

# Expected response structure:
# {
#   "request_id": "...",
#   "query": "iPhone 15",
#   "latency_ms": <number>,
#   "offers": [...],
#   "scoring": {"best": "...", "confidence": ...},
#   "explanation": {...}
# }

# Test query 2: With preferences
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Samsung Galaxy",
    "top_k": 6,
    "prefs": {
      "budget": 20000000
    }
  }'

# Test query 3: Generic query
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{
    "query": "laptop gaming",
    "top_k": 5
  }'
```

**Test via Frontend:**

1. Open http://localhost:3000
2. Click "Start Chatting"
3. Type: "So sánh giá iPhone 15"
4. Press Enter
5. Should see:
   - Loading indicator
   - Results with product cards
   - Recommendations
   - Pros/cons

### Verify MVP Success Criteria

- [ ] ✅ API responds in ≤ 5 seconds
- [ ] ✅ Returns ≥ 3 product offers
- [ ] ✅ Response has `scoring.best` and `confidence`
- [ ] ✅ Response has `explanation` with recommendations
- [ ] ✅ No crashes on queries: "iPhone", "Samsung", "Xiaomi"
- [ ] ✅ Frontend displays results cleanly
- [ ] ✅ Can create new chat sessions
- [ ] ✅ Chat history persists in localStorage

---

## Development Workflow

### Daily Development Routine

```bash
# 1. Start your day
cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 2. Pull latest changes (if team)
git pull origin main

# 3. Start services
./scripts/start-api.sh       # Terminal 1
./scripts/start-frontend.sh  # Terminal 2

# 4. Make your changes
# Edit files in your IDE

# 5. Test changes
curl http://localhost:8000/v1/smart-buyer -X POST ...

# 6. Check logs
# Backend logs appear in Terminal 1
# Frontend logs appear in Terminal 2

# 7. Commit changes
git add .
git commit -m "feat: your feature description"
git push origin your-branch
```

### Hot Reload

Both backend and frontend support hot reload:

**Backend (FastAPI with --reload):**
- Edit any `.py` file
- Server automatically restarts
- See changes immediately

**Frontend (Next.js):**
- Edit any `.tsx`, `.ts`, `.css` file
- Page automatically refreshes
- See changes in ~1 second

### Adding New Features

**Backend Feature:**

```bash
# 1. Add code to appropriate package
vim packages/search_core/search_core/new_feature.py

# 2. Register if it's a tool
vim packages/tools/tools/registry.py

# 3. Add route if needed
vim apps/api/src/api/routes/smart_buyer.py

# 4. Test
curl http://localhost:8000/v1/your-new-endpoint

# 5. Check logs for errors
# See Terminal 1
```

**Frontend Feature:**

```bash
# 1. Add component
vim apps/web-app/src/components/NewComponent.tsx

# 2. Add to page
vim apps/web-app/src/pages/chat.tsx

# 3. Check browser
open http://localhost:3000

# 4. Check console for errors (F12)
```

### Running Tests

```bash
# Python tests (when implemented - Phase C)
pytest tests/ -v

# Frontend tests (when implemented - Phase C)
cd apps/web-app
npm test

# Type checking
cd apps/web-app
npm run type-check

# Linting
cd apps/web-app
npm run lint
```

### Database Migrations (Phase B)

```bash
# When PostgreSQL is added
cd infra/migrations
psql -d quantumx -f 001_initial.sql
```

### Checking Logs

**Backend Logs:**
```bash
# Logs appear in Terminal 1 where you started the API
# Format: timestamp | level | name | message

# Grep for specific request
# (logs show request_id)
grep "request_id=abc123" api.log

# Check for errors
grep "ERROR" api.log
```

**Frontend Logs:**
```bash
# Development logs in Terminal 2
# Production logs (after build):
cd apps/web-app
npm run build
npm start
```

---

## Common Commands

### Backend Commands

```bash
# Start API
cd apps/api && uvicorn src.main:app --reload --port 8000

# Start with different port
cd apps/api && uvicorn src.main:app --reload --port 8001

# Start in production mode (no reload)
cd apps/api && uvicorn src.main:app --host 0.0.0.0 --port 8000

# Check syntax errors
find apps/api -name "*.py" -exec python -m py_compile {} \;

# Format code (if black installed)
black apps/api packages/

# Type check (if mypy installed)
mypy apps/api packages/

# Check imports
python -c "from apps.api.src.main import app; print('✅ Imports OK')"
```

### Frontend Commands

```bash
# Development server
cd apps/web-app && npm run dev

# Production build
cd apps/web-app && npm run build

# Start production server
cd apps/web-app && npm start

# Type checking
cd apps/web-app && npx tsc --noEmit

# Linting
cd apps/web-app && npm run lint

# Format code (if prettier configured)
cd apps/web-app && npx prettier --write src/
```

### Package Management

```bash
# Update Python dependencies
pip list --outdated
pip install --upgrade package-name

# Update frontend dependencies
cd apps/web-app
npm outdated
npm update

# Add new Python package
pip install new-package
pip freeze > apps/api/requirements.txt

# Add new npm package
cd apps/web-app
npm install new-package
```

### Git Commands

```bash
# Create feature branch
git checkout -b feature/your-feature

# Check status
git status

# Stage changes
git add .

# Commit
git commit -m "feat: add new feature"

# Push
git push origin feature/your-feature

# Pull latest
git pull origin main

# Merge main into your branch
git merge main
```

---

## Troubleshooting

### Issue 1: Import Errors

**Error:**
```
ModuleNotFoundError: No module named 'packages'
```

**Solution:**
```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Verify
echo $PYTHONPATH

# Or install in editable mode
pip install -e packages/agent_core
```

### Issue 2: Port Already in Use

**Error:**
```
ERROR: [Errno 48] error while attempting to bind on address ('0.0.0.0', 8000)
```

**Solution:**
```bash
# Find process using port 8000
lsof -ti:8000

# Kill the process
lsof -ti:8000 | xargs kill -9

# Or use different port
uvicorn src.main:app --port 8001
```

### Issue 3: Missing .env File

**Error:**
```
pydantic_settings.sources.EnvSettingsSource: error loading settings
```

**Solution:**
```bash
# Create .env file
cp apps/api/.env.example apps/api/.env

# Edit and add your API keys
nano apps/api/.env
```

### Issue 4: OpenAI API Error

**Error:**
```
openai.error.AuthenticationError: Incorrect API key provided
```

**Solution:**
```bash
# Check API key is set
cat apps/api/.env | grep OPENAI_API_KEY

# Test API key
curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"

# If invalid, get new key from platform.openai.com
```

### Issue 5: Frontend Can't Connect

**Error:**
Browser console shows: `Failed to fetch` or `CORS error`

**Solution:**
```bash
# Check API is running
curl http://localhost:8000/v1/healthz

# Check CORS in .env
cat apps/api/.env | grep CORS_ORIGINS
# Should include: http://localhost:3000

# Check frontend .env.local
cat apps/web-app/.env.local | grep API_URL
# Should be: http://localhost:8000
```

### Issue 6: npm install fails

**Error:**
```
npm ERR! code ENOENT
```

**Solution:**
```bash
# Update npm
npm install -g npm@latest

# Clear cache
npm cache clean --force

# Remove and reinstall
cd apps/web-app
rm -rf node_modules package-lock.json
npm install
```

### Issue 7: Python version mismatch

**Error:**
```
Python 3.8 required, but 3.7 installed
```

**Solution:**
```bash
# Install Python 3.10+
brew install python@3.10  # macOS

# Or use pyenv
pyenv install 3.10.0
pyenv local 3.10.0

# Recreate venv
rm -rf venv
python -m venv venv
source venv/bin/activate
```

### Issue 8: Slow Response Times

**Symptom:**
API takes > 10 seconds to respond

**Solution:**
```bash
# Check if using fake adapter (fast)
grep "FakeAdapter" packages/search_core/search_core/ecommerce/price_compare.py

# If using real scraping, sites might be slow
# Add timeout in .env:
echo "QX_HTTPX_TIMEOUT=5.0" >> apps/api/.env

# Check logs for bottlenecks
grep "latency_ms" api.log
```

### Getting Help

If you're still stuck:

1. **Check logs** in both terminals
2. **Search documentation**: `README.md`, `ARCHITECTURE.md`, `develop_planning.md`
3. **Check CODE_INVENTORY.md** for file status
4. **Look at example code** in `packages/*/USAGE_EXAMPLE.py`
5. **Check API docs**: http://localhost:8000/docs

---

## Project Structure

```
quantumx-ai/
├── apps/
│   ├── api/                      # FastAPI Backend
│   │   ├── .env                  # ← Configuration (create this)
│   │   ├── requirements.txt      # ← Dependencies (create this)
│   │   └── src/
│   │       ├── main.py           # Entry point
│   │       ├── api/              # Routes & middleware
│   │       ├── config/           # Settings
│   │       ├── dependencies/     # DI providers
│   │       ├── router/           # Intent routing
│   │       └── orchestrator/     # Business logic
│   │
│   └── web-app/                  # Next.js Frontend
│       ├── .env.local            # ← Configuration (create this)
│       ├── package.json          # Dependencies
│       └── src/
│           ├── components/       # React components
│           ├── pages/            # Next.js pages
│           ├── hooks/            # Custom hooks
│           └── lib/              # Utilities
│
├── packages/                     # Core Packages
│   ├── agent_core/               # Agent orchestration
│   ├── search_core/              # Search & ranking
│   ├── decision_core/            # Scoring & explanation
│   ├── tools/                    # Tool registry
│   ├── llm_client/               # LLM integrations
│   ├── memory_core/              # Memory management
│   └── shared/                   # Shared utilities
│
├── scripts/                      # Helper scripts
│   ├── start-api.sh              # ← Create this
│   └── start-frontend.sh         # ← Create this
│
├── infra/                        # Infrastructure
│   └── docker-compose.yml        # Docker config
│
├── venv/                         # Python virtual env (create this)
│
├── develop_planning.md           # Development roadmap
├── CODE_INVENTORY.md             # File inventory
├── ARCHITECTURE.md               # Architecture docs
└── RUN_GUIDE.md                  # This file
```

---

## Next Steps

### After Getting It Running

**Phase 0 - Complete Critical Fixes:**
1. Fix syntax errors in `smart_buyer.py` (see develop_planning.md)
2. Fix import errors in `llm_provider.py`
3. Create `fake_adapter.py` for testing
4. Verify all health checks pass

**Phase A - End-to-End Integration:**
1. Connect fake adapter to price comparison
2. Test tool registry
3. Add observability (request ID, metrics)
4. Run E2E tests with 3-5 queries
5. Verify frontend integration

**Phase B - Real Features:**
1. Add real site scraping (Tiki first)
2. Add LLM-powered explanations
3. Add Redis caching
4. Improve error handling

**Phase C - Production Ready:**
1. Add Docker deployment
2. Add CI/CD pipeline
3. Add comprehensive tests
4. Add monitoring & logging

### Learning Resources

**Documentation:**
- `ARCHITECTURE.md` - System design
- `develop_planning.md` - Implementation plan
- `CODE_INVENTORY.md` - File status
- `DATAFLOW.md` - Data flow diagrams

**Code Examples:**
- `packages/agent_core/USAGE_EXAMPLE.py`
- API docs: http://localhost:8000/docs
- Frontend README: `apps/web-app/README.md`

**External Resources:**
- FastAPI: https://fastapi.tiangolo.com
- Next.js: https://nextjs.org/docs
- OpenAI: https://platform.openai.com/docs
- Pydantic: https://docs.pydantic.dev

---

## Support

### Quick Commands Reference Card

Save this for quick reference:

```bash
# Activate environment
source venv/bin/activate
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Start services
./scripts/start-api.sh
./scripts/start-frontend.sh

# Health checks
curl http://localhost:8000/v1/healthz
curl http://localhost:8000/v1/readyz

# Test API
curl -X POST http://localhost:8000/v1/smart-buyer \
  -H "Content-Type: application/json" \
  -d '{"query": "iPhone 15", "top_k": 5}'

# Access points
# Frontend: http://localhost:3000
# API Docs: http://localhost:8000/docs
# Health: http://localhost:8000/v1/healthz
```

---

**Last Updated**: November 18, 2025  
**Version**: 1.0  
**For**: MVP Development

For detailed development planning, see `develop_planning.md`  
For architecture details, see `ARCHITECTURE.md`  
For file status, see `CODE_INVENTORY.md`

