"""
LangGraph Learning Project: Number Addition Agent

This module demonstrates how to build a simple LangGraph agent that:
1. Parses text input to extract two numbers
2. Adds them together
3. Returns the result

This is a learning example to understand LangGraph concepts including:
- State management
- Node definitions
- Graph construction
- Agent execution

Author: Learning Project
"""

import argparse
import json
import logging
import os
import re
import sys
from typing import Annotated, Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph

# Configure logging following project patterns
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# API KEY CONFIGURATION
# ============================================================================
# Option 1 (Recommended): Set as environment variable
#   In terminal: export GOOGLE_API_KEY="your-api-key-here"
#
# Option 2 (For testing only): Uncomment and set your API key below
#   WARNING: Never commit API keys to git! This is only for local testing.
# ============================================================================
# GOOGLE_API_KEY_FALLBACK = "your-api-key-here"  # Uncomment and add your key here
GOOGLE_API_KEY_FALLBACK = None  # Set to None to use environment variable only

# Try to import Google Gemini - will fail gracefully if not installed
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning(
        "langchain-google-genai not installed. LLM features will not be available. "
        "Install with: pip install langchain-google-genai"
    )


# Define the state structure for our agent
class AgentState(TypedDict):
    """
    State structure for the number addition agent.
    
    Attributes:
        messages: List of messages in the conversation
        number1: First extracted number (optional)
        number2: Second extracted number (optional)
        result: The sum of the two numbers (optional)
        error: Error message if something goes wrong (optional)
    """
    messages: Annotated[list, "list of messages"]
    number1: float | None
    number2: float | None
    result: float | None
    error: str | None


def has_written_numbers(text: str) -> bool:
    """
    Check if text likely contains written numbers (one, two, three, etc.).
    
    Args:
        text: Input text to check
        
    Returns:
        True if text likely contains written numbers
    """
    written_number_words = [
        "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
        "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", 
        "eighteen", "nineteen", "twenty"
    ]
    text_lower = text.lower()
    return any(word in text_lower for word in written_number_words)


def extract_numbers_regex(text: str) -> tuple[float | None, float | None]:
    """
    Extract two numbers from text input using regex.
    
    This function uses regex to find numbers in the input text.
    It looks for integers and decimals.
    
    Args:
        text: Input text that may contain numbers
        
    Returns:
        Tuple of (first_number, second_number) or (None, None) if not found
        
    Example:
        >>> extract_numbers_regex("Add 5 and 10")
        (5.0, 10.0)
        >>> extract_numbers_regex("What is 3.5 plus 2.7?")
        (3.5, 2.7)
    """
    logger.info(f"Extracting numbers using regex from text: {text}")
    
    # Pattern to match integers and decimals
    pattern = r'-?\d+\.?\d*'
    numbers = re.findall(pattern, text)
    
    if len(numbers) >= 2:
        try:
            num1 = float(numbers[0])
            num2 = float(numbers[1])
            logger.info(f"Extracted numbers: {num1} and {num2}")
            return num1, num2
        except ValueError as e:
            logger.error(f"Error converting numbers to float: {e}")
            return None, None
    else:
        logger.warning(f"Could not find two numbers in text. Found: {numbers}")
        return None, None


