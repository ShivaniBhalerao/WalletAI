# Quick Start: Use This Prompt with Cursor AI

## HOW TO USE THIS DOCUMENT WITH CURSOR

### Option 1: Copy & Paste to Cursor (Recommended for MVP)
1. **Open Cursor** in your project directory
2. **Create a new Composer chat** (⌘+I or Ctrl+I)
3. **Paste this prompt:**

```
You are an expert Full-Stack AI Engineer. Your task is to implement a production-ready chat UI for a financial assistant MVP.

CONTEXT:
- Using FastAPI full-stack starter project
- Backend: FastAPI running on http://localhost:8000
- Frontend: Next.js running on http://localhost:3000
- Tech stack: Vercel AI SDK 5, Next.js 15, Tailwind CSS, TypeScript

YOUR TASK:
Follow the detailed instructions in "AI-Friendly-Chat-UI-Prompt.md" to implement:

PHASE 1: Dependencies & Setup (30 min)
- Install @ai-sdk/react, @vercel/ai, ai packages
- Create TypeScript types for chat (ChatMessage, StreamResponse, etc.)

PHASE 2: Chat UI Components (1.5 hours)
- Create Message.tsx (displays user/assistant messages with styling)
- Create LoadingIndicator.tsx (animated dots while waiting)
- Create FinancialChat.tsx (main component using useChat hook)
- Create chat page route (/chat)

PHASE 3: Backend Integration (1.5 hours)
- Verify FastAPI chat endpoint exists at POST /api/chat
- Endpoint must accept {"messages": [...]} and stream NDJSON responses
- Update chat agent to support async streaming
- Configure CORS to allow localhost:3000

PHASE 4: Environment Configuration (15 min)
- Create frontend/.env.local with NEXT_PUBLIC_API_URL=http://localhost:8000
- Ensure backend/.env has ANTHROPIC_API_KEY and JWT_SECRET

PHASE 5: Testing (1 hour)
- Start backend: python -m uvicorn main:app --reload --port 8000
- Start frontend: npm run dev
- Navigate to http://localhost:3000/chat
- Test sending messages and verify streaming responses

PHASE 6: Production Touches (30 min)
- Add error boundary around chat component
- (Optional) Add message persistence via localStorage
- (Optional) Add typing indicators

REQUIREMENTS:
✓ Streaming token-by-token responses (NDJSON format)
✓ JWT authentication from localStorage
✓ Responsive design (mobile-first with Tailwind)
✓ Error handling for auth failures and API errors
✓ Loading states and typing indicators
✓ TypeScript types for type safety
✓ CORS configured correctly
✓ Fintech aesthetic (teal colors, professional design)

DELIVERABLES:
1. Complete chat UI components (frontend/components/chat/)
2. Chat page route (frontend/app/chat/page.tsx or pages/chat.tsx)
3. FastAPI chat endpoint with streaming (backend/routes/chat.py)
4. Environment variables configured (.env files)
5. Error boundary and production-ready touches
6. Working demo at http://localhost:3000/chat

INSTRUCTIONS:
- Reference "AI-Friendly-Chat-UI-Prompt.md" for detailed implementation steps
- Follow the 6 phases in order
- Use the exact code examples provided (they're tested)
- Run the testing checklist to verify everything works
- Ask clarifying questions if any step is unclear
- Implement full code, not pseudocode

START NOW: Begin with Phase 1 (Dependencies). Create each file and component exactly as specified in the prompt document.
```

4. **Cursor will then:**
   - Read the entire chat UI prompt document
   - Implement each phase sequentially
   - Create all necessary files
   - Provide working code immediately

### Option 2: Add File to Cursor (Most Efficient)
1. Save the prompt document as `CHAT_UI_BUILD_INSTRUCTIONS.md`
2. In Cursor Composer, type: `@CHAT_UI_BUILD_INSTRUCTIONS.md`
3. Add task: "Implement the chat UI following this document"
4. Cursor will reference the file throughout the conversation

### Option 3: Use as System Prompt (Advanced)
Add to `.cursor/rules.md`:
```markdown
# Chat UI Build Rules

When building the financial chat UI:
1. Follow the phases in AI-Friendly-Chat-UI-Prompt.md exactly
2. Use Vercel AI SDK (useChat hook) for state management
3. Implement NDJSON streaming from FastAPI backend
4. Include JWT authentication from localStorage
5. Use Tailwind CSS for fintech styling (teal primary)
6. Add error boundaries and loading states
7. Test with both servers running before delivering
```

---

## EXPECTED CURSOR WORKFLOW

### Step 1: Cursor Reads Your Prompt
"I'll implement the financial chat UI using Vercel AI SDK. Let me start with Phase 1."

### Step 2: Creates Dependencies
Cursor will:
- Show npm install command
- Create TypeScript types file
- Verify package.json

### Step 3: Builds Components
Cursor will:
- Create Message.tsx with Tailwind styling
- Create LoadingIndicator.tsx with animations
- Create FinancialChat.tsx with useChat hook
- Create chat page route

### Step 4: Integrates Backend
Cursor will:
- Show FastAPI endpoint code for streaming
- Suggest chat agent updates
- Verify CORS configuration

### Step 5: Tests Everything
Cursor will:
- Provide testing checklist
- Troubleshoot common issues
- Verify streaming works

### Step 6: Polish & Deploy
Cursor will:
- Add error boundaries
- Suggest performance optimizations
- Provide deployment guidance

---

## CRITICAL POINTS FOR CURSOR

When using this prompt with an AI agent, emphasize:

