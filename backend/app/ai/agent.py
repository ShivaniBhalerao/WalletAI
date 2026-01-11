"""
Core LangGraph agent implementation for Financial Analyst

Builds and manages the agent graph with nodes and conditional routing
"""

import logging
import uuid
from typing import Literal

from langchain_core.messages import BaseMessage, HumanMessage
from langgraph.graph import END, StateGraph
from sqlmodel import Session

from app.ai.config import AIConfig
from app.ai.nodes import (
    analyze_intent_node,
    fetch_financial_data_node,
    format_response_node,
    generate_clarification_node,
    generate_response_node,
)
from app.ai.state import FinancialAgentState, create_initial_state

logger = logging.getLogger(__name__)


def should_clarify(state: FinancialAgentState) -> Literal["clarify", "fetch_data"]:
    """
    Conditional edge function to determine if clarification is needed
    
    Routes to clarification node if the user's intent is unclear,
    otherwise routes to data fetching.
    
    Args:
        state: Current agent state
        
    Returns:
        "clarify" if clarification needed, "fetch_data" otherwise
    """
    logger.info("Evaluating conditional edge: should_clarify")
    
    # If there's an error, skip clarification and go to fetch data
    if state.get("error"):
        logger.info("Error detected, routing to fetch_data")
        return "fetch_data"
    
    # Check if clarification is needed and enabled
    needs_clarification = state.get("needs_clarification", False)
    clarification_enabled = AIConfig.ENABLE_CLARIFICATION
    
    # Check if intent is explicitly unclear
    intent = state.get("intent")
    is_unclear = intent == "unclear"
    
    if clarification_enabled and (needs_clarification or is_unclear):
        logger.info("Clarification needed, routing to clarify")
        return "clarify"
    
    logger.info("No clarification needed, routing to fetch_data")
    return "fetch_data"


def build_financial_agent() -> StateGraph:
    """
    Build the LangGraph agent for financial analysis
    
    This function constructs the agent graph with the following flow:
    1. analyze_intent_node: Extracts intent and entities from user message
    2. Conditional routing: Either ask for clarification or fetch data
    3. fetch_financial_data_node: Queries database for relevant financial data
    4. generate_response_node: Generates response using fetched data
    5. format_response_node: Formats the final response
    
    Returns:
        Compiled LangGraph StateGraph ready for execution
        
    Raises:
        ValueError: If AI configuration is invalid
        
    Example:
        >>> agent = build_financial_agent()
        >>> result = agent.invoke(initial_state)
    """
    logger.info("Building financial agent graph")
    
    # Validate configuration
    if not AIConfig.validate_config():
        raise ValueError(
            "AI configuration invalid. Please ensure GOOGLE_API_KEY is set. "
            "Set it as an environment variable: export GOOGLE_API_KEY='your-key'"
        )
    
    # Create the graph
    workflow = StateGraph(FinancialAgentState)
    
    # Add nodes to the graph
    workflow.add_node("analyze_intent", analyze_intent_node)
    workflow.add_node("fetch_financial_data", fetch_financial_data_node)
    workflow.add_node("generate_clarification", generate_clarification_node)
    workflow.add_node("generate_response", generate_response_node)
    workflow.add_node("format_response", format_response_node)
    
    # Set the entry point
    workflow.set_entry_point("analyze_intent")
    
    # Add conditional edges
    # After analyzing intent, decide whether to clarify or fetch data
    workflow.add_conditional_edges(
        "analyze_intent",
        should_clarify,
        {
            "clarify": "generate_clarification",
            "fetch_data": "fetch_financial_data",
        },
    )
    
    # After fetching data, generate response
    workflow.add_edge("fetch_financial_data", "generate_response")
    
    # After generating clarification, format and end
    workflow.add_edge("generate_clarification", "format_response")
    
    # After generating response, format and end
    workflow.add_edge("generate_response", "format_response")
    
    # After formatting, end the graph
    workflow.add_edge("format_response", END)
    
    logger.info("Agent graph construction complete")
    
    # Compile the graph
    compiled_graph = workflow.compile()
    
    logger.info("Agent graph compiled successfully")
    
    return compiled_graph


