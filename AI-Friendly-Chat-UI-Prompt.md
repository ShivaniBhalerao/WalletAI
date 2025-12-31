# AI-Friendly Prompt: Build Financial Chat UI with Vercel AI SDK

**Purpose:** This document provides detailed, step-by-step instructions for an AI agent (Claude, Cursor AI, or similar) to implement a production-ready chat interface for the Finance Assistant MVP.

**Context:** You're using the FastAPI full-stack starter project. This prompt assumes:
- Backend: FastAPI running on `http://localhost:8000`
- Frontend: Next.js running on `http://localhost:3000`
- Chat endpoint: `POST /api/chat` (FastAPI) that streams NDJSON responses
- Agent: LangChain chat agent available in `backend/agents/chat_agent.py`

---

## OVERVIEW

Build a financial chat UI using:
1. **Vercel AI SDK 5** (`@ai-sdk/react` hooks + `ai` package)
2. **Next.js** with TypeScript
3. **Tailwind CSS** for fintech-appropriate styling
4. **FastAPI streaming** backend (NDJSON format)
5. **JWT authentication** from localStorage

**Estimated time:** 4 hours

---

## PHASE 1: DEPENDENCIES & SETUP (30 minutes)

### Task 1.1: Install Dependencies
**What to do:**
In the `frontend` (Next.js) directory, install required packages:

```bash
npm install @ai-sdk/react @vercel/ai ai
npm install -D @types/node
```

**Why:** 
- `@ai-sdk/react` provides the `useChat` hook for managing chat state and streaming
- `@vercel/ai` provides the low-level streaming utilities
- `ai` package provides the core functionality

**Verify:** After installation, check that `package.json` shows these versions:
```json
{
  "dependencies": {
    "@ai-sdk/react": "latest",
    "@vercel/ai": "latest",
    "ai": "latest"
  }
}
```

### Task 1.2: Create TypeScript Types File
**What to do:**
Create `frontend/types/chat.ts`:

```typescript
// types/chat.ts
export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  createdAt: Date;
}

export interface StreamResponse {
  content: string;
  type?: 'text' | 'tool_call' | 'error';
  toolName?: string;
  toolInput?: Record<string, unknown>;
}

export interface ApiChatRequest {
  messages: Array<{
    role: 'user' | 'assistant';
    content: string;
  }>;
}

export interface ApiChatResponse {
  content: string;
}
```

**Why:** TypeScript types ensure the frontend and backend communicate correctly and prevent runtime errors.

---

## PHASE 2: CHAT UI COMPONENTS (1.5 hours)

### Task 2.1: Create Message Component
**What to do:**
Create `frontend/components/chat/Message.tsx`:

```typescript
import React from 'react';

interface MessageProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
}

export function Message({ role, content, timestamp }: MessageProps) {
  const isUser = role === 'user';

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`
          max-w-xs md:max-w-md lg:max-w-lg xl:max-w-2xl
          px-4 py-3 rounded-lg text-sm md:text-base
          ${
            isUser
              ? 'bg-gradient-to-r from-teal-500 to-teal-600 text-white rounded-br-none'
              : 'bg-slate-100 text-slate-900 border border-slate-200 rounded-bl-none'
          }
        `}
      >
        {/* Content */}
        <p className="whitespace-pre-wrap break-words">{content}</p>

        {/* Optional timestamp */}
        {timestamp && (
          <p
            className={`text-xs mt-1 ${
              isUser ? 'text-teal-100' : 'text-slate-500'
            }`}
          >
            {new Date(timestamp).toLocaleTimeString()}
          </p>
        )}
      </div>
    </div>
  );
}
```

**Why:**
- Clean, reusable component for displaying chat messages
- Tailwind styling matches fintech aesthetic (teal primary color)
- Responsive (works on mobile, tablet, desktop)
- Left-aligned for assistant, right-aligned for user

### Task 2.2: Create Loading Indicator Component
**What to do:**
Create `frontend/components/chat/LoadingIndicator.tsx`:

```typescript
export function LoadingIndicator() {
  return (
    <div className="flex gap-1 items-center">
      <div className="w-2 h-2 bg-teal-500 rounded-full animate-bounce"></div>
      <div
        className="w-2 h-2 bg-teal-500 rounded-full animate-bounce"
        style={{ animationDelay: '0.2s' }}
      ></div>
      <div
        className="w-2 h-2 bg-teal-500 rounded-full animate-bounce"
        style={{ animationDelay: '0.4s' }}
      ></div>
    </div>
  );
}
```

