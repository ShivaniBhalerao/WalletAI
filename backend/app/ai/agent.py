"""
Core LangGraph agent implementation for Financial Analyst (Tool-Based Architecture)

This version uses LangGraph's built-in tool support for dynamic tool calling.
The LLM decides which tools to call based on user queries.
"""

import logging
import uuid
from typing import Literal

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode, tools_condition
from sqlmodel import Session

from app.ai.config import AIConfig
from app.ai.shared_prompts import FINANCIAL_ANALYST_PERSONA
from app.ai.state import FinancialAgentState, create_initial_state
from app.ai.tools import clear_context, get_all_tools, set_context

logger = logging.getLogger(__name__)


# =============================================================================
# Agent Nodes
# =============================================================================


def call_model_node(state: FinancialAgentState) -> dict:
    """
    Call the LLM with tool binding to generate a response or tool calls.
    
    This node:
    1. Calls the LLM with bound tools
    2. Returns the LLM's response (which may include tool calls)
    
    Note: Context is NOT cleared here as tools may need it in the next node.
    Context is only cleared after the entire agent execution completes.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with new message from LLM
    """
    logger.info(f"Executing call_model_node for user {state['user_id']}")
    
    try:
        # Get LLM with tools bound
        llm = get_llm_with_tools()
        
        # Prepare messages for LLM call
        # We need to include system message at the start, but we don't want to 
        # modify the state's message history
        messages = state["messages"]
        
        # Prepare messages for LLM: ensure system message is at the start
        messages_for_llm = []
        if messages and isinstance(messages[0], SystemMessage):
            # System message already present, use messages as-is
            messages_for_llm = messages
        else:
            # Add system message for this LLM call
            messages_for_llm = [SystemMessage(content=FINANCIAL_ANALYST_PERSONA)] + messages
        
        logger.info(f"Calling LLM with {len(messages_for_llm)} messages")
        
        # Call LLM
        response = llm.invoke(messages_for_llm)
        
        logger.info(f"LLM response received, type: {type(response)}")
        logger.info(f"LLM response content type: {type(response.content)}")
        logger.info(f"LLM response content: {response.content}")
        
        # Check if response has tool calls
        if hasattr(response, "tool_calls") and response.tool_calls:
            logger.info(f"LLM response includes {len(response.tool_calls)} tool calls")
            for idx, tool_call in enumerate(response.tool_calls):
                logger.debug(f"Tool call {idx + 1}: {tool_call.get('name', 'unknown')} with args: {tool_call.get('args', {})}")
        else:
            logger.info("LLM response has no tool calls")
        
        # Log response content for debugging
        if isinstance(response.content, str):
            logger.debug(f"LLM string response (first 200 chars): {response.content[:200]}")
        elif isinstance(response.content, list):
            logger.warning(f"LLM response content is a list with {len(response.content)} items")
            logger.debug(f"LLM list response items: {response.content}")
        else:
            logger.warning(f"LLM response content is unexpected type: {type(response.content)}")
        
        # Return ONLY the new response message - LangGraph will append it to state
        return {
            "messages": [response],
            "error": None,
        }
        
    except Exception as e:
        logger.error(f"Error in call_model_node: {e}", exc_info=True)
        
        # Create error message
        error_msg = AIMessage(
            content="I apologize, but I encountered an error processing your request. "
                   "Please try rephrasing your question or try again later."
        )
        
        return {
            "messages": [error_msg],
            "error": str(e),
        }


def call_tools_node(state: FinancialAgentState) -> dict:
    """
    Execute tools requested by the LLM.
    
    This node:
    1. Sets up the context for tools (session and user_id)
    2. Executes the tools using LangGraph's ToolNode
    3. Returns the tool results
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with tool messages
    """
    logger.info(f"Executing call_tools_node for user {state['user_id']}")
    
    try:
        # Set context for tools before execution
        session = state["session"]
        user_id = state["user_id"]
        set_context(session, user_id)
        logger.debug(f"Context set for tools: user_id={user_id}")
        
        # Get tools and create ToolNode
        tools = get_all_tools()
        tool_node = ToolNode(tools)
        
        # Execute tools
        result = tool_node.invoke(state)
        
        logger.info(f"Tools executed successfully, returned {len(result.get('messages', []))} messages")
        
        return result
        
    except Exception as e:
        logger.error(f"Error in call_tools_node: {e}", exc_info=True)
        
        # Create error message
        error_msg = AIMessage(
            content="I encountered an error while retrieving your financial data. "
                   "Please try again in a moment."
        )
        
        # Return only the new error message - LangGraph will append it
        return {
            "messages": [error_msg],
            "error": str(e),
        }


# =============================================================================
# Helper Functions
# =============================================================================