def process_message(
    user_id: uuid.UUID,
    messages: list[BaseMessage],
    session: Session,
    conversation_context: dict | None = None
) -> FinancialAgentState:
    """
    Process a user message through the financial agent
    
    This is the main entry point for interacting with the agent.
    It builds the agent, creates the initial state, and invokes the graph.
    
    Args:
        user_id: UUID of the authenticated user
        messages: List of conversation messages (LangChain format)
        session: Database session for querying financial data
        conversation_context: Optional additional context to pass to the agent
        
    Returns:
        Final agent state after processing, including the response message
        
    Raises:
        ValueError: If no messages provided or configuration invalid
        Exception: If agent processing fails
        
    Example:
        >>> from langchain_core.messages import HumanMessage
        >>> messages = [HumanMessage(content="How much did I spend on groceries?")]
        >>> result = process_message(user_id=uuid.uuid4(), messages=messages, session=session)
        >>> print(result["messages"][-1].content)  # AI response
    """
    logger.info(f"Processing message for user {user_id}, message count: {len(messages)}")
    
    # Validate input
    if not messages:
        raise ValueError("No messages provided")
    
    # Extract just the user message if that's what was passed
    last_message = messages[-1]
    if not isinstance(last_message, HumanMessage):
        raise ValueError("Last message must be a HumanMessage")
    
    logger.info(f"User message: {last_message.content[:100]}...")
    
    try:
        # Build the agent
        agent = build_financial_agent()
        
        # Create initial state with session
        initial_state = create_initial_state(user_id=user_id, messages=messages, session=session)
        
        # Add any additional context
        if conversation_context:
            initial_state["context"] = {
                **initial_state.get("context", {}),
                **conversation_context
            }
        
        # Trim message history if too long (keep last N messages)
        if len(messages) > AIConfig.MAX_CONVERSATION_HISTORY:
            logger.info(f"Trimming message history from {len(messages)} to {AIConfig.MAX_CONVERSATION_HISTORY}")
            initial_state["messages"] = messages[-AIConfig.MAX_CONVERSATION_HISTORY:]
        
        # Invoke the agent
        logger.info("Invoking agent graph")
        result = agent.invoke(initial_state)
        
        logger.info(f"Agent processing complete, final message count: {len(result['messages'])}")
        
        # Log the response for debugging
        if result["messages"]:
            last_response = result["messages"][-1].content
            logger.debug(f"Agent response: {last_response[:200]}...")
        
        return result
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        
        # Create error state
        error_state = create_initial_state(user_id=user_id, messages=messages, session=session)
        error_state["error"] = str(e)
        
        # Try to format a user-friendly error response
        try:
            from langchain_core.messages import AIMessage
            error_message = AIMessage(
                content="I apologize, but I'm having trouble processing your request right now. "
                        "Please try again in a moment, or rephrase your question."
            )
            error_state["messages"] = messages + [error_message]
        except Exception:
            pass
        
        return error_state


def process_message_simple(user_id: uuid.UUID, message_text: str, session: Session) -> str:
    """
    Simplified interface for processing a single message
    
    Convenience function that handles message conversion and returns just the response text.
    
    Args:
        user_id: UUID of the authenticated user
        message_text: The user's message as plain text
        session: Database session for querying financial data
        
    Returns:
        The agent's response as plain text
        
    Example:
        >>> response = process_message_simple(user_id=uuid.uuid4(), message_text="Show my spending", session=session)
        >>> print(response)
    """
    logger.info(f"Processing simple message for user {user_id}")
    
    # Convert to LangChain message
    message = HumanMessage(content=message_text)
    
    # Process through agent
    result = process_message(user_id=user_id, messages=[message], session=session)
    
    # Extract response text
    if result["messages"]:
        response = result["messages"][-1].content
        return response
    
    return "I'm sorry, I couldn't process your request."

