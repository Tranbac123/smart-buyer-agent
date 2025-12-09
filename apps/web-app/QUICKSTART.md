# Quick Start Guide

## 🚀 Get QuantumX Web App Running in 5 Minutes

### Prerequisites

- Node.js 18+ installed
- Backend API running on `localhost:8000`

---

## Step 1: Install Dependencies

```bash
cd apps/web-app
npm install
```

This installs:
- Next.js 14
- React 18
- TypeScript 5

---

## Step 2: Configure Environment

```bash
# Create environment file
cp .env.local.example .env.local

# Edit if needed (default is fine for local dev)
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

---

## Step 3: Start Development Server

```bash
npm run dev
```

You should see:
```
ready - started server on 0.0.0.0:3000, url: http://localhost:3000
```

---

## Step 4: Open Browser

```bash
open http://localhost:3000
```

Or navigate to: **http://localhost:3000**

---

## 🎯 First Steps

### 1. **Landing Page**
- Click **"Start Chatting"** to create your first chat

### 2. **Chat Interface**
- Type a message in the input box
- Press **Enter** or click **Send**
- Watch the streaming response!

### 3. **Try Different Queries**

**Shopping Query:**
```
So sánh giá iPhone 15 trên Shopee và Lazada
```
→ Triggers Smart Buyer flow

**Research Query:**
```
Nghiên cứu về AI agents
```
→ Triggers Deep Research flow

**General Chat:**
```
Xin chào, bạn là ai?
```
→ Triggers Chat flow

---

## 🔧 Troubleshooting

### API Connection Failed

**Problem:** Can't connect to backend

**Solution:**
```bash
# 1. Check backend is running
curl http://localhost:8000/health

# 2. Check CORS is configured
# Backend must allow: http://localhost:3000

# 3. Check API URL in .env.local
cat .env.local
```

### Port Already in Use

**Problem:** Port 3000 is busy

**Solution:**
```bash
# Run on different port
PORT=3001 npm run dev

# Or kill existing process
lsof -ti:3000 | xargs kill
```

### Dependencies Error

**Problem:** npm install fails

**Solution:**
```bash
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

### TypeScript Errors

**Problem:** Type errors in editor

**Solution:**
```bash
# Restart TypeScript server in VSCode
# Cmd+Shift+P → "TypeScript: Restart TS Server"

# Or rebuild
npm run build
```

---

## 📂 Project Structure

```
apps/web-app/
├── src/
│   ├── components/     # React components
│   ├── hooks/          # Custom hooks
│   ├── lib/            # Utilities
│   ├── pages/          # Next.js pages
│   ├── types/          # TypeScript types
│   └── styles/         # CSS
├── public/             # Static files
├── package.json
├── tsconfig.json
└── .env.local         # Your config
```

---

## 🎨 Example Queries to Try

### Smart Shopping
```
Tìm laptop gaming giá rẻ tốt nhất
Compare prices for AirPods Pro
So sánh tai nghe bluetooth dưới 1 triệu
```

### Deep Research
```
Nghiên cứu về Large Language Models
Phân tích xu hướng e-commerce 2024
What are the latest developments in AI?
```

### General Chat
```
Xin chào
Tell me a joke
Bạn có thể giúp gì cho tôi?
```

---

## 💡 Pro Tips

### 1. **Multiple Chat Sessions**
- Click **"+ New Chat"** to create separate conversations
- Each session has its own history
- Switch between sessions in the sidebar

### 2. **Keyboard Shortcuts**
- **Enter**: Send message
- **Shift+Enter**: New line
- Auto-resize text area

### 3. **Delete Sessions**
- Hover over a session in the list
- Click the **delete icon** that appears
- Confirmation required

### 4. **Streaming**
- Responses stream in real-time
- See text as it's generated
- Cancel anytime with stop button

### 5. **Persistent History**
- All chats saved to localStorage
- Survives page refresh
- No login required (for now)

---

## 🔄 Development Workflow

```bash
# Start development
npm run dev

# Make changes
# → Hot reload automatically

# Build for production
npm run build

# Test production build
npm start
```

---

## 📊 What Happens Under the Hood

```
1. User sends message
   ↓
2. useChat.send() called
   ↓
3. API request to backend
   POST /v1/chat with { message, sessionId }
   ↓
4. Backend processes:
   - Router detects intent
   - Selects flow (Smart Buyer/Research/Chat)
   - Orchestrator executes
   - Streams response
   ↓
5. Frontend receives SSE stream:
   data: {"type":"content","content":"Hello"}
   data: {"type":"content","content":" world"}
   ↓
6. UI updates in real-time
   ↓
7. Save to localStorage
   Key: qx.chat.history.{sessionId}
```

---

## 🎯 Next Steps

1. ✅ **App is running** - You're done with setup!

2. 🧪 **Test Features**
   - Create multiple chats
   - Try different query types
   - Test streaming
   - Delete sessions

3. 🎨 **Customize**
   - Edit `tailwind.config.js` for colors
   - Modify `components/` for UI
   - Update `lib/api.ts` for endpoints

4. 🚀 **Deploy**
   - Vercel: `vercel deploy`
   - Netlify: `netlify deploy`
   - Docker: Use Next.js Docker

---

## 🆘 Still Having Issues?

### Check These:

1. **Backend Running?**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Correct Node Version?**
   ```bash
   node --version  # Should be 18+
   ```

3. **Dependencies Installed?**
   ```bash
   ls node_modules | wc -l  # Should be 100+
   ```

4. **Environment Variables Set?**
   ```bash
   cat .env.local
   ```

5. **Port Available?**
   ```bash
   lsof -i:3000
   ```

---

## 📚 Learn More

- **README.md** - Full documentation
- **WEB_APP_SUMMARY.md** - Implementation details
- **src/components/** - Component examples
- **src/hooks/** - Hook usage

---

## ✅ Success Checklist

- [ ] Dependencies installed (`npm install`)
- [ ] Environment configured (`.env.local`)
- [ ] Dev server running (`npm run dev`)
- [ ] Backend API accessible (`curl localhost:8000/health`)
- [ ] Browser open (`localhost:3000`)
- [ ] First chat created
- [ ] Message sent successfully
- [ ] Streaming working

---

**If all checks pass, you're ready to use QuantumX AI!** 🎉

---

## 🎊 Enjoy!

You now have a **full-featured AI chat application** with:
- ✅ Multi-session support
- ✅ Real-time streaming
- ✅ Persistent history
- ✅ Modern UI
- ✅ Smart routing (Shopping/Research/Chat)

**Happy chatting!** 💬🚀