def extract_numbers_llm(text: str) -> tuple[float | None, float | None]:
    """
    Extract two numbers from text input using Google Gemini LLM.
    
    This function uses Google Gemini to understand natural language
    and extract numbers, including written numbers like "two", "three", etc.
    
    Args:
        text: Input text that may contain numbers in various formats
        
    Returns:
        Tuple of (first_number, second_number) or (None, None) if not found
        
    Example:
        >>> extract_numbers_llm("Add 5 and two")
        (5.0, 2.0)
        >>> extract_numbers_llm("What is three plus four?")
        (3.0, 4.0)
    """
    if not GEMINI_AVAILABLE:
        logger.error("Google Gemini LLM not available. Install langchain-google-genai.")
        return None, None
    
    logger.info(f"Extracting numbers using Google Gemini from text: {text}")
    
    # Check for API key (try environment variable first, then fallback)
    api_key = os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY_FALLBACK
    if not api_key:
        logger.error(
            "GOOGLE_API_KEY not set. "
            "Please set it as an environment variable or in the code (see top of file)."
        )
        return None, None
    
    try:
        # Initialize Google Gemini
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            temperature=0,
            google_api_key=api_key,
        )
        
        # Create a system prompt for number extraction
        system_prompt = """You are a helpful assistant that extracts exactly two numbers from user input.
The user may provide numbers in various formats:
- Numeric: 5, 10, 3.5, -2
- Written: one, two, three, four, five, six, seven, eight, nine, ten, eleven, twelve, etc.
- Mixed: "5 and two", "three plus 4"

Your task is to extract exactly two numbers and return them as a JSON object with keys "number1" and "number2".
Convert written numbers to their numeric equivalents.

Return ONLY valid JSON in this format:
{"number1": <first_number>, "number2": <second_number>}

If you cannot find exactly two numbers, return:
{"number1": null, "number2": null}"""
        
        # Create messages
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"Extract two numbers from this text: {text}"),
        ]
        
        # Call the LLM
        logger.info("Calling Google Gemini for number extraction")
        response = llm.invoke(messages)
        response_text = response.content.strip()
        
        logger.info(f"LLM response: {response_text}")
        
        # Parse the JSON response
        # Try to extract JSON from the response (in case LLM adds extra text)
        # Look for JSON object in the response
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        
        if json_start == -1 or json_end == 0:
            logger.error(f"Could not find JSON in LLM response: {response_text}")
            return None, None
        
        json_str = response_text[json_start:json_end]
        result = json.loads(json_str)
        
        num1 = result.get("number1")
        num2 = result.get("number2")
        
        if num1 is None or num2 is None:
            logger.warning(f"LLM could not extract two numbers. Response: {result}")
            return None, None
        
        # Convert to float
        try:
            num1 = float(num1)
            num2 = float(num2)
            logger.info(f"LLM extracted numbers: {num1} and {num2}")
            return num1, num2
        except (ValueError, TypeError) as e:
            logger.error(f"Error converting LLM response to float: {e}")
            return None, None
            
    except Exception as e:
        logger.error(f"Error calling Google Gemini: {e}", exc_info=True)
        return None, None


def extract_numbers(text: str, use_llm: bool = False, auto_fallback: bool = True) -> tuple[float | None, float | None]:
    """
    Extract two numbers from text input.
    
    This function can use either regex or LLM-based extraction.
    With auto_fallback=True (default), it tries regex first and automatically
    falls back to LLM if regex fails and LLM is available.
    
    Args:
        text: Input text that may contain numbers
        use_llm: If True, use Google Gemini for extraction (handles natural language).
                 If False, use regex-based extraction (faster, no API needed).
        auto_fallback: If True and use_llm=False, automatically try LLM if regex fails.
        
    Returns:
        Tuple of (first_number, second_number) or (None, None) if not found
        
    Example:
        >>> extract_numbers("Add 5 and 10", use_llm=False)
        (5.0, 10.0)
        >>> extract_numbers("Add 5 and two", use_llm=True)
        (5.0, 2.0)  # Uses Google Gemini
        >>> extract_numbers("Add 5 and two", use_llm=False, auto_fallback=True)
        (5.0, 2.0)  # Falls back to LLM automatically
    """
    if use_llm:
        # Direct LLM mode
        return extract_numbers_llm(text)
    else:
        # Check if text contains written numbers - if so, use LLM directly
        if has_written_numbers(text):
            logger.info("Detected written numbers in text, using LLM for extraction...")
            api_key = os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY_FALLBACK
            if GEMINI_AVAILABLE and api_key:
                return extract_numbers_llm(text)
            else:
                logger.warning(
                    "Written numbers detected but LLM not available. "
                    "Install langchain-google-genai and set GOOGLE_API_KEY."
                )
        
        # Try regex first
        result = extract_numbers_regex(text)
        
        # If regex failed and auto_fallback is enabled, try LLM
        if result == (None, None) and auto_fallback:
            logger.info("Regex extraction failed, attempting LLM fallback...")
            api_key = os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY_FALLBACK
            
            # Check if LLM is available
            if not GEMINI_AVAILABLE:
                logger.warning(
                    "LLM fallback not available: langchain-google-genai not installed. "
                    "Install with: pip install langchain-google-genai"
                )
            elif not api_key:
                logger.warning(
                    "LLM fallback not available: GOOGLE_API_KEY not set. "
                    "Set it as an environment variable or in the code (see line 43)."
                )
            else:
                logger.info("LLM available, attempting to extract numbers with Google Gemini...")
                llm_result = extract_numbers_llm(text)
                if llm_result != (None, None):
                    logger.info(f"LLM fallback succeeded: extracted {llm_result[0]} and {llm_result[1]}")
                    return llm_result
                else:
                    logger.warning("LLM fallback also failed to extract numbers")
        
        return result