**Why:** Visual feedback while waiting for agent response. Reassures user the system is processing.

### Task 2.3: Create Main Chat Component
**What to do:**
Create `frontend/components/chat/FinancialChat.tsx`:

```typescript
'use client'; // Enable client-side rendering in Next.js App Router

import { useChat } from '@ai-sdk/react';
import { useState, useEffect } from 'react';
import { Message } from './Message';
import { LoadingIndicator } from './LoadingIndicator';

interface FinancialChatProps {
  userId?: string;
}

export function FinancialChat({ userId }: FinancialChatProps) {
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Get JWT token from localStorage on mount
  useEffect(() => {
    const storedToken = localStorage.getItem('auth_token');
    if (!storedToken) {
      setError('Authentication required. Please log in first.');
      return;
    }
    setToken(storedToken);
  }, []);

  // Initialize useChat hook with custom API endpoint
  const { messages, input, handleInputChange, handleSubmit, isLoading } =
    useChat({
      // CRITICAL: Point to your FastAPI backend chat endpoint
      api: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/chat`,
      headers: {
        Authorization: token ? `Bearer ${token}` : '',
        'Content-Type': 'application/json',
      },
      // Ensure messages are in the correct format for FastAPI
      sendExtraMessageFields: true,
    });

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-center">
          <p className="text-red-600 font-medium">{error}</p>
          <button
            onClick={() => window.location.href = '/login'}
            className="mt-4 bg-teal-600 text-white px-4 py-2 rounded-lg hover:bg-teal-700"
          >
            Go to Login
          </button>
        </div>
      </div>
    );
  }

  if (!token) {
    return (
      <div className="flex items-center justify-center h-screen bg-slate-50">
        <div className="text-slate-500">Loading authentication...</div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white border-b border-slate-200 shadow-sm p-4 md:p-6">
        <div className="max-w-4xl mx-auto">
          <h1 className="text-2xl md:text-3xl font-bold text-slate-900">
            💰 Financial Assistant
          </h1>
          <p className="text-sm md:text-base text-slate-600 mt-1">
            Ask about your spending, trends, and financial insights
          </p>
        </div>
      </header>

      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-4xl mx-auto space-y-4">
          {/* Empty State */}
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="text-5xl mb-4">💼</div>
                <h2 className="text-xl md:text-2xl font-semibold text-slate-900 mb-2">
                  Start your financial conversation
                </h2>
                <p className="text-slate-600 mb-4">
                  Try asking:
                </p>
                <div className="space-y-2 text-left inline-block">
                  <p className="text-slate-700">• How much did I spend on groceries last month?</p>
                  <p className="text-slate-700">• What's my highest spending category?</p>
                  <p className="text-slate-700">• Compare my spending this month vs last month</p>
                </div>
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.map((msg) => (
            <Message
              key={msg.id}
              role={msg.role as 'user' | 'assistant'}
              content={msg.content}
            />
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-slate-100 px-4 py-3 rounded-lg">
                <LoadingIndicator />
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Input Form */}
      <form
        onSubmit={handleSubmit}
        className="bg-white border-t border-slate-200 p-4 md:p-6 shadow-lg"
      >
        <div className="max-w-4xl mx-auto">
          <div className="flex gap-3">
            <input
              type="text"
              value={input}
              onChange={handleInputChange}
              disabled={isLoading}
              placeholder="Ask me about your finances..."
              className={`
                flex-1 px-4 py-3 border border-slate-300 rounded-lg
                focus:outline-none focus:ring-2 focus:ring-teal-500 focus:border-transparent
                disabled:bg-slate-100 disabled:cursor-not-allowed disabled:text-slate-500
                text-slate-900 placeholder-slate-400
                transition-all
              `}
              aria-label="Chat message input"
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className={`
                px-6 py-3 font-medium rounded-lg
                transition-all
                ${
                  isLoading || !input.trim()
                    ? 'bg-slate-300 text-slate-500 cursor-not-allowed'
                    : 'bg-teal-600 hover:bg-teal-700 text-white'
                }
              `}
              aria-label="Send message"
            >
              {isLoading ? 'Thinking...' : 'Send'}
            </button>
          </div>

          {/* Character count (optional) */}
          <p className="text-xs text-slate-500 mt-2">
            {input.length} / 500 characters
          </p>
        </div>
      </form>
    </div>
  );
}
```

**Why:**
- `useChat` hook automatically manages message history and streaming
- Custom API endpoint points to your FastAPI backend
- JWT token from localStorage included in every request
- Responsive design (mobile-first with Tailwind)
- Error handling for authentication failures
- Loading state prevents double-submission
- Empty state guides user on what to ask

### Task 2.4: Create Chat Page Route
**What to do:**
Create `frontend/app/chat/page.tsx` (if using App Router) or `frontend/pages/chat.tsx` (if using Pages Router):

**For App Router:**
```typescript
// app/chat/page.tsx
'use client';

import { FinancialChat } from '@/components/chat/FinancialChat';

export default function ChatPage() {
  return <FinancialChat />;
}
```

**For Pages Router:**
```typescript
// pages/chat.tsx
import { FinancialChat } from '@/components/chat/FinancialChat';

export default function ChatPage() {
  return <FinancialChat />;
}
```

**Why:** Makes the chat accessible at `/chat` route.

---

## PHASE 3: FASTAPI BACKEND INTEGRATION (1.5 hours)

### Task 3.1: Verify FastAPI Chat Endpoint Structure
**What to do:**
In your FastAPI backend, ensure you have a chat endpoint that:
1. Accepts POST requests with message history
2. Streams responses in NDJSON format (line-delimited JSON)
3. Each line is a JSON object with at minimum `{ "content": "string" }`

**Expected endpoint signature:**
```python
@router.post("/api/chat")
async def chat_endpoint(
    request: dict,  # or use Pydantic model
    authorization: str = Header(None)
) -> StreamingResponse:
    """
    Receives: {"messages": [{"role": "user", "content": "..."}, ...]}
    Streams: {"content": "token by token"}\n
    """
```

**Why:** The frontend's `useChat` hook expects NDJSON streaming format.

### Task 3.2: Create Chat Endpoint (if not exists)
**What to do:**
Create or update `backend/routes/chat.py`:

```python
from fastapi import APIRouter, HTTPException, Header
from fastapi.responses import StreamingResponse
from typing import Optional
import json
import asyncio
from agents.chat_agent import create_chat_agent
from utils.auth import verify_jwt_token
from db.queries import get_user_transactions

router = APIRouter(prefix="/api", tags=["chat"])

@router.post("/chat")
async def chat_endpoint(
    request: dict,
    authorization: Optional[str] = Header(None)
):
    """
    Chat endpoint for financial queries.
    
    Request body:
    {
        "messages": [
            {"role": "user", "content": "How much did I spend on groceries?"},
            {"role": "assistant", "content": "You spent $150 on groceries..."},
            {"role": "user", "content": "Any trends?"}
        ]
    }
    
    Streams NDJSON responses:
    {"content": "You"}\n
    {"content": " spent"}\n
    {"content": " $150"}\n
    ...
    """
    
    # 1. Verify authentication
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")
    
    try:
        user_id = verify_jwt_token(authorization.replace("Bearer ", ""))
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {str(e)}")
    
    # 2. Extract messages
    messages = request.get("messages", [])
    if not messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    user_message = messages[-1]["content"]
    
    # 3. Get user's financial data
    try:
        user_data = await get_user_transactions(user_id)
        if not user_data:
            raise HTTPException(
                status_code=404, 
                detail="No financial data found. Please upload your data first."
            )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error fetching user data: {str(e)}"
        )
    
    # 4. Create chat agent
    try:
        agent = create_chat_agent(user_data=user_data)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Error initializing agent: {str(e)}"
        )
    
    # 5. Stream response
    async def generate():
        try:
            # Execute agent with streaming
            full_response = ""
            
            # For token-by-token streaming, iterate through agent output
            async for token in agent.stream(
                input=user_message,
                config={"user_id": user_id, "chat_history": messages[:-1]}
            ):
                full_response += str(token)
                
                # Yield each token wrapped in JSON
                yield json.dumps({
                    "content": str(token),
                    "type": "text"
                }).encode() + b"\n"
            
            # Optional: Yield final summary
            yield json.dumps({
                "content": "",  # Empty to signal end
                "type": "complete"
            }).encode() + b"\n"
            
        except Exception as e:
            # Stream error response
            yield json.dumps({
                "content": f"Error: {str(e)}",
                "type": "error"
            }).encode() + b"\n"
    
    return StreamingResponse(
        generate(),
        media_type="application/x-ndjson",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
        }
    )
