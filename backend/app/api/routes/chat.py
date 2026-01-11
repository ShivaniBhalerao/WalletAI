"""
Chat endpoint for the Financial Assistant
Provides streaming NDJSON responses for real-time chat experience
"""

import asyncio
import json
import logging
import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from pydantic import BaseModel

from app.ai.agent import process_message
from app.ai.config import AIConfig
from app.api.deps import CurrentUser, SessionDep

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(tags=["chat"])


class ChatMessage(BaseModel):
    """Single message in a chat conversation
    Supports both formats:
    - AI SDK format: {"role": "user", "parts": [{"type": "text", "text": "..."}]}
    - Simple format: {"role": "user", "content": "..."}
    """
    role: str
    content: str | None = None
    parts: list[dict[str, Any]] | None = None
    
    def get_content(self) -> str:
        """Extract text content from either format"""
        if self.content:
            return self.content
        if self.parts:
            # Extract text from parts array (AI SDK format)
            text_parts = [
                part.get("text", "") 
                for part in self.parts 
                if isinstance(part, dict) and part.get("type") == "text"
            ]
            return "".join(text_parts)
        return ""


class ChatRequest(BaseModel):
    """Request body for chat endpoint"""
    messages: list[ChatMessage]


async def generate_agent_response(
    user_message: str, 
    user_id: uuid.UUID,
    session: SessionDep,
    conversation_history: list[ChatMessage] | None = None
) -> str:
    """
    Generate response using the LangGraph agent
    
    Args:
        user_message: The user's input message
        user_id: The authenticated user's UUID
        session: Database session for querying financial data
        conversation_history: Optional conversation history for context
        
    Returns:
        Agent's response string
    """
    logger.info(f"Generating agent response for user {user_id}: {user_message[:50]}...")
    
    try:
        # Check if AI is configured
        if not AIConfig.validate_config():
            logger.warning("AI not configured, falling back to mock response")
            #return await generate_mock_response(user_message, user_id)
        
        # Convert conversation history to LangChain messages
        messages = []
        if conversation_history:
            for msg in conversation_history[-AIConfig.MAX_CONVERSATION_HISTORY:]:
                content = msg.get_content()
                if msg.role == "user":
                    messages.append(HumanMessage(content=content))
                elif msg.role == "assistant":
                    messages.append(AIMessage(content=content))
        
        # Add current message if not already in history
        if not messages or messages[-1].content != user_message:
            messages.append(HumanMessage(content=user_message))
        
        # Process through agent with database session
        result = process_message(
            user_id=user_id,
            messages=messages,
            session=session
        )
        
        # Extract response
        if result["messages"]:
            response = result["messages"][-1].content
            logger.info(f"Agent response generated: {len(response)} characters")
            return response
        else:
            logger.error("No response from agent")
            return "I apologize, but I couldn't generate a response. Please try again."
            
    except Exception as e:
        logger.error(f"Error generating agent response: {e}", exc_info=True)
        # Fallback to mock response on error
        logger.info("Falling back to mock response due to error")
      #  return await generate_mock_response(user_message, user_id)


async def generate_mock_response(user_message: str, user_id: uuid.UUID) -> str:
    """
    Generate a mock response based on the user's message
    In production, this would call the LangChain agent with user data
    
    Args:
        user_message: The user's input message
        user_id: The authenticated user's ID
        
    Returns:
        Mock response string
    """
    logger.info(f"Generating response for user {user_id}: {user_message[:50]}...")
    
    # Mock responses based on keywords
    message_lower = user_message.lower()
    
    if "groceries" in message_lower or "grocery" in message_lower:
        return (
            "Based on your transaction history, you spent approximately $342.50 "
            "on groceries last month. This represents about 18% of your total spending. "
            "Your main grocery stores were Whole Foods ($180), Trader Joe's ($95), "
            "and local markets ($67.50). Would you like to see a detailed breakdown?"
        )
    elif "category" in message_lower or "categories" in message_lower:
        return (
            "Here's your spending breakdown by category:\n\n"
            "🏠 Housing: $1,850 (42%)\n"
            "🚗 Transportation: $450 (10%)\n"
            "🍕 Food & Dining: $680 (15%)\n"
            "🛍️ Shopping: $320 (7%)\n"
            "💡 Utilities: $280 (6%)\n"
            "🎬 Entertainment: $240 (5%)\n"
            "💰 Other: $680 (15%)\n\n"
            "Your highest spending category is Housing at $1,850."
        )
    elif "compare" in message_lower or "comparison" in message_lower:
        return (
            "Comparing your spending:\n\n"
            "📊 This month: $4,215\n"
            "📊 Last month: $3,890\n\n"
            "You've spent $325 more this month (8.4% increase).\n\n"
            "Main differences:\n"
            "• Shopping increased by $180\n"
            "• Entertainment increased by $95\n"
            "• Utilities increased by $50\n\n"
            "Would you like tips on reducing spending in these categories?"
        )
    elif "save" in message_lower or "saving" in message_lower:
        return (
            "Great question about savings! 💰\n\n"
            "Based on your spending patterns, here are some recommendations:\n\n"
            "1. Reduce dining out by 20% → Save $136/month\n"
            "2. Cancel unused subscriptions → Save $45/month\n"
            "3. Shop sales for groceries → Save $50/month\n\n"
            "Total potential savings: $231/month or $2,772/year!\n\n"
            "Would you like specific tips for any category?"
        )
    else:
        return (
            f"I understand you're asking about: '{user_message}'. "
            "I'm your financial assistant and I can help you analyze your spending patterns, "
            "compare expenses across time periods, identify saving opportunities, and more. "
            "\n\nTry asking me about:\n"
            "• Specific spending categories (e.g., 'How much did I spend on groceries?')\n"
            "• Spending comparisons (e.g., 'Compare this month vs last month')\n"
            "• Saving tips (e.g., 'How can I save money?')\n"
            "• Category breakdowns (e.g., 'Show me my spending by category')"
        )