def create_parse_input_node(use_llm: bool = False):
    """
    Factory function to create a parse_input_node with LLM support.
    
    Args:
        use_llm: Whether to use LLM for number extraction
        
    Returns:
        A parse_input_node function configured with the specified extraction method
    """
    def parse_input_node(state: AgentState) -> AgentState:
        """
        Node 1: Parse the input message to extract numbers.
        
        This is the first node in our graph. It processes the user's input
        and extracts the two numbers that need to be added.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with extracted numbers
        """
        logger.info(f"Executing parse_input_node (use_llm={use_llm})")
        
        # Get the last message (user input)
        if not state["messages"]:
            logger.error("No messages in state")
            return {
                **state,
                "error": "No input message provided",
                "number1": None,
                "number2": None,
            }
        
        last_message = state["messages"][-1]
        user_input = last_message.content if hasattr(last_message, "content") else str(last_message)
        
        logger.info(f"Processing user input: {user_input}")
        
        # Extract numbers from the input
        num1, num2 = extract_numbers(user_input, use_llm=use_llm)
        
        if num1 is None or num2 is None:
            logger.warning("Failed to extract two numbers from input")
            return {
                **state,
                "error": "Could not extract two numbers from the input. Please provide two numbers.",
                "number1": None,
                "number2": None,
            }
        
        logger.info(f"Successfully extracted numbers: {num1} and {num2}")
        
        return {
            **state,
            "number1": num1,
            "number2": num2,
            "error": None,
        }
    
    return parse_input_node


def calculate_sum_node(state: AgentState) -> AgentState:
    """
    Node 2: Calculate the sum of the two numbers.
    
    This node performs the actual addition operation.
    
    Args:
        state: Current agent state with number1 and number2
        
    Returns:
        Updated state with the result
    """
    logger.info("Executing calculate_sum_node")
    
    num1 = state.get("number1")
    num2 = state.get("number2")
    
    if num1 is None or num2 is None:
        logger.error("Missing numbers for calculation")
        return {
            **state,
            "error": "Cannot calculate sum: missing numbers",
            "result": None,
        }
    
    result = num1 + num2
    logger.info(f"Calculated sum: {num1} + {num2} = {result}")
    
    return {
        **state,
        "result": result,
        "error": None,
    }


def format_response_node(state: AgentState) -> AgentState:
    """
    Node 3: Format the response message.
    
    This node creates a formatted response message with the result.
    
    Args:
        state: Current agent state with the result
        
    Returns:
        Updated state with formatted response message
    """
    logger.info("Executing format_response_node")
    
    if state.get("error"):
        error_msg = state["error"]
        logger.warning(f"Formatting error response: {error_msg}")
        response = f"Error: {error_msg}"
    else:
        num1 = state.get("number1")
        num2 = state.get("number2")
        result = state.get("result")
        
        if result is not None:
            response = f"The sum of {num1} and {num2} is {result}."
            logger.info(f"Formatted response: {response}")
        else:
            response = "Error: Could not calculate the result."
            logger.error("Result is None when formatting response")
    
    # Add the response as a new message
    from langchain_core.messages import AIMessage
    new_message = AIMessage(content=response)
    
    return {
        **state,
        "messages": state["messages"] + [new_message],
    }


def should_continue(state: AgentState) -> Literal["calculate", "format", "end"]:
    """
    Conditional edge function to determine the next step.
    
    This function decides which node to execute next based on the current state.
    
    Args:
        state: Current agent state
        
    Returns:
        Next node to execute: "calculate", "format", or "end"
    """
    logger.info("Evaluating conditional edge")
    
    # If we have an error, go directly to formatting
    if state.get("error"):
        logger.info("Error detected, routing to format_response_node")
        return "format"
    
    # If we have numbers but no result, calculate
    if state.get("number1") is not None and state.get("number2") is not None and state.get("result") is None:
        logger.info("Numbers extracted, routing to calculate_sum_node")
        return "calculate"
    
    # If we have a result, format the response
    if state.get("result") is not None:
        logger.info("Result calculated, routing to format_response_node")
        return "format"
    
    # Default: end
    logger.info("Routing to end")
    return "end"


