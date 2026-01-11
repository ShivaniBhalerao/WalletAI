"""
Agent node functions for the Financial Analyst Agent

Each node represents a step in the agent's processing pipeline
"""

import json
import logging
from datetime import date
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.ai.config import AIConfig
from app.ai.prompts import (
    CLARIFICATION_PROMPT,
    ERROR_RESPONSE_PROMPT,
    FINANCIAL_ANALYST_PERSONA,
    INTENT_ANALYSIS_PROMPT,
    RESPONSE_GENERATION_PROMPT,
)
from app.ai.state import FinancialAgentState
from app.ai.tools import (
    compare_spending_periods,
    get_category_breakdown,
    get_month_date_range,
    get_transactions,
    parse_time_period,
    query_spending_by_category,
    query_spending_by_time_period,
)

logger = logging.getLogger(__name__)


def get_llm() -> ChatGoogleGenerativeAI:
    """
    Initialize and return the Gemini LLM instance
    
    Returns:
        Configured ChatGoogleGenerativeAI instance
        
    Raises:
        ValueError: If GOOGLE_API_KEY is not set
    """
    if not AIConfig.GOOGLE_API_KEY:
        raise ValueError("GOOGLE_API_KEY not set. Please configure it in environment variables.")
    
    return ChatGoogleGenerativeAI(
        google_api_key=AIConfig.GOOGLE_API_KEY,
        **AIConfig.get_model_kwargs()
    )


