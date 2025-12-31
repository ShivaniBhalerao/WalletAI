# LangGraph Learning Project

This directory contains learning examples for LangGraph, a framework for building stateful, multi-actor applications with LLMs.

## Number Addition Agent

The `langgraph_number_adder.py` file demonstrates a simple LangGraph agent that:
- Parses text input to extract two numbers
- Adds them together
- Returns a formatted response

### Key Concepts Demonstrated

1. **State Management**: Using TypedDict to define the agent's state
2. **Node Definitions**: Creating individual processing nodes
3. **Graph Construction**: Building a workflow with nodes and edges
4. **Conditional Routing**: Using conditional edges to control flow
5. **Error Handling**: Gracefully handling edge cases

### Installation

First, install the required dependencies:

```bash
cd backend
pip install langgraph langchain-core
```

Or if using uv (as this project does):

```bash
cd backend
uv pip install langgraph langchain-core
```

**For LLM-based extraction (optional):**

To use Claude Sonnet 3.5 for natural language number extraction (handles written numbers like "two", "three"):

```bash
pip install langchain-anthropic
```

Or with uv:

```bash
uv pip install langchain-anthropic
```

Then set your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="your-api-key-here"
```

**Note**: 
- The default implementation uses regex-based number extraction (no API key needed)
- For LLM-based extraction with Claude Sonnet 3.5 (handles natural language like "two", "three"), install `langchain-anthropic` and set the `ANTHROPIC_API_KEY` environment variable

### Running the Example

The script supports multiple ways to provide input:

#### 1. Interactive Mode (Default)
Prompts you for input interactively:

```bash
cd backend
python ../learning/langgraph_number_adder.py
```

Then enter your text when prompted:
```
Enter your text: Add 5 and 10
```

#### 2. Command-Line Argument
Pass text directly as an argument:

```bash
cd backend
python ../learning/langgraph_number_adder.py "Add 5 and 10"
python ../learning/langgraph_number_adder.py "What is 3.5 plus 2.7?"
python ../learning/langgraph_number_adder.py "Calculate -5 + 15"
```

#### 3. Pipe Input
Pipe text from another command:

```bash
echo "Add 10 and 20" | python ../learning/langgraph_number_adder.py
```

#### 4. Run Built-in Examples
See the agent in action with pre-configured examples:

```bash
cd backend
python ../learning/langgraph_number_adder.py --examples
```

#### 5. Use LLM for Natural Language Understanding
Use Claude Sonnet 3.5 to understand written numbers (e.g., "two", "three"):

```bash
# Set your Anthropic API key first
export ANTHROPIC_API_KEY="your-api-key-here"

# Use LLM mode
cd backend
python ../learning/langgraph_number_adder.py "Add 5 and two" --use-llm
python ../learning/langgraph_number_adder.py "What is three plus four?" --use-llm
```

#### 6. Help
See all available options:

```bash
python ../learning/langgraph_number_adder.py --help
```

### Example Usage

#### Basic Usage (Regex-based extraction)
```python
from learning.langgraph_number_adder import build_number_adder_agent
from langchain_core.messages import HumanMessage

# Build the agent
agent = build_number_adder_agent()

# Use it
state = {
    "messages": [HumanMessage(content="Add 5 and 10")],
    "number1": None,
    "number2": None,
    "result": None,
    "error": None,
}

result = agent.invoke(state)
print(result['messages'][-1].content)
# Output: "The sum of 5.0 and 10.0 is 15.0."
```

#### LLM-based Usage (Natural Language)
```python
from learning.langgraph_number_adder import build_number_adder_agent
from langchain_core.messages import HumanMessage
import os

# Set API key
os.environ["ANTHROPIC_API_KEY"] = "your-api-key"

# Build the agent with LLM support
agent = build_number_adder_agent(use_llm=True)

# Use it with natural language
state = {
    "messages": [HumanMessage(content="Add 5 and two")],
    "number1": None,
    "number2": None,
    "result": None,
    "error": None,
}

result = agent.invoke(state)
print(result['messages'][-1].content)
# Output: "The sum of 5.0 and 2.0 is 7.0."
```

### Graph Structure

```
[Entry] → parse_input_node → [Conditional] → calculate_sum_node → format_response_node → [End]
                                    ↓
                            format_response_node → [End]
```

### Learning Path

1. **Start here**: Run the example and see how it works
2. **Modify**: Try changing the number extraction logic
3. **Extend**: Add more operations (subtraction, multiplication, etc.)
4. **Advanced**: Use LLM mode to handle natural language numbers (e.g., "two", "three")
5. **Expert**: Integrate additional LLM features or build more complex agents

### Next Steps

- Learn about LangGraph's streaming capabilities
- Explore more complex state management
- Build multi-agent systems
- Integrate with tools and external APIs

### Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [LangGraph Tutorials](https://langchain-ai.github.io/langgraph/tutorials/)
- [LangChain Documentation](https://python.langchain.com/)