```

**Why:**
- Streaming response allows real-time message display (better UX)
- JWT verification secures the endpoint
- NDJSON format is what `useChat` hook expects
- Error handling prevents crashes
- Headers prevent proxy buffering issues

### Task 3.3: Update Chat Agent for Streaming
**What to do:**
Update `backend/agents/chat_agent.py` to ensure it supports async streaming:

```python
from langchain.agents import AgentExecutor, create_react_agent
from langchain_anthropic import ChatAnthropic
from langchain.tools import tool

async def create_chat_agent(user_data: dict):
    """
    Create a chat agent that streams token-by-token.
    
    Args:
        user_data: User's financial transactions and metadata
    
    Returns:
        AgentExecutor configured for streaming
    """
    
    # Define tools
    @tool
    async def get_spending_by_category(month: str) -> dict:
        """Get user's spending breakdown by category for a given month."""
        # Filter transactions for the month
        spending = {}
        for txn in user_data.get("transactions", []):
            if txn["month"] == month:
                cat = txn.get("category", "Other")
                spending[cat] = spending.get(cat, 0) + txn["amount"]
        return spending
    
    @tool
    async def get_total_spending(start_date: str, end_date: str) -> float:
        """Get total spending between two dates."""
        total = 0
        for txn in user_data.get("transactions", []):
            if start_date <= txn["date"] <= end_date:
                total += txn["amount"]
        return total
    
    @tool
    async def identify_merchants(category: str) -> list:
        """Get all merchants in a specific spending category."""
        merchants = set()
        for txn in user_data.get("transactions", []):
            if txn.get("category") == category:
                merchants.add(txn.get("merchant", "Unknown"))
        return sorted(list(merchants))
    
    tools = [
        get_spending_by_category,
        get_total_spending,
        identify_merchants,
    ]
    
    # Create LLM
    llm = ChatAnthropic(
        model="claude-3-5-sonnet-20241022",
        temperature=0.7,
        streaming=True,  # IMPORTANT: Enable streaming
    )
    
    # Create prompt
    prompt = """You are a financial advisor AI assistant. Analyze user financial data to provide insights.
    
User's financial data summary:
- Total transactions: {total_transactions}
- Date range: {date_range}
- Top spending categories: {top_categories}

Use the available tools to answer questions about spending patterns, trends, and recommendations.
Always be specific with numbers and cite the data you're referencing.
If you don't have the exact data, use the tools to find it.

When answering:
1. Use tool calls to retrieve specific data
2. Analyze the data for patterns
3. Provide actionable insights
4. Ask clarifying questions if needed"""
    
    # Create agent
    agent = create_react_agent(
        llm=llm,
        tools=tools,
        prompt=prompt,
    )
    
    # Create executor with streaming enabled
    executor = AgentExecutor.from_agent_and_tools(
        agent=agent,
        tools=tools,
        verbose=True,
        streaming=True,  # Enable streaming
        return_intermediate_steps=False,
    )
    
    return executor