def build_number_adder_agent(use_llm: bool = False) -> StateGraph:
    """
    Build the LangGraph agent for adding two numbers.
    
    This function constructs the graph with nodes and edges:
    1. parse_input_node: Extracts numbers from text (using regex or LLM)
    2. calculate_sum_node: Adds the numbers
    3. format_response_node: Formats the response
    
    Args:
        use_llm: If True, use Google Gemini for number extraction (handles natural language).
                 If False, use regex-based extraction (faster, no API needed).
        
    Returns:
        Compiled LangGraph StateGraph ready for execution
        
    Example:
        >>> graph = build_number_adder_agent()
        >>> result = graph.invoke({"messages": [HumanMessage(content="Add 5 and 10")]})
        >>> graph_llm = build_number_adder_agent(use_llm=True)
        >>> result = graph_llm.invoke({"messages": [HumanMessage(content="Add 5 and two")]})  # Uses Google Gemini
    """
    logger.info(f"Building number adder agent graph (use_llm={use_llm})")
    
    if use_llm and not GEMINI_AVAILABLE:
        logger.warning(
            "LLM requested but langchain-google-genai not available. "
            "Falling back to regex extraction."
        )
        use_llm = False
    
    api_key = os.getenv("GOOGLE_API_KEY") or GOOGLE_API_KEY_FALLBACK
    if use_llm and not api_key:
        logger.warning(
            "LLM requested but GOOGLE_API_KEY not set. "
            "Falling back to regex extraction."
        )
        use_llm = False
    
    # Create the graph
    workflow = StateGraph(AgentState)
    
    # Create parse_input_node with the specified extraction method
    parse_input = create_parse_input_node(use_llm=use_llm)
    
    # Add nodes to the graph
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("calculate", calculate_sum_node)
    workflow.add_node("format_response", format_response_node)
    
    # Set the entry point
    workflow.set_entry_point("parse_input")
    
    # Add conditional edges
    # After parsing, decide what to do next
    workflow.add_conditional_edges(
        "parse_input",
        should_continue,
        {
            "calculate": "calculate",
            "format": "format_response",
            "end": END,
        },
    )
    
    # After calculating, always format the response
    workflow.add_edge("calculate", "format_response")
    
    # After formatting, end the graph
    workflow.add_edge("format_response", END)
    
    logger.info("Graph construction complete")
    
    # Compile the graph
    return workflow.compile()


def process_user_input(user_text: str, use_llm: bool = False) -> str:
    """
    Process user text input through the number adder agent.
    
    Args:
        user_text: Text input from the user containing numbers to add
        use_llm: If True, use Google Gemini for number extraction
        
    Returns:
        The agent's response as a string
    """
    logger.info(f"Processing user input: {user_text} (use_llm={use_llm})")
    
    # Build the agent
    agent = build_number_adder_agent(use_llm=use_llm)
    
    # Create initial state
    state = {
        "messages": [HumanMessage(content=user_text)],
        "number1": None,
        "number2": None,
        "result": None,
        "error": None,
    }
    
    # Invoke the agent
    result = agent.invoke(state)
    
    # Extract and return the response
    response = result["messages"][-1].content
    logger.info(f"Agent response: {response}")
    
    return response


def run_example():
    """
    Example usage of the number adder agent.
    
    This function demonstrates how to use the agent with different inputs.
    """
    logger.info("Starting number adder agent example")
    
    # Build the agent
    agent = build_number_adder_agent()
    
    # Example 1: Simple addition
    logger.info("=" * 50)
    logger.info("Example 1: Simple addition")
    logger.info("=" * 50)
    
    from langchain_core.messages import HumanMessage
    
    state1 = {
        "messages": [HumanMessage(content="Add 5 and 10")],
        "number1": None,
        "number2": None,
        "result": None,
        "error": None,
    }
    
    result1 = agent.invoke(state1)
    logger.info(f"Input: Add 5 and 10")
    logger.info(f"Result: {result1['messages'][-1].content}")
    print(f"\nInput: Add 5 and 10")
    print(f"Result: {result1['messages'][-1].content}\n")
    
    # Example 2: Decimal numbers
    logger.info("=" * 50)
    logger.info("Example 2: Decimal numbers")
    logger.info("=" * 50)
    
    state2 = {
        "messages": [HumanMessage(content="What is 3.5 plus 2.7?")],
        "number1": None,
        "number2": None,
        "result": None,
        "error": None,
    }
    
    result2 = agent.invoke(state2)
    logger.info(f"Input: What is 3.5 plus 2.7?")
    logger.info(f"Result: {result2['messages'][-1].content}")
    print(f"Input: What is 3.5 plus 2.7?")
    print(f"Result: {result2['messages'][-1].content}\n")
    
    # Example 3: Negative numbers
    logger.info("=" * 50)
    logger.info("Example 3: Negative numbers")
    logger.info("=" * 50)
    
    state3 = {
        "messages": [HumanMessage(content="Calculate -5 + 15")],
        "number1": None,
        "number2": None,
        "result": None,
        "error": None,
    }
    
    result3 = agent.invoke(state3)
    logger.info(f"Input: Calculate -5 + 15")
    logger.info(f"Result: {result3['messages'][-1].content}")
    print(f"Input: Calculate -5 + 15")
    print(f"Result: {result3['messages'][-1].content}\n")
    
    # Example 4: Error case - only one number
    logger.info("=" * 50)
    logger.info("Example 4: Error case")
    logger.info("=" * 50)
    
    state4 = {
        "messages": [HumanMessage(content="Add 5")],
        "number1": None,
        "number2": None,
        "result": None,
        "error": None,
    }
    
    result4 = agent.invoke(state4)
    logger.info(f"Input: Add 5")
    logger.info(f"Result: {result4['messages'][-1].content}")
    print(f"Input: Add 5")
    print(f"Result: {result4['messages'][-1].content}\n")
    
    logger.info("Example execution complete")


