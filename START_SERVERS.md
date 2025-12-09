# 🚀 Start QuantumX AI Servers

## Quick Start

### Backend (Terminal 1)
```bash
cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai
source .venv/bin/activate
cd apps/api/src
uvicorn main:app --reload
```

Backend will run on: http://localhost:8000

### Frontend (Terminal 2)
```bash
cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai/apps/web-app
npm run dev
```

Frontend will run on: http://localhost:3000

---

## Current Status

✅ **Backend:** Running on PID 61498
✅ **Routes:** /v1/smart-buyer/chat endpoint working
✅ **Test:** `curl -X POST http://localhost:8000/v1/smart-buyer/chat -H "Content-Type: application/json" -d '{"message":"test","top_k":3}'`

⚠️ **Frontend:** Needs manual start (permission issue in background)

---

## Verify Both Running

```bash
# Check processes
ps aux | grep -E "(next-server|uvicorn)" | grep -v grep

# Test backend
curl http://localhost:8000/v1/ping

# Test frontend (after starting)
curl http://localhost:3000

# Test full integration
curl -X POST http://localhost:3000/api/smart-buyer/chat \
  -H "Content-Type: application/json" \
  -d '{"message":"laptop gaming","top_k":3}'
```

---

## 📝 Notes

- Backend: Đã fix conflict và đang hoạt động ✅
- Frontend: Cần start từ terminal user (không thể background vì permission)
- Code đã được commit và push lên GitHub ✅

---

## 🎯 Next Steps

1. Mở terminal mới
2. Chạy `cd /Users/tranvanbac/Documents/AI/ai-agent/quantumx-ai/apps/web-app`
3. Chạy `npm run dev`
4. Visit http://localhost:3000
5. Enjoy your ChatGPT-style UI! 🎉