```

**Why:**
- Streaming enabled on both LLM and executor
- Tools provide real data to agent
- Prompt guides agent behavior
- Executor handles tool calling + streaming

### Task 3.4: Configure CORS (Important!)
**What to do:**
In `backend/main.py`, ensure CORS is configured to allow requests from Next.js frontend:

```python
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Local development
        "http://localhost:3001",  # Alternative port
        # Add production domains here
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],  # Expose all headers
)
```

**Why:** Allows frontend to make requests to backend without CORS errors.

---

## PHASE 4: ENVIRONMENT CONFIGURATION (15 minutes)

### Task 4.1: Frontend Environment Variables
**What to do:**
Create or update `frontend/.env.local`:

```bash
# API Configuration
NEXT_PUBLIC_API_URL=http://localhost:8000

# Authentication
NEXT_PUBLIC_AUTH_ENABLED=true

# LLM Configuration
NEXT_PUBLIC_MODEL=claude-3-5-sonnet
```

**Why:**
- `NEXT_PUBLIC_API_URL` tells frontend where backend lives
- Frontend can access `NEXT_PUBLIC_*` variables in the browser
- Non-public variables are only available on the server

### Task 4.2: Backend Environment Variables
**What to do:**
Ensure `backend/.env` has:

```bash
# API Configuration
API_PORT=8000
API_HOST=0.0.0.0