def main():
    """
    Main entry point for the learning script.
    
    Supports two modes:
    1. Interactive mode: Prompts user for input
    2. Command-line mode: Accepts text as argument
    
    Usage:
        # Interactive mode
        python learning/langgraph_number_adder.py
        
        # Command-line mode
        python learning/langgraph_number_adder.py "Add 5 and 10"
        
        # Run examples
        python learning/langgraph_number_adder.py --examples
    """
    parser = argparse.ArgumentParser(
        description="LangGraph Number Addition Agent - Add two numbers from text input",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive mode (prompts for input)
  python langgraph_number_adder.py
  
  # Command-line mode
  python langgraph_number_adder.py "Add 5 and 10"
  python langgraph_number_adder.py "What is 3.5 plus 2.7?"
  python langgraph_number_adder.py "Calculate -5 + 15"
  
  # Run built-in examples
  python langgraph_number_adder.py --examples
  
  # Use LLM for natural language understanding
  python langgraph_number_adder.py "Add 5 and two" --use-llm
  python langgraph_number_adder.py "What is three plus four?" --use-llm
        """,
    )
    parser.add_argument(
        "text",
        nargs="?",
        help="Text input containing two numbers to add (e.g., 'Add 5 and 10')",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Run built-in examples instead of processing user input",
    )
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Run in interactive mode (prompts for input)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        dest="use_llm",
        help="Use Google Gemini for number extraction (handles natural language like 'two', 'three'). Requires GOOGLE_API_KEY environment variable.",
    )
    
    args = parser.parse_args()
    
    try:
        # Run examples if requested
        if args.examples:
            logger.info("Running built-in examples")
            run_example()
            return
        
        # Get user input
        user_text = args.text
        
        # If no text provided and not explicitly interactive, prompt for input
        if not user_text and not args.interactive:
            # Check if input is available from stdin (piped input)
            if not sys.stdin.isatty():
                user_text = sys.stdin.read().strip()
            else:
                # Prompt interactively
                print("\n" + "=" * 60)
                print("LangGraph Number Addition Agent")
                print("=" * 60)
                print("Enter text with two numbers to add them together.")
                print("Examples: 'Add 5 and 10', 'What is 3.5 plus 2.7?'")
                if args.use_llm:
                    print("Using Google Gemini - can handle written numbers like 'two', 'three'")
                print("Type 'exit' or 'quit' to stop.\n")
                args.interactive = True
        
        # Interactive mode: keep prompting until user exits
        if args.interactive or (not user_text and sys.stdin.isatty()):
            while True:
                try:
                    if not user_text:
                        user_text = input("Enter your text: ").strip()
                    
                    if not user_text:
                        print("Please enter some text.")
                        user_text = None
                        continue
                    
                    # Check for exit commands
                    if user_text.lower() in ["exit", "quit", "q"]:
                        print("Goodbye!")
                        break
                    
                    # Process the input
                    print("\nProcessing...")
                    response = process_user_input(user_text, use_llm=args.use_llm)
                    print(f"\nResult: {response}\n")
                    
                    # Reset for next iteration
                    user_text = None
                    
                except KeyboardInterrupt:
                    print("\n\nGoodbye!")
                    break
                except EOFError:
                    print("\n\nGoodbye!")
                    break
        else:
            # Single input mode: process the provided text
            if not user_text:
                logger.error("No text input provided")
                parser.print_help()
                sys.exit(1)
            
            print(f"\nInput: {user_text}")
            if args.use_llm:
                print("Using Google Gemini for number extraction...")
            print("Processing...")
            response = process_user_input(user_text, use_llm=args.use_llm)
            print(f"Result: {response}\n")
            
    except Exception as e:
        logger.error(f"Error running agent: {e}", exc_info=True)
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

