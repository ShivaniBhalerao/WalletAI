"""
Unit tests for agent context management without requiring full database setup.

Tests that the context is properly managed during agent execution.
"""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage

from app.ai.tools.base import clear_context, current_session, current_user_id


class TestAgentContextManagement:
    """Tests for agent context management logic."""
    
    def test_context_cleared_initially(self) -> None:
        """Test that context is clear at the start of tests."""
        clear_context()
        
        assert current_session.get() is None
        assert current_user_id.get() is None
    
    def test_set_and_clear_context(self) -> None:
        """Test basic context setting and clearing."""
        from app.ai.tools.base import set_context
        import uuid
        from unittest.mock import MagicMock
        
        # Clear first
        clear_context()
        
        # Create mock session and user_id
        mock_session = MagicMock()
        test_user_id = uuid.uuid4()
        
        # Set context
        set_context(mock_session, test_user_id)
        
        # Verify context is set
        assert current_session.get() is not None
        assert current_user_id.get() == test_user_id
        
        # Clear context
        clear_context()
        
        # Verify context is cleared
        assert current_session.get() is None
        assert current_user_id.get() is None
    
    def test_context_available_in_tools_node(self) -> None:
        """Test that the call_tools_node sets context before tool execution."""
        import uuid
        from unittest.mock import MagicMock, patch
        from app.ai.agent import call_tools_node
        from app.ai.state import FinancialAgentState
        
        # Clear context first
        clear_context()
        
        # Create mock state
        mock_session = MagicMock()
        test_user_id = uuid.uuid4()
        
        state: FinancialAgentState = {
            "messages": [
                HumanMessage(content="Test"),
                AIMessage(
                    content="",
                    tool_calls=[
                        {
                            "name": "test_tool",
                            "args": {},
                            "id": "call_123",
                        }
                    ],
                ),
            ],
            "session": mock_session,
            "user_id": test_user_id,
            "context": {},
            "error": None,
        }
        
        # Mock ToolNode to verify context is set when it's called
        context_when_tool_node_invoked = {}
        
        def capture_context(*args, **kwargs):
            """Capture the context state when ToolNode is invoked."""
            context_when_tool_node_invoked["session"] = current_session.get()
            context_when_tool_node_invoked["user_id"] = current_user_id.get()
            # Return a minimal response
            return {"messages": state["messages"] + [AIMessage(content="Tool result")]}
        
        with patch("app.ai.agent.ToolNode") as mock_tool_node_class:
            mock_tool_node = MagicMock()
            mock_tool_node.invoke.side_effect = capture_context
            mock_tool_node_class.return_value = mock_tool_node
            
            # Execute the tools node
            result = call_tools_node(state)
            
            # Verify that context was set when ToolNode was invoked
            assert context_when_tool_node_invoked["session"] is not None
            assert context_when_tool_node_invoked["user_id"] == test_user_id
            
            # Verify result is returned
            assert result is not None
            assert "messages" in result
    
    def test_process_message_sets_and_clears_context(self) -> None:
        """Test that process_message sets context before execution and clears after."""
        import uuid
        from unittest.mock import MagicMock, patch
        from app.ai.agent import process_message
        
        # Clear context first
        clear_context()
        
        mock_session = MagicMock()
        test_user_id = uuid.uuid4()
        messages = [HumanMessage(content="Test message")]
        
        # Mock the agent graph
        with patch("app.ai.agent.build_financial_agent") as mock_build:
            mock_agent = MagicMock()
            mock_agent.invoke.return_value = {
                "messages": messages + [AIMessage(content="Response")],
                "session": mock_session,
                "user_id": test_user_id,
                "context": {},
                "error": None,
            }
            mock_build.return_value = mock_agent
            
            # Process message
            result = process_message(
                user_id=test_user_id,
                messages=messages,
                session=mock_session,
            )
            
            # Verify we got a result
            assert result is not None
            
            # IMPORTANT: Verify context is cleared after execution
            assert current_session.get() is None
            assert current_user_id.get() is None
    
    def test_process_message_clears_context_on_error(self) -> None:
        """Test that context is cleared even when an error occurs."""
        import uuid
        from unittest.mock import MagicMock, patch
        from app.ai.agent import process_message
        
        # Clear context first
        clear_context()
        
        mock_session = MagicMock()
        test_user_id = uuid.uuid4()
        messages = [HumanMessage(content="Test message")]
        
        # Mock the agent graph to raise an error
        with patch("app.ai.agent.build_financial_agent") as mock_build:
            mock_agent = MagicMock()
            mock_agent.invoke.side_effect = Exception("Test error")
            mock_build.return_value = mock_agent
            
            # Process message (should handle error)
            result = process_message(
                user_id=test_user_id,
                messages=messages,
                session=mock_session,
            )
            
            # Verify error was handled
            assert result is not None
            assert "error" in result
            
            # IMPORTANT: Verify context is cleared even after error
            assert current_session.get() is None
            assert current_user_id.get() is None