def analyze_intent_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Node 1: Analyze user intent and extract entities
    
    This node processes the user's latest message to understand what they're
    asking for and extracts relevant financial entities (categories, amounts, etc.)
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with intent, entities, and keywords
    """
    logger.info(f"Executing analyze_intent_node for user {state['user_id']}")
    
    try:
        # Get the last user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        if not user_messages:
            logger.error("No user messages found in state")
            return {
                **state,
                "error": "No user message to analyze",
            }
        
        last_message = user_messages[-1].content
        logger.info(f"Analyzing message: {last_message[:100]}...")
        
        # Get conversation context
        context = state.get("context", {})
        context_str = json.dumps(context) if context else "No previous context"
        
        # Build prompt for intent analysis
        prompt = INTENT_ANALYSIS_PROMPT.format(
            message=last_message,
            context=context_str
        )
        
        # Call LLM for intent analysis
        llm = get_llm()
        messages = [
            SystemMessage(content="You are an expert at analyzing user intent in financial queries."),
            HumanMessage(content=prompt)
        ]
        
        logger.info("Calling Gemini for intent analysis")
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        logger.debug(f"Intent analysis response: {response_text[:200]}...")
        
        # Parse JSON response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            logger.warning(f"Could not find JSON in LLM response, using fallback")
            # Fallback to basic analysis
            return {
                **state,
                "intent": "general_question",
                "entities": {},
                "keywords": [],
                "needs_clarification": False,
            }
        
        json_str = response_text[json_start:json_end]
        analysis = json.loads(json_str)
        
        intent = analysis.get("intent", "general_question")
        entities = analysis.get("entities", {})
        keywords = analysis.get("keywords", [])
        needs_clarification = analysis.get("needs_clarification", False)
        
        logger.info(f"Intent extracted: {intent}, needs_clarification: {needs_clarification}")
        
        return {
            **state,
            "intent": intent,
            "entities": entities,
            "keywords": keywords,
            "needs_clarification": needs_clarification,
            "context": {
                **context,
                "last_intent": intent,
                "last_entities": entities,
            },
            "error": None,
        }
        
    except Exception as e:
        logger.error(f"Error in analyze_intent_node: {e}", exc_info=True)
        return {
            **state,
            "error": f"Failed to analyze intent: {str(e)}",
            "intent": "general_question",
            "needs_clarification": False,
        }


def fetch_financial_data_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Node 2: Fetch financial data from database
    
    This node queries the database based on the extracted intent and entities
    to retrieve relevant financial data for the user's query.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with financial_data populated
    """
    logger.info(f"Executing fetch_financial_data_node for user {state['user_id']}")
    
    try:
        intent = state.get("intent", "general_question")
        entities = state.get("entities", {})
        session = state["session"]
        user_id = state["user_id"]
        
        financial_data = {}
        
        # Parse time period from entities
        time_period = entities.get("time_period", "this_month")
        start_date, end_date = parse_time_period(time_period)
        
        logger.info(f"Fetching data for intent: {intent}, time_period: {time_period}")
        
        # Fetch data based on intent
        if intent == "spending_query":
            # User asking about spending in a specific category
            categories = entities.get("categories", [])
            
            if categories:
                # Query spending for the first category mentioned
                category = categories[0]
                data = query_spending_by_category(
                    session=session,
                    user_id=user_id,
                    category=category,
                    start_date=start_date,
                    end_date=end_date
                )
                financial_data = {
                    "type": "category_spending",
                    "data": data
                }
            else:
                # No specific category, get overall spending
                data = query_spending_by_time_period(
                    session=session,
                    user_id=user_id,
                    start_date=start_date,
                    end_date=end_date
                )
                financial_data = {
                    "type": "period_spending",
                    "data": data
                }
        
        elif intent == "spending_comparison":
            # User comparing spending across periods
            # Default to comparing this month vs last month
            period1_start, period1_end = get_month_date_range(0)
            period2_start, period2_end = get_month_date_range(1)
            
            # Override with entities if provided
            if entities.get("comparison"):
                # Try to parse custom comparison periods
                pass  # Use defaults for now
            
            data = compare_spending_periods(
                session=session,
                user_id=user_id,
                period1_start=period1_start,
                period1_end=period1_end,
                period2_start=period2_start,
                period2_end=period2_end
            )
            financial_data = {
                "type": "spending_comparison",
                "data": data
            }
        
        elif intent == "category_analysis":
            # User asking for spending breakdown by category
            data = get_category_breakdown(
                session=session,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            financial_data = {
                "type": "category_breakdown",
                "data": data
            }
        
        elif intent == "transaction_query":
            # User asking about specific transactions
            categories = entities.get("categories", [])
            merchants = entities.get("merchants", [])
            
            category = categories[0] if categories else None
            merchant = merchants[0] if merchants else None
            
            data = get_transactions(
                session=session,
                user_id=user_id,
                category=category,
                merchant=merchant,
                start_date=start_date,
                end_date=end_date,
                limit=10
            )
            financial_data = {
                "type": "transactions",
                "data": {"transactions": data}
            }
        
        else:
            # For general questions or other intents, fetch category breakdown as context
            data = get_category_breakdown(
                session=session,
                user_id=user_id,
                start_date=start_date,
                end_date=end_date
            )
            financial_data = {
                "type": "general",
                "data": data
            }
        
        logger.info(f"Fetched financial data: type={financial_data.get('type')}")
        
        return {
            **state,
            "financial_data": financial_data,
            "error": None,
        }
        
    except Exception as e:
        logger.error(f"Error in fetch_financial_data_node: {e}", exc_info=True)
        # Continue without data - the response node will handle missing data
        return {
            **state,
            "financial_data": {"type": "error", "data": {}},
            "error": None,  # Don't propagate as error, just use empty data
        }


def generate_clarification_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Node 2a: Generate a clarifying question
    
    This node is called when the user's intent is unclear and we need
    to ask for more information.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with clarification question
    """
    logger.info(f"Executing generate_clarification_node for user {state['user_id']}")
    
    try:
        # Get the last user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        last_message = user_messages[-1].content if user_messages else ""
        
        # Build clarification prompt
        context = state.get("context", {})
        prompt = CLARIFICATION_PROMPT.format(
            message=last_message,
            reason="Intent unclear or ambiguous",
            context=json.dumps(context) if context else "No previous context"
        )
        
        # Call LLM
        llm = get_llm()
        messages = [
            SystemMessage(content=FINANCIAL_ANALYST_PERSONA),
            HumanMessage(content=prompt)
        ]
        
        logger.info("Calling Gemini for clarification question")
        response = llm.invoke(messages)
        clarification_question = response.content.strip()
        
        logger.info(f"Generated clarification: {clarification_question[:100]}...")
        
        return {
            **state,
            "clarification_question": clarification_question,
            "error": None,
        }
        
    except Exception as e:
        logger.error(f"Error in generate_clarification_node: {e}", exc_info=True)
        # Fallback clarification
        fallback = "I want to help you with your financial question. Could you provide more details about what you'd like to know?"
        return {
            **state,
            "clarification_question": fallback,
            "error": None,
        }


def generate_response_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Node 3: Generate financial analyst response
    
    This node generates the main response to the user's query based on
    the extracted intent, entities, and fetched financial data.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with generated response
    """
    logger.info(f"Executing generate_response_node for user {state['user_id']}")
    
    try:
        # Get the last user message
        user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
        last_message = user_messages[-1].content if user_messages else ""
        
        intent = state.get("intent", "general_question")
        entities = state.get("entities", {})
        keywords = state.get("keywords", [])
        context = state.get("context", {})
        financial_data = state.get("financial_data", {})
        
        # Build response generation prompt with financial data
        prompt = RESPONSE_GENERATION_PROMPT.format(
            message=last_message,
            intent=intent,
            entities=json.dumps(entities) if entities else "None",
            keywords=", ".join(keywords) if keywords else "None",
            financial_data=json.dumps(financial_data, default=str) if financial_data else "No data available",
            context=json.dumps(context) if context else "No previous context"
        )
        
        # Call LLM with full persona and conversation history
        llm = get_llm()
        
        # Include recent conversation history for context
        conversation_messages = [SystemMessage(content=FINANCIAL_ANALYST_PERSONA)]
        
        # Add last few messages for context (but not too many)
        recent_messages = state["messages"][-6:]  # Last 3 exchanges (user + assistant)
        for msg in recent_messages[:-1]:  # Exclude the current message we're responding to
            conversation_messages.append(msg)
        
        # Add the response generation prompt
        conversation_messages.append(HumanMessage(content=prompt))
        
        logger.info(f"Calling Gemini for response generation (intent: {intent})")
        response = llm.invoke(conversation_messages)
        generated_response = response.content.strip()
        
        logger.info(f"Generated response length: {len(generated_response)} characters")
        
        return {
            **state,
            "clarification_question": None,
            "context": {
                **context,
                "last_response_intent": intent,
            },
            "error": None,
            # Store the response temporarily - will be added to messages in format node
            "generated_response": generated_response,
        }
        
    except Exception as e:
        logger.error(f"Error in generate_response_node: {e}", exc_info=True)
        return {
            **state,
            "error": f"Failed to generate response: {str(e)}",
        }


def format_response_node(state: FinancialAgentState) -> FinancialAgentState:
    """
    Node 4: Format final response
    
    This node takes either the clarification question or generated response
    and formats it as an AI message to be added to the conversation.
    
    Args:
        state: Current agent state
        
    Returns:
        Updated state with response added to messages
    """
    logger.info(f"Executing format_response_node for user {state['user_id']}")
    
    try:
        # Check if we have an error
        if state.get("error"):
            error_message = state["error"]
            logger.warning(f"Formatting error response: {error_message}")
            
            # Generate friendly error message
            user_messages = [msg for msg in state["messages"] if isinstance(msg, HumanMessage)]
            last_message = user_messages[-1].content if user_messages else ""
            
            try:
                llm = get_llm()
                prompt = ERROR_RESPONSE_PROMPT.format(
                    message=last_message,
                    error=error_message
                )
                error_response = llm.invoke([
                    SystemMessage(content=FINANCIAL_ANALYST_PERSONA),
                    HumanMessage(content=prompt)
                ])
                response_text = error_response.content.strip()
            except Exception as e:
                logger.error(f"Error generating error message: {e}")
                response_text = "I apologize, but I'm having trouble processing your request right now. Please try again or rephrase your question."
        
        # Check if we have a clarification question
        elif state.get("clarification_question"):
            response_text = state["clarification_question"]
            logger.info("Using clarification question as response")
        
        # Check if we have a generated response
        elif state.get("generated_response"):
            response_text = state["generated_response"]
            logger.info("Using generated response")
        
        else:
            logger.error("No response content available")
            response_text = "I'm here to help with your financial questions. What would you like to know?"
        
        # Create AI message
        ai_message = AIMessage(content=response_text)
        
        # Add to message history
        updated_messages = state["messages"] + [ai_message]
        
        # Clean up temporary fields
        cleaned_state = {k: v for k, v in state.items() if not k.startswith("_")}
        cleaned_state["generated_response"] = None  # Clear the temporary response
        
        logger.info(f"Response formatted successfully, total messages: {len(updated_messages)}")
        
        return {
            **cleaned_state,
            "messages": updated_messages,
        }
        
    except Exception as e:
        logger.error(f"Error in format_response_node: {e}", exc_info=True)
        # Fallback response
        fallback_message = AIMessage(content="I apologize, but I encountered an error. Please try asking your question again.")
        return {
            **state,
            "messages": state["messages"] + [fallback_message],
        }

