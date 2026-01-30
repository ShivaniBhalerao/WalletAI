"""
Unit tests for get_transactions_by_account tool.

Tests the account-based transaction query functionality with proper database setup.
"""

import uuid
from datetime import date, timedelta

import pytest
from sqlmodel import Session

from app.ai.tools import get_transactions_by_account, set_context
from app.models import Account, Transaction, User, UserCreate


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user for financial queries."""
    from app import crud
    
    user_create = UserCreate(
        email=f"testuser_{uuid.uuid4()}@example.com",
        password="testpassword123",
        full_name="Test User",
    )
    user = crud.create_user(session=db, user_create=user_create)
    return user


@pytest.fixture
def test_accounts(db: Session, test_user: User) -> list[Account]:
    """Create test accounts of different types."""
    accounts = [
        Account(
            user_id=test_user.id,
            name="My Checking",
            official_name="Test Checking Account",
            type="depository",
            current_balance=5000.0,
            currency="USD",
            plaid_account_id="test-checking-123",
        ),
        Account(
            user_id=test_user.id,
            name="Savings Account",
            official_name="Test Savings Account",
            type="depository",
            current_balance=10000.0,
            currency="USD",
            plaid_account_id="test-savings-456",
        ),
        Account(
            user_id=test_user.id,
            name="Credit Card",
            official_name="Test Credit Card",
            type="credit",
            current_balance=-1500.0,
            currency="USD",
            plaid_account_id="test-credit-789",
        ),
    ]
    
    for account in accounts:
        db.add(account)
    db.commit()
    
    for account in accounts:
        db.refresh(account)
    
    return accounts


@pytest.fixture
def test_transactions(db: Session, test_accounts: list[Account]) -> list[Transaction]:
    """Create test transactions across different account types."""
    today = date.today()
    
    checking_account = test_accounts[0]  # depository
    credit_account = test_accounts[2]  # credit
    
    transactions = [
        # Checking account transactions
        Transaction(
            account_id=checking_account.id,
            amount=52.30,
            auth_date=today - timedelta(days=1),
            merchant_name="Whole Foods",
            category="Food and Drink, Groceries",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-check-1",
        ),
        Transaction(
            account_id=checking_account.id,
            amount=45.00,
            auth_date=today - timedelta(days=2),
            merchant_name="Restaurant ABC",
            category="Food and Drink, Restaurants",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-check-2",
        ),
        # Credit card transactions
        Transaction(
            account_id=credit_account.id,
            amount=120.00,
            auth_date=today - timedelta(days=1),
            merchant_name="Amazon",
            category="Shopping, Online Shopping",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-credit-1",
        ),
        Transaction(
            account_id=credit_account.id,
            amount=85.50,
            auth_date=today - timedelta(days=3),
            merchant_name="Target",
            category="Shopping, General Merchandise",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-credit-2",
        ),
        # Old checking transaction (outside default range)
        Transaction(
            account_id=checking_account.id,
            amount=200.00,
            auth_date=today - timedelta(days=40),
            merchant_name="Old Store",
            category="Shopping",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-check-old",
        ),
    ]
    
    for txn in transactions:
        db.add(txn)
    db.commit()
    
    for txn in transactions:
        db.refresh(txn)
    
    return transactions


class TestGetTransactionsByAccount:
    """Tests for get_transactions_by_account tool."""
    
    def test_get_transactions_depository_account(
        self,
        db: Session,
        test_user: User,
        test_accounts: list[Account],
        test_transactions: list[Transaction],
    ) -> None:
        """Test getting transactions from depository account (checking/savings)."""
        # Set context for tool execution
        set_context(db, test_user.id)
        
        # Call the tool
        result = get_transactions_by_account.invoke({"account_type": "depository", "limit": 10, "days_back": 30})
        
        # Assertions
        assert result["account_type"] == "depository"
        assert result["accounts_found"] == 2  # Both checking and savings are depository
        assert result["transaction_count"] == 2  # 2 recent transactions in depository accounts
        assert result["total_amount"] == 97.30  # 52.30 + 45.00
        
        # Check transaction details
        assert len(result["transactions"]) == 2
        assert all("merchant" in txn for txn in result["transactions"])
    
    def test_get_transactions_credit_account(
        self,
        db: Session,
        test_user: User,
        test_accounts: list[Account],
        test_transactions: list[Transaction],
    ) -> None:
        """Test getting transactions from credit card account."""
        # Set context for tool execution
        set_context(db, test_user.id)
        
        # Call the tool
        result = get_transactions_by_account.invoke({"account_type": "credit", "limit": 10, "days_back": 30})
        
        # Assertions
        assert result["account_type"] == "credit"
        assert result["accounts_found"] == 1
        assert result["transaction_count"] == 2  # 2 credit card transactions
        assert result["total_amount"] == 205.50  # 120.00 + 85.50
        
        # Check transaction details
        assert len(result["transactions"]) == 2
        merchants = [txn["merchant"] for txn in result["transactions"]]
        assert "Amazon" in merchants
        assert "Target" in merchants
    
    def test_get_transactions_no_account_found(
        self,
        db: Session,
        test_user: User,
        test_accounts: list[Account],
    ) -> None:
        """Test querying for non-existent account type."""
        # Set context for tool execution
        set_context(db, test_user.id)
        
        # Call the tool with non-existent account type
        result = get_transactions_by_account.invoke({"account_type": "investment", "limit": 10, "days_back": 30})
        
        # Assertions
        assert result["accounts_found"] == 0
        assert result["transaction_count"] == 0
        assert result["total_amount"] == 0.0
        assert len(result["transactions"]) == 0
        assert "message" in result
    
    def test_get_transactions_with_date_filter(
        self,
        db: Session,
        test_user: User,
        test_accounts: list[Account],
        test_transactions: list[Transaction],
    ) -> None:
        """Test that old transactions are filtered out by days_back parameter."""
        # Set context for tool execution
        set_context(db, test_user.id)
        
        # Call the tool with only 5 days back (should exclude the 40-day old transaction)
        result = get_transactions_by_account.invoke({"account_type": "depository", "limit": 10, "days_back": 5})
        
        # Assertions - should only get recent transactions
        assert result["transaction_count"] == 2
        
        # The old transaction (200.00) should not be included
        assert result["total_amount"] == 97.30
    
    def test_get_transactions_with_limit(
        self,
        db: Session,
        test_user: User,
        test_accounts: list[Account],
        test_transactions: list[Transaction],
    ) -> None:
        """Test that limit parameter restricts number of transactions returned."""
        # Set context for tool execution
        set_context(db, test_user.id)
        
        # Call the tool with limit of 1
        result = get_transactions_by_account.invoke({"account_type": "credit", "limit": 1, "days_back": 30})
        
        # Assertions
        assert result["transaction_count"] == 1  # Limited to 1
        assert len(result["transactions"]) == 1
    
    def test_get_transactions_case_insensitive(
        self,
        db: Session,
        test_user: User,
        test_accounts: list[Account],
        test_transactions: list[Transaction],
    ) -> None:
        """Test that account type matching is case-insensitive."""
        # Set context for tool execution
        set_context(db, test_user.id)
        
        # Call the tool with uppercase account type
        result = get_transactions_by_account.invoke({"account_type": "CREDIT", "limit": 10, "days_back": 30})
        
        # Assertions - should still find credit accounts
        assert result["accounts_found"] == 1
        assert result["transaction_count"] == 2