def get_llm_with_tools() -> ChatGoogleGenerativeAI:
    """
    Initialize and return the Gemini LLM with tools bound.
    
    Returns:
        Configured ChatGoogleGenerativeAI instance with tools bound
        
    Raises:
        ValueError: If GOOGLE_API_KEY is not set
    """
    if not AIConfig.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set. Please configure it in environment variables.")
    
    # Get base LLM
    llm = ChatGoogleGenerativeAI(
        google_api_key=AIConfig.GOOGLE_API_KEY,
        **AIConfig.get_model_kwargs()
    )
    
    # Get all registered tools
    tools = get_all_tools()
    
    logger.info(f"Binding {len(tools)} tools to LLM")
    
    # Bind tools to LLM
    llm_with_tools = llm.bind_tools(tools)
    
    return llm_with_tools


def should_continue(state: FinancialAgentState) -> Literal["tools", "end"]:
    """
    Conditional edge to determine if we should call tools or end.
    
    Args:
        state: Current agent state
        
    Returns:
        "tools" if the LLM wants to call tools, "end" otherwise
    """
    messages = state["messages"]
    last_message = messages[-1]
    
    # Check if the last message has tool calls
    if hasattr(last_message, "tool_calls") and last_message.tool_calls:
        logger.info(f"Tool calls detected: {len(last_message.tool_calls)} tool(s)")
        return "tools"
    
    logger.info("No tool calls, ending conversation turn")
    return "end"


# =============================================================================
# Agent Builder
# =============================================================================


def build_financial_agent() -> StateGraph:
    """
    Build the LangGraph agent for financial analysis with tool support.
    
    This function constructs a ReAct-style agent graph with the following flow:
    1. call_model_node: LLM decides whether to use tools or respond
    2. Conditional routing: If tools needed, execute them; otherwise end
    3. tools_node: Execute requested tools
    4. Loop back to call_model_node to let LLM process tool results
    
    Returns:
        Compiled LangGraph StateGraph ready for execution
        
    Raises:
        ValueError: If AI configuration is invalid
        
    Example:
        >>> agent = build_financial_agent()
        >>> result = agent.invoke(initial_state)
    """
    logger.info("Building financial agent graph with tool support")
    
    # Validate configuration
    if not AIConfig.validate_config():
        raise ValueError(
            "AI configuration invalid. Please ensure GOOGLE_API_KEY is set. "
            "Set it as an environment variable: export GOOGLE_API_KEY='your-key'"
        )
    
    # Get tools
    tools = get_all_tools()
    logger.info(f"Loaded {len(tools)} tools for agent")
    
    # Create the graph
    workflow = StateGraph(FinancialAgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model_node)
    workflow.add_node("tools", call_tools_node)  # Use custom tool node that sets context
    
    # Set entry point
    workflow.set_entry_point("agent")
    
    # Add conditional edges
    # After agent node, decide whether to use tools or end
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "end": END,
        },
    )
    
    # After using tools, always go back to agent to process results
    workflow.add_edge("tools", "agent")
    
    logger.info("Agent graph construction complete")
    
    # Compile the graph
    compiled_graph = workflow.compile()
    
    logger.info("Agent graph compiled successfully")
    
    return compiled_graph


# =============================================================================
# Public API
# =============================================================================


def process_message(
    user_id: uuid.UUID,
    messages: list[BaseMessage],
    session: Session,
    conversation_context: dict | None = None
) -> FinancialAgentState:
    """
    Process a user message through the financial agent.
    
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
        
        # Set context before invoking agent (needed for the entire execution)
        set_context(session, user_id)
        logger.debug(f"Context set for agent execution: user_id={user_id}")
        
        try:
            # Invoke the agent
            logger.info("Invoking agent graph")
            result = agent.invoke(initial_state)
            
            logger.info(f"Agent processing complete, final message count: {len(result['messages'])}")
            
            # Log the response for debugging
            if result["messages"]:
                last_message = result["messages"][-1]
                last_response = last_message.content
                logger.info(f"Final agent message type: {type(last_message)}")
                logger.info(f"Final agent content type: {type(last_response)}")
                
                if isinstance(last_response, str):
                    logger.debug(f"Agent response (first 200 chars): {last_response[:200]}...")
                elif isinstance(last_response, list):
                    logger.warning(f"Agent response is a list with {len(last_response)} items: {last_response}")
                else:
                    logger.warning(f"Agent response is unexpected type: {type(last_response)}")
            
            return result
        finally:
            # Always clear context after agent execution completes
            clear_context()
            logger.debug("Context cleared after agent execution")
        
    except Exception as e:
        logger.error(f"Error processing message: {e}", exc_info=True)
        
        # Ensure context is cleared even on error
        clear_context()
        logger.debug("Context cleared after error")
        
        # Create error state
        error_state = create_initial_state(user_id=user_id, messages=messages, session=session)
        error_state["error"] = str(e)
        
        # Try to format a user-friendly error response
        try:
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
    Simplified interface for processing a single message.
    
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