# Database
DATABASE_URL=postgresql://user:password@localhost/finance_db

# LLM
ANTHROPIC_API_KEY=your_actual_api_key
LLM_MODEL=claude-3-5-sonnet-20241022

# JWT
JWT_SECRET=your_super_secret_key
JWT_ALGORITHM=HS256
JWT_EXPIRE_HOURS=24
```

**Why:** Separates config from code, enables environment-specific settings.

---

## PHASE 5: TESTING & DEBUGGING (1 hour)

### Task 5.1: Start Both Servers
**What to do:**
In two separate terminals:

**Terminal 1 (Backend):**
```bash
cd backend
python -m uvicorn main:app --reload --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

**Expected output:**
- Backend: `INFO:     Uvicorn running on http://0.0.0.0:8000`
- Frontend: `▲ Next.js 15.x.x` and `● ready - started server on 0.0.0.0:3000`

### Task 5.2: Manual Testing Flow
**What to do:**
1. Navigate to `http://localhost:3000/chat`
2. You should see the Financial Assistant header
3. Type a test message: "How much did I spend on groceries last month?"
4. Press Send
5. Watch as the response streams in token-by-token

**Expected behavior:**
- Message appears on the right (teal bubble)
- Loading indicator appears while agent thinks
- Assistant response appears on the left (gray bubble) with streaming tokens
- Input is disabled while loading

### Task 5.3: Debug Checklist
**If chat is not working, verify:**

```
□ Backend running on port 8000
  - Check: curl http://localhost:8000/docs (shows Swagger UI)

□ Frontend running on port 3000
  - Check: http://localhost:3000/chat loads without errors

□ JWT token available
  - Check: Open DevTools → Application → localStorage
  - Should see: "auth_token" key with a valid JWT

□ CORS configured
  - Check: Network tab in DevTools, look for CORS errors
  - If present: verify CORSMiddleware in backend/main.py

□ API endpoint exists
  - Check: curl -X POST http://localhost:8000/api/chat \
     -H "Content-Type: application/json" \
     -d '{"messages": [{"role": "user", "content": "test"}]}'
  - Should return streaming response (NDJSON)

□ Environment variables loaded
  - Frontend: console.log(process.env.NEXT_PUBLIC_API_URL)
  - Backend: print(os.getenv("ANTHROPIC_API_KEY"))

□ Chat agent initialized
  - Check backend logs for "Agent initialized" message
  - No import errors in chat_agent.py

□ Streaming works
  - Check Network tab → /api/chat → Response
  - Should see newline-delimited JSON objects
```

### Task 5.4: Common Issues & Solutions

**Issue: "404 Not Found" on `/api/chat`**
- Solution: Verify endpoint path in both frontend and backend matches
- Frontend: `api: "${NEXT_PUBLIC_API_URL}/api/chat"`
- Backend: `@router.post("/api/chat")`

**Issue: CORS error in console**
- Solution: Check CORSMiddleware configuration, ensure localhost:3000 is in allow_origins

**Issue: "Missing authorization header"**
- Solution: Check that JWT token exists in localStorage and is being sent
  - In FinancialChat.tsx, verify: `const token = localStorage.getItem('auth_token')`

**Issue: Response not streaming, comes all at once**
- Solution: Verify `streaming=True` is set on LLM and executor in backend
  - Check: `ChatAnthropic(..., streaming=True)`
  - Check: Agent executor created with streaming

**Issue: "Request timeout"**
- Solution: LLM call may be slow. Increase timeout in frontend useChat config:
  ```typescript
  const { messages, ... } = useChat({
    api: "...",
    timeout: 30000,  // 30 seconds
  });
  ```

---

## PHASE 6: PRODUCTION TOUCHES (30 minutes)

### Task 6.1: Add Error Boundary
**What to do:**
Create `frontend/components/chat/ChatErrorBoundary.tsx`:

