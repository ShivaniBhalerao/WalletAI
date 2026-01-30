"""
Unit tests for the Financial AI Agent.

Tests the full agent execution flow including context management
and tool execution through the LangGraph workflow.
"""

import uuid
from datetime import date, timedelta
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.messages import AIMessage, HumanMessage
from sqlmodel import Session

from app.ai.agent import build_financial_agent, process_message
from app.ai.tools.base import clear_context, current_session, current_user_id
from app.models import Account, Transaction, User, UserCreate


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user for agent queries."""
    from app import crud
    
    user_create = UserCreate(
        email=f"testuser_{uuid.uuid4()}@example.com",
        password="testpassword123",
        full_name="Test Agent User",
    )
    user = crud.create_user(session=db, user_create=user_create)
    return user


@pytest.fixture
def test_account(db: Session, test_user: User) -> Account:
    """Create a test account for transactions."""
    account = Account(
        user_id=test_user.id,
        name="Test Checking",
        official_name="Test Checking Account",
        type="depository",
        current_balance=1000.0,
        currency="USD",
        plaid_account_id="test-account-123",
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@pytest.fixture
def test_transactions(db: Session, test_account: Account) -> list[Transaction]:
    """Create test transactions for the agent to query."""
    today = date.today()
    transactions = [
        Transaction(
            account_id=test_account.id,
            amount=52.30,
            auth_date=today - timedelta(days=1),
            merchant_name="Whole Foods",
            category="Food and Drink, Groceries",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-1",
        ),
        Transaction(
            account_id=test_account.id,
            amount=85.00,
            auth_date=today - timedelta(days=3),
            merchant_name="Trader Joe's",
            category="Food and Drink, Groceries",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-2",
        ),
        Transaction(
            account_id=test_account.id,
            amount=45.00,
            auth_date=today - timedelta(days=2),
            merchant_name="Restaurant ABC",
            category="Food and Drink, Restaurants",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-3",
        ),
    ]
    
    for txn in transactions:
        db.add(txn)
    db.commit()
    
    for txn in transactions:
        db.refresh(txn)
    
    return transactions


class TestAgentContextManagement:
    """Tests for agent context management during tool execution."""
    
    def test_context_set_before_tool_execution(
        self,
        db: Session,
        test_user: User,
        test_account: Account,
        test_transactions: list[Transaction],
    ) -> None:
        """Test that context is properly set when tools are executed by the agent."""
        # Ensure context is clear before test
        clear_context()
        
        # Create a message that will trigger tool usage
        messages = [HumanMessage(content="Show my grocery spending")]
        
        # Mock the LLM to avoid actual API calls
        with patch("app.ai.agent.ChatGoogleGenerativeAI") as mock_llm_class:
            # Create a mock LLM instance
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            
            # First call: LLM decides to use a tool
            tool_call_message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_transactions_by_category",
                        "args": {"category": "groceries", "limit": 20, "days_back": 30},
                        "id": "call_123",
                    }
                ],
            )
            
            # Second call: LLM responds with the tool results
            response_message = AIMessage(
                content="You spent $137.30 on groceries in the last 30 days. "
                       "Your main grocery stores were Trader Joe's ($85.00) and Whole Foods ($52.30)."
            )
            
            # Configure mock to return these messages in sequence
            mock_llm.invoke.side_effect = [tool_call_message, response_message]
            mock_llm.bind_tools.return_value = mock_llm
            
            # Process the message through the agent
            result = process_message(
                user_id=test_user.id,
                messages=messages,
                session=db,
            )
            
            # Verify that we got a response
            assert result is not None
            assert "messages" in result
            assert len(result["messages"]) > 0
            
            # Verify that the context was cleared after execution
            # (Context should be None outside of agent execution)
            assert current_session.get() is None
            assert current_user_id.get() is None
    
    def test_context_cleared_after_error(
        self,
        db: Session,
        test_user: User,
    ) -> None:
        """Test that context is cleared even when an error occurs during execution."""
        # Ensure context is clear before test
        clear_context()
        
        messages = [HumanMessage(content="Test message")]
        
        # Mock the LLM to raise an error
        with patch("app.ai.agent.ChatGoogleGenerativeAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            mock_llm.bind_tools.return_value = mock_llm
            mock_llm.invoke.side_effect = Exception("Test error")
            
            # Process the message (should handle the error gracefully)
            result = process_message(
                user_id=test_user.id,
                messages=messages,
                session=db,
            )
            
            # Verify error was handled
            assert result is not None
            assert "error" in result
            
            # Verify that the context was cleared even after error
            assert current_session.get() is None
            assert current_user_id.get() is None
    
    def test_agent_graph_builds_successfully(self) -> None:
        """Test that the agent graph builds without errors."""
        # Mock the configuration validation
        with patch("app.ai.agent.AIConfig") as mock_config:
            mock_config.validate_config.return_value = True
            mock_config.GOOGLE_API_KEY = "test-key"
            mock_config.get_model_kwargs.return_value = {
                "model": "gemini-2.0-flash-exp",
                "temperature": 0.7,
            }
            
            # Build the agent
            agent = build_financial_agent()
            
            # Verify the agent was created
            assert agent is not None
    
    def test_multiple_tool_calls_maintain_context(
        self,
        db: Session,
        test_user: User,
        test_account: Account,
        test_transactions: list[Transaction],
    ) -> None:
        """Test that context persists across multiple tool calls in one turn."""
        # Ensure context is clear before test
        clear_context()
        
        messages = [HumanMessage(content="Compare my grocery and restaurant spending")]
        
        # Mock the LLM to simulate multiple tool calls
        with patch("app.ai.agent.ChatGoogleGenerativeAI") as mock_llm_class:
            mock_llm = MagicMock()
            mock_llm_class.return_value = mock_llm
            
            # First call: LLM decides to use multiple tools
            tool_call_message = AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": "get_transactions_by_category",
                        "args": {"category": "groceries", "limit": 20, "days_back": 30},
                        "id": "call_123",
                    },
                    {
                        "name": "get_transactions_by_category",
                        "args": {"category": "restaurants", "limit": 20, "days_back": 30},
                        "id": "call_456",
                    },
                ],
            )
            
            # Second call: LLM responds with comparison
            response_message = AIMessage(
                content="You spent $137.30 on groceries and $45.00 on restaurants. "
                       "Your grocery spending is higher."
            )
            
            # Configure mock
            mock_llm.invoke.side_effect = [tool_call_message, response_message]
            mock_llm.bind_tools.return_value = mock_llm
            
            # Process the message
            result = process_message(
                user_id=test_user.id,
                messages=messages,
                session=db,
            )
            
            # Verify success
            assert result is not None
            assert "error" not in result or result["error"] is None
            
            # Verify context was cleared after execution
            assert current_session.get() is None
            assert current_user_id.get() is None


class TestAgentIntegration:
    """Integration tests for the full agent workflow."""
    
    @pytest.mark.skipif(
        True,  # Skip by default as it requires actual API key
        reason="Requires actual Google API key - enable for integration testing"
    )
    def test_real_agent_execution(
        self,
        db: Session,
        test_user: User,
        test_account: Account,
        test_transactions: list[Transaction],
    ) -> None:
        """
        Integration test with real LLM (disabled by default).
        
        To run this test:
        1. Set GOOGLE_API_KEY environment variable
        2. Change skipif condition to False
        3. Run: pytest -k test_real_agent_execution
        """
        messages = [HumanMessage(content="How much did I spend on groceries?")]
        
        result = process_message(
            user_id=test_user.id,
            messages=messages,
            session=db,
        )
        
        # Verify we got a response
        assert result is not None
        assert len(result["messages"]) > 0
        
        # The last message should be from the AI
        last_message = result["messages"][-1]
        assert isinstance(last_message, AIMessage)
        assert len(last_message.content) > 0