1. **STREAMING IS ESSENTIAL**
   - Not just one response - token-by-token streaming
   - NDJSON format: `{"content": "token"}\n`
   - useChat hook handles this automatically

2. **JWT AUTHENTICATION**
   - Get token from `localStorage.getItem('auth_token')`
   - Pass in headers: `Authorization: Bearer ${token}`
   - Verify on backend with verify_jwt_token()

3. **API ENDPOINT FORMAT**
   - Request: `{"messages": [{"role": "user", "content": "..."}, ...]}`
   - Response: Streaming NDJSON (not JSON array)
   - Each line must be valid JSON

4. **CORS CONFIGURATION**
   - Must allow `http://localhost:3000`
   - Expose all headers
   - Enable credentials

5. **ERROR HANDLING**
   - Show error if no auth token
   - Display API errors to user
   - Gracefully handle connection issues

6. **RESPONSIVE DESIGN**
   - Mobile-first with Tailwind
   - Test on mobile (DevTools device emulation)
   - Use max-w-4xl for desktop constraints

---

## TIME BREAKDOWN

| Phase | Time | What You Get |
|-------|------|-------------|
| 1. Dependencies | 30 min | Packages installed, types created |
| 2. Components | 1.5 hrs | Full chat UI, fully styled |
| 3. Backend | 1.5 hrs | Streaming endpoint, agent updated |
| 4. Config | 15 min | .env files configured |
| 5. Testing | 1 hr | Working demo, verified |
| 6. Production | 30 min | Error boundary, polish |
| **TOTAL** | **~4.5 hours** | **Production-ready chat** |

---

## SUCCESS CRITERIA (For Cursor to Verify)

After implementing, verify:

- [ ] Chat page loads at `http://localhost:3000/chat`
- [ ] Can type message and send
- [ ] Response streams token-by-token (not all at once)
- [ ] Messages display with correct styling (user right, assistant left)
- [ ] Loading indicator shows while waiting
- [ ] Error message if JWT token missing
- [ ] Works on mobile (responsive)
- [ ] No console errors or warnings
- [ ] CORS requests succeed (check Network tab)
- [ ] Backend streaming works (check with curl)

---

## COMMON CURSOR MISTAKES TO AVOID

Tell Cursor to **NOT**:

❌ Use WebSockets (not needed, HTTP streaming is simpler)
❌ Implement custom streaming (useChat hook does it)
❌ Build chat from scratch (use Vercel AI components)
❌ Skip error handling (auth failures will happen)
❌ Use localStorage without checking (token might be missing)
❌ Ignore NDJSON format (frontend expects this exact format)
❌ Forget CORS (will fail in browser)
❌ Build without testing (test as you go)

---

## FILE CHECKLIST FOR CURSOR

By end of build, these files should exist:

```
frontend/
├── app/
│   └── chat/
│       └── page.tsx          ← Chat page route
├── components/
│   └── chat/
│       ├── FinancialChat.tsx    ← Main component
│       ├── Message.tsx           ← Message display
│       ├── LoadingIndicator.tsx  ← Loading state
│       └── ChatErrorBoundary.tsx ← Error handling
├── types/
│   └── chat.ts               ← TypeScript types
├── .env.local                ← Frontend env
└── package.json              ← With new deps

backend/
├── routes/
│   └── chat.py               ← Chat endpoint
├── agents/
│   └── chat_agent.py         ← Updated for streaming
├── main.py                   ← CORS configured
└── .env                      ← Backend env
```

---

## TESTING COMMAND FOR CURSOR

After implementation, run this to verify:

```bash
# Terminal 1: Backend
cd backend
python -m uvicorn main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend
npm run dev

# Terminal 3: Manual test
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TEST_TOKEN" \
  -d '{"messages": [{"role": "user", "content": "Hello"}]}'
# Should see NDJSON streaming response
```

---

## IF CURSOR GETS STUCK

Common blockers and solutions:

| Issue | Solution |
|-------|----------|
| "Module not found" | Run `npm install` in frontend directory |
| "Port already in use" | Change port or kill existing process |
| "CORS error" | Add http://localhost:3000 to CORSMiddleware |
| "401 Unauthorized" | Ensure JWT token in localStorage |
| "Response not streaming" | Add `streaming=True` to LLM |
| "useChat not found" | Verify @ai-sdk/react installed |
| "TypeScript errors" | Create types/chat.ts file |

---

## NEXT STEPS AFTER CHAT UI

Once Cursor finishes chat UI (should be done in ~4 hours):

1. **Report Generation UI** — Add page to display financial reports
2. **File Upload** — Add UI to upload CSV/JSON data
3. **Plaid Integration** — Connect to Plaid Sandbox API
4. **Authentication** — Implement login/signup pages
5. **Deployment** — Deploy to Vercel (frontend) + Railway (backend)

---

## FINAL INSTRUCTIONS FOR CURSOR

**Copy this into Cursor Composer:**

---

> You are an expert Full-Stack AI Engineer. Implement a financial chat UI for an MVP using the detailed instructions in "AI-Friendly-Chat-UI-Prompt.md". 
>
> Follow the 6 phases exactly, create all components with full code (not pseudocode), and test as you go. The goal is a production-ready chat interface that streams responses from a FastAPI backend in real-time.
>
> Start with Phase 1: Dependencies & Setup. Ask clarifying questions if needed, then proceed through each phase systematically.
>
> Reference the document for exact code examples, API formats, and testing procedures.

---

Good luck! Your chat UI will be ready in ~4 hours. 🚀