```typescript
'use client';

import React, { ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ChatErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('Chat error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex items-center justify-center h-screen bg-slate-50">
          <div className="text-center max-w-md">
            <h2 className="text-2xl font-bold text-red-600 mb-2">
              Something went wrong
            </h2>
            <p className="text-slate-600 mb-4">{this.state.error?.message}</p>
            <button
              onClick={() => window.location.reload()}
              className="bg-teal-600 text-white px-4 py-2 rounded-lg hover:bg-teal-700"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
```

**Then wrap the chat component in your page:**
```typescript
// app/chat/page.tsx
import { ChatErrorBoundary } from '@/components/chat/ChatErrorBoundary';
import { FinancialChat } from '@/components/chat/FinancialChat';

export default function ChatPage() {
  return (
    <ChatErrorBoundary>
      <FinancialChat />
    </ChatErrorBoundary>
  );
}
```

### Task 6.2: Add Message Persistence (Optional)
**What to do:**
Store chat history in localStorage to survive page refresh:

```typescript
// In FinancialChat.tsx, after useChat initialization
useEffect(() => {
  // Save messages to localStorage whenever they change
  localStorage.setItem('chat_history', JSON.stringify(messages));
}, [messages]);

// Initialize with saved messages
const initialMessages = localStorage.getItem('chat_history')
  ? JSON.parse(localStorage.getItem('chat_history'))
  : [];

const { messages, ... } = useChat({
  api: "...",
  initialMessages: initialMessages,  // Load from localStorage
});
```

### Task 6.3: Add Typing Indicator on User Input
**What to do:**
In `FinancialChat.tsx`, update the input onChange to show typing state.

(This is already partially done with the `isLoading` state from `useChat`.)

### Task 6.4: Performance: Virtualize Long Message Lists (Advanced)
**What to do:**
For MVP, you don't need this, but for production with many messages, consider using `react-window` to virtualize the message list:

```bash
npm install react-window
```

Then replace the messages container with virtualized rendering.

**For MVP:** Skip this. Keep it simple.

---

## SUMMARY CHECKLIST

### Before Starting
- [ ] FastAPI backend running on port 8000
- [ ] Next.js frontend running on port 3000
- [ ] JWT token generation working (test on `/login` page)
- [ ] Chat agent implemented in backend

### Phase 1: Dependencies
- [ ] Installed `@ai-sdk/react`, `@vercel/ai`, `ai`
- [ ] Created TypeScript types file

### Phase 2: Chat UI Components
- [ ] Created `Message.tsx` component
- [ ] Created `LoadingIndicator.tsx` component
- [ ] Created `FinancialChat.tsx` (main component)
- [ ] Created chat page route (`app/chat/page.tsx` or `pages/chat.tsx`)

### Phase 3: Backend Integration
- [ ] Chat endpoint exists at `POST /api/chat`
- [ ] Endpoint accepts streaming NDJSON requests
- [ ] Endpoint verifies JWT tokens
- [ ] Chat agent initialized and working
- [ ] CORS configured for frontend domain

### Phase 4: Environment Configuration
- [ ] `.env.local` file created with `NEXT_PUBLIC_API_URL`
- [ ] Backend `.env` has `ANTHROPIC_API_KEY` and `JWT_SECRET`

### Phase 5: Testing
- [ ] Both servers start without errors
- [ ] Navigate to `/chat` page loads
- [ ] Can type message and send
- [ ] Response streams token-by-token
- [ ] Error handling works

### Phase 6: Production
- [ ] Error boundary wrapped around component
- [ ] (Optional) Message persistence via localStorage
- [ ] (Optional) Typing indicator visible

---

## TROUBLESHOOTING QUICK LINKS

If something breaks, check:
1. **Backend not responding:** Is Uvicorn running? Check port 8000
2. **CORS errors:** Are origins configured in CORSMiddleware?
3. **No streaming:** Is `streaming=True` set on LLM?
4. **Messages not displaying:** Check browser DevTools console for errors
5. **Token not sent:** Is JWT token in localStorage?

For more help:
- Vercel AI SDK docs: https://sdk.vercel.ai/docs
- FastAPI docs: https://fastapi.tiangolo.com
- LangChain docs: https://docs.langchain.com

---

## FINAL NOTES

- **Total time:** ~4 hours
- **Lines of code:** ~500 (frontend) + ~200 (backend)
- **Production readiness:** 85% (missing: rate limiting, analytics, refined error messages)
- **Next steps after this:** Add UI for report generation, then integrate Plaid data

Good luck! 🚀
