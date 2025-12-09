# QuantumX AI - Web App

Modern Next.js web application for QuantumX AI assistant.

## Features

- 🗨️ **Multi-Session Chat** - Create and manage multiple chat conversations
- 💬 **Real-time Streaming** - Streaming responses with Server-Sent Events
- 🛍️ **Smart Shopping** - E-commerce search with price comparison
- 🔬 **Deep Research** - In-depth analysis with multi-step reasoning
- 💾 **Persistent Storage** - LocalStorage-based history
- 🎨 **Modern UI** - Clean, responsive interface with Tailwind CSS
- ⚡ **Fast & Lightweight** - Optimized Next.js with TypeScript

## Tech Stack

- **Framework**: Next.js 14
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: React Hooks
- **API**: REST with SSE streaming
- **Storage**: localStorage

## Project Structure

```
src/
├── components/          # React components
│   ├── ChatWindow.tsx   # Main chat interface
│   ├── ChatInput.tsx    # Message input
│   ├── ChatList.tsx     # Session list
│   ├── Sidebar.tsx      # Navigation sidebar
│   ├── MessageBubble.tsx # Message display
│   └── NewChatButton.tsx # Create chat button
├── hooks/               # Custom React hooks
│   ├── useChat.ts       # Per-session chat state
│   ├── useChatHistory.ts # Session management
│   └── useStream.ts     # SSE streaming
├── lib/                 # Utilities
│   ├── api.ts           # API client
│   ├── storage.ts       # localStorage wrapper
│   └── config.ts        # Configuration
├── pages/               # Next.js pages
│   ├── index.tsx        # Home page
│   ├── chat/[id].tsx    # Chat session page
│   └── admin.tsx        # Admin panel
├── types/               # TypeScript types
│   └── chat.ts          # Chat types
└── styles/              # CSS
    └── globals.css      # Global styles
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm/yarn/pnpm
- Backend API running on `http://localhost:8000`

### Installation

```bash
# Install dependencies
npm install

# Create environment file
cp .env.local.example .env.local

# Edit .env.local with your API URL
# NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
```

### Development

```bash
# Run development server
npm run dev

# Open browser
open http://localhost:3000
```

### Build

```bash
# Build for production
npm run build

# Start production server
npm start
```

## Key Features

### Multi-Session Chat

Each chat session has its own:
- Unique ID (UUID)
- Message history (localStorage)
- Title (auto-generated from first message)
- Timestamp

```typescript
// Create new session
const { createNew } = useChatHistory();
const session = createNew("My Chat");

// Navigate to session
router.push(`/chat/${session.id}`);
```

### Streaming Responses

Real-time streaming with Server-Sent Events:

```typescript
// Send message with streaming
const stream = await sendMessage({
  message: "So sánh giá iPhone 15",
  sessionId: session.id
});

// Process chunks
for await (const chunk of stream) {
  if (chunk.type === "content") {
    // Update UI with streaming content
    setStreamingMessage(prev => prev + chunk.content);
  }
}
```

### Per-Session Storage

Messages are stored per session:

```typescript
// Storage key pattern
const KEY = `qx.chat.history.${sessionId}`;

// Load messages
const messages = storage.get<Message[]>(KEY, []);

// Save messages
storage.set(KEY, [...messages, newMessage]);
```

## API Integration

### Endpoints

```typescript
// Chat endpoint (auto-routing)
POST /v1/chat
{
  "message": "Your query",
  "sessionId": "session-uuid",
  "context": {}
}

// Smart Buyer endpoint
POST /v1/smart-buyer
{
  "message": "Compare prices...",
  "sessionId": "session-uuid",
  "context": {
    "sites": ["shopee", "lazada", "tiki"]
  }
}

// Deep Research endpoint
POST /v1/deep-research
{
  "message": "Research topic...",
  "sessionId": "session-uuid"
}
```

### Response Format

```typescript
{
  "response": "Generated response text",
  "type": "smart_buyer",
  "intent": "compare",
  "flow_type": "smart_buyer",
  "session_id": "session-uuid",
  "top_recommendations": [...],
  "explanation": {...},
  "metadata": {...}
}
```

### Streaming Format (SSE)

```
data: {"type":"content","content":"Hello"}
data: {"type":"content","content":" world"}
data: {"type":"metadata","data":{...}}
data: [DONE]
```

## Components

### ChatWindow

Main chat interface with messages and input.

```tsx
<ChatWindow sessionId="session-uuid" />
```

### Sidebar

Navigation with chat list and new chat button.

```tsx
<Sidebar />
```

### MessageBubble

Individual message display with metadata.

```tsx
<MessageBubble 
  message={message} 
  isStreaming={false} 
/>
```

## Hooks

### useChat

Manages per-session chat state:

```typescript
const {
  messages,        // Message history
  streamingMessage, // Currently streaming
  isLoading,       // Loading state
  error,           // Error message
  send,            // Send message
  cancel,          // Cancel request
  clear,           // Clear history
  retry            // Retry last message
} = useChat(sessionId);
```

### useChatHistory

Manages chat sessions:

```typescript
const {
  sessions,        // All sessions
  createNew,       // Create session
  remove,          // Delete session
  updateTitle,     // Update title
  getSession       // Get by ID
} = useChatHistory();
```

## Styling

Uses Tailwind CSS with custom theme:

```css
/* Blue gradient for primary actions */
bg-gradient-to-r from-blue-600 to-purple-600

/* Clean borders */
border border-gray-200

/* Hover effects */
hover:bg-gray-100 transition-colors
```

## Environment Variables

```bash
# Required
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

# Optional
NEXT_PUBLIC_ENABLE_STREAMING=true
NEXT_PUBLIC_ENABLE_MULTI_SESSION=true
```

## Browser Support

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

## Performance

- Initial load: ~200KB
- Time to Interactive: < 2s
- Lighthouse Score: 95+

## Security

- XSS protection via React
- CSRF tokens (TODO)
- Rate limiting (backend)
- Input validation

## Troubleshooting

### API Connection Issues

```bash
# Check API is running
curl http://localhost:8000/health

# Check CORS settings
# Backend must allow http://localhost:3000
```

### LocalStorage Issues

```bash
# Clear storage
localStorage.clear()

# Check storage size
console.log(JSON.stringify(localStorage).length)
```

### Build Errors

```bash
# Clear cache
rm -rf .next

# Reinstall dependencies
rm -rf node_modules package-lock.json
npm install
```

## Future Enhancements

- [ ] Voice input
- [ ] Image upload
- [ ] Export conversations
- [ ] Dark mode
- [ ] Mobile app
- [ ] PWA support
- [ ] Collaborative chat
- [ ] Search within chats

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Create Pull Request

## License

MIT License - see LICENSE file for details
