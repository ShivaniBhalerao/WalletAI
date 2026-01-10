# Financial Analyst AI Agent

This module implements a conversational AI agent using LangGraph and Google Gemini that acts as a financial analyst for WalletAI users.

## Architecture

The agent is built using LangGraph's state graph pattern with the following components:

### Core Components

- **`state.py`**: Defines the agent state structure (`FinancialAgentState`) that flows through the graph
- **`agent.py`**: Main agent implementation with graph construction and entry points
- **`nodes.py`**: Individual node functions that process state at each step
- **`prompts.py`**: System prompts and templates for the financial analyst persona
- **`config.py`**: Configuration management for API keys and model settings
- **`tools.py`**: Tool stubs for future database query integration

### Agent Flow

```
User Message → Analyze Intent → Check Clarification?
                                   ↓ Yes          ↓ No
                          Generate Clarification  Generate Response
                                   ↓                    ↓
                                Format Response ← ──────┘
                                   ↓
                            Stream to User (SSE)
```

### Nodes

1. **analyze_intent_node**: Extracts user intent and entities using Gemini
2. **generate_clarification_node**: Generates clarifying questions when needed
3. **generate_response_node**: Generates main financial analyst response
4. **format_response_node**: Formats final response for streaming

## Configuration

### Environment Variables

Required:
- `GOOGLE_API_KEY`: Google Gemini API key

Optional:
- `GEMINI_MODEL`: Model to use (default: `gemini-2.0-flash-exp`)
- `GEMINI_TEMPERATURE`: Temperature for generation (default: `0.7`)
- `GEMINI_MAX_TOKENS`: Max tokens in response (default: `2048`)

### Setup

1. Install dependencies:
```bash
cd backend
uv pip install -e .
```

2. Set API key:
```bash
export GOOGLE_API_KEY="your-api-key-here"
```

3. Run the application:
```bash
uvicorn app.main:app --reload
```

## Usage

### From Code

```python
import uuid
from langchain_core.messages import HumanMessage
from app.ai.agent import process_message, process_message_simple

# Simple interface
user_id = uuid.uuid4()
response = process_message_simple(
    user_id=user_id,
    message_text="How much did I spend on groceries?"
)
print(response)

# Full interface with conversation history
messages = [HumanMessage(content="Show my spending breakdown")]
result = process_message(user_id=user_id, messages=messages)
print(result["messages"][-1].content)
```

### Via API

The agent is integrated with the `/api/v1/chat` endpoint:

```bash
curl -X POST "http://localhost:8000/api/v1/chat" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "How much did I spend on groceries?"}
    ]
  }'
```

## Features

### Current Capabilities

✅ Natural language understanding of financial queries  
✅ Intent extraction (spending, comparison, category analysis, etc.)  
✅ Entity extraction (categories, amounts, time periods)  
✅ Clarifying questions when intent is unclear  
✅ Conversation context maintenance (in-memory)  
✅ Streaming responses via SSE  
✅ Mock data responses with realistic patterns  

### Future Enhancements

🔜 Database query integration via tools  
🔜 Vector DB for transaction search  
🔜 Multi-turn planning for complex queries  
🔜 Proactive insights based on spending patterns  
🔜 Budget tracking and recommendations  
🔜 Anomaly detection  

## Testing

Run tests:
```bash
cd backend
pytest tests/ai/ -v
```

Run tests with coverage:
```bash
pytest tests/ai/ --cov=app.ai --cov-report=html
```

Note: Most tests require `GOOGLE_API_KEY` to be set. Tests will skip if not available.

## Development

### Adding New Intents

1. Add intent to `INTENT_TYPES` in `state.py`
2. Update intent analysis prompt in `prompts.py`
3. Add handling logic in `generate_response_node` in `nodes.py`

### Adding Database Tools

1. Implement real query function in `tools.py`
2. Replace mock data returns with actual database queries
3. Update tests to use test database

### Modifying Agent Flow

1. Add new node function in `nodes.py`
2. Add node to graph in `build_financial_agent()` in `agent.py`
3. Add edges to connect the node
4. Update conditional routing if needed

## Logging

The module uses Python's standard logging. Configure logging level:

```python
import logging
logging.getLogger("app.ai").setLevel(logging.DEBUG)
```

All major operations are logged:
- Agent invocations
- Intent analysis results
- LLM calls and responses
- Errors and fallbacks

## Error Handling

The agent implements multiple levels of error handling:

1. **API Key Missing**: Validation fails gracefully, falls back to mock responses
2. **LLM Errors**: Catches exceptions, generates user-friendly error messages
3. **Invalid State**: Validates inputs, provides clear error messages
4. **Fallback Responses**: Always provides a response even if agent fails

## Performance

- **Response Time**: ~2-3 seconds with Gemini 2.0 Flash
- **Tokens**: Configured for max 2048 tokens output
- **Context Window**: Maintains last 10 messages for context
- **Streaming**: Tokens streamed word-by-word for better UX

## Security

- API keys loaded from environment variables only
- No credentials in code or logs
- User ID validation on all requests
- Rate limiting handled by FastAPI middleware

## License

Part of WalletAI project - see main LICENSE file.

