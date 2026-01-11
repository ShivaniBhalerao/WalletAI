"""
Agent state definitions for Financial Analyst Agent

Defines the state structure used throughout the LangGraph agent execution
"""

import uuid
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage


class FinancialAgentState(TypedDict):
    """
    State structure for the financial analyst agent.
    
    This state is passed between nodes in the LangGraph and accumulates
    information throughout the conversation flow.
    
    Attributes:
        messages: List of conversation messages in LangChain format
                  (HumanMessage, AIMessage, SystemMessage)
        user_id: UUID of the authenticated user
        intent: Extracted user intent (spending_query, comparison, etc.)
        entities: Extracted entities from user message (categories, amounts, dates)
        keywords: Key terms extracted from the message
        needs_clarification: Whether the agent needs to ask for clarification
        clarification_question: The clarification question to ask (if needed)
        context: Additional session context (metadata, previous intents, etc.)
        error: Error message if something goes wrong
    """
    
    messages: Annotated[list[BaseMessage], "Conversation message history"]
    user_id: uuid.UUID
    intent: str | None
    entities: dict[str, Any] | None
    keywords: list[str] | None
    needs_clarification: bool
    clarification_question: str | None
    context: dict[str, Any]
    error: str | None
    generated_response: str | None  # Temporary storage for response between nodes


# Intent types that the agent can recognize
INTENT_TYPES = {
    "spending_query": "User asking about spending in specific categories or time periods",
    "spending_comparison": "User comparing spending across time periods",
    "category_analysis": "User asking for spending breakdown by category",
    "trend_analysis": "User asking about spending trends over time",
    "savings_suggestion": "User asking for tips to save money",
    "budget_query": "User asking about budget or budget limits",
    "transaction_query": "User asking about specific transactions",
    "general_question": "General financial question or greeting",
    "unclear": "User intent is unclear, needs clarification",
}


def create_initial_state(user_id: uuid.UUID, messages: list[BaseMessage]) -> FinancialAgentState:
    """
    Create initial agent state for a new conversation turn
    
    Args:
        user_id: The authenticated user's UUID
        messages: Initial message history
        
    Returns:
        FinancialAgentState with default values
    """
    return FinancialAgentState(
        messages=messages,
        user_id=user_id,
        intent=None,
        entities=None,
        keywords=None,
        needs_clarification=False,
        clarification_question=None,
        context={},
        error=None,
        generated_response=None,
    )