async def stream_response_generator(
    user_message: str, 
    user_id: uuid.UUID,
    session: SessionDep,
    conversation_history: list[ChatMessage] | None = None
):
    """
    Generate streaming NDJSON response in AI SDK format
    Yields chunks of JSON objects, each on a new line
    
    The AI SDK expects UIMessageChunk format:
    - text-start: Initial chunk with message id
    - text-delta: Text content chunks with delta
    - text-done: Final chunk to signal completion
    
    Args:
        user_message: The user's input message
        user_id: The authenticated user's ID
        session: Database session for querying financial data
        
    Yields:
        JSON chunks in NDJSON format (newline-delimited JSON)
    """
    try:
        # Generate the full response using agent
        full_response = await generate_agent_response(user_message, user_id, session, conversation_history)
        
        # Generate a unique message ID
        message_id = str(uuid.uuid4())
        
        # Send text-start chunk (SSE format: data: prefix)
        start_data = json.dumps({
            "type": "text-start",
            "id": message_id
        })
        yield f"data: {start_data}\n\n".encode('utf-8')
        
        # Stream the response token by token (word by word for better effect)
        words = full_response.split(" ")
        
        for i, word in enumerate(words):
            # Add space before word (except for the first one)
            token = word if i == 0 else f" {word}"
            
            # Yield text-delta chunks (SSE format)
            delta_data = json.dumps({
                "type": "text-delta",
                "delta": token,
                "id": message_id
            })
            yield f"data: {delta_data}\n\n".encode('utf-8')
            
            # Small delay to simulate streaming (remove in production with real LLM)
            await asyncio.sleep(0.05)
        
        # Send text-end chunk to signal completion (SSE format)
        # Note: The AI SDK expects "text-end", not "text-done"
        end_data = json.dumps({
            "type": "text-end",
            "id": message_id
        })
        yield f"data: {end_data}\n\n".encode('utf-8')
        
        logger.info(f"Successfully streamed response to user {user_id}")
        
    except Exception as e:
        logger.error(f"Error streaming response: {str(e)}", exc_info=True)
        # Stream error response in AI SDK format
        error_chunk = json.dumps({
            "type": "error",
            "error": str(e)
        }) + "\n"
        yield error_chunk.encode('utf-8')


@router.post("/chat")
async def chat_endpoint(
    request: ChatRequest,
    current_user: CurrentUser,
    session: SessionDep,
) -> StreamingResponse:
    """
    Chat endpoint for financial queries
    
    Accepts a list of messages and streams back NDJSON responses
    Requires authentication via JWT token
    
    Args:
        request: ChatRequest with message history
        current_user: Authenticated user from JWT token
        session: Database session for querying financial data
        
    Returns:
        StreamingResponse with NDJSON content
        
    Example request:
        {
            "messages": [
                {"role": "user", "content": "How much did I spend on groceries?"},
                {"role": "assistant", "content": "You spent $150 on groceries..."},
                {"role": "user", "content": "Any trends?"}
            ]
        }
    
    Example response (NDJSON stream):
        {"content": "You", "type": "text"}\n
        {"content": " spent", "type": "text"}\n
        {"content": " $150", "type": "text"}\n
        ...
    """
    logger.info(f"Chat request from user {current_user.id} with {len(request.messages)} messages")
    
    # Validate request
    if not request.messages:
        raise HTTPException(status_code=400, detail="No messages provided")
    
    # Get the last user message - extract content from either format
    last_message = request.messages[-1]
    user_message = last_message.get_content()
    if not user_message or not user_message.strip():
        raise HTTPException(status_code=400, detail="Empty message content")
    
    # Log chat interaction
    logger.debug(f"User {current_user.id} message: {user_message[:100]}")
    
    # Return streaming response with conversation history and session for context
    # Use text/event-stream for SSE format (AI SDK expects this)
    return StreamingResponse(
        stream_response_generator(user_message, current_user.id, session, request.messages),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable proxy buffering
            "Transfer-Encoding": "chunked",
        }
    )
