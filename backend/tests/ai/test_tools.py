"""
Unit tests for AI tools that query financial data.

Tests all tool functions with proper database setup and mock data.
"""

import uuid
from datetime import date, timedelta

import pytest
from sqlmodel import Session

from app.ai.tools import (
    compare_spending_periods,
    get_category_breakdown,
    get_month_date_range,
    get_transactions,
    parse_time_period,
    query_spending_by_category,
    query_spending_by_time_period,
)
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
    """Create test transactions for querying."""
    today = date.today()
    transactions = [
        # Groceries transactions
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
            amount=32.50,
            auth_date=today - timedelta(days=5),
            merchant_name="Local Market",
            category="Food and Drink, Groceries",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-3",
        ),
        # Dining transactions
        Transaction(
            account_id=test_account.id,
            amount=45.00,
            auth_date=today - timedelta(days=2),
            merchant_name="Restaurant ABC",
            category="Food and Drink, Restaurants",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-4",
        ),
        # Transportation
        Transaction(
            account_id=test_account.id,
            amount=60.00,
            auth_date=today - timedelta(days=4),
            merchant_name="Gas Station",
            category="Travel, Gas Stations",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-5",
        ),
        # Old transaction from last month
        Transaction(
            account_id=test_account.id,
            amount=100.00,
            auth_date=today - timedelta(days=35),
            merchant_name="Old Store",
            category="Shopping",
            pending=False,
            currency="USD",
            plaid_transaction_id="txn-6",
        ),
    ]
    
    for txn in transactions:
        db.add(txn)
    db.commit()
    
    for txn in transactions:
        db.refresh(txn)
    
    return transactions


class TestQuerySpendingByCategory:
    """Tests for query_spending_by_category function."""
    
    def test_query_groceries_success(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test querying grocery spending successfully."""
        result = query_spending_by_category(
            session=db,
            user_id=test_user.id,
            category="Groceries",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        assert result["category"] == "Groceries"
        assert result["total_amount"] == 169.80  # 52.30 + 85.00 + 32.50
        assert result["transaction_count"] == 3
        assert len(result["top_merchants"]) == 3
        assert result["top_merchants"][0]["name"] == "Trader Joe's"
        assert result["top_merchants"][0]["amount"] == 85.00
    
    def test_query_no_transactions(
        self,
        db: Session,
        test_user: User,
    ) -> None:
        """Test querying category with no transactions."""
        result = query_spending_by_category(
            session=db,
            user_id=test_user.id,
            category="Electronics",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        assert result["total_amount"] == 0.0
        assert result["transaction_count"] == 0
        assert len(result["top_merchants"]) == 0
    
    def test_query_with_date_filter(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test querying with date range filter."""
        result = query_spending_by_category(
            session=db,
            user_id=test_user.id,
            category="Groceries",
            start_date=date.today() - timedelta(days=2),
            end_date=date.today(),
        )
        
        # Should only include the most recent grocery transaction
        assert result["total_amount"] == 52.30
        assert result["transaction_count"] == 1


class TestQuerySpendingByTimePeriod:
    """Tests for query_spending_by_time_period function."""
    
    def test_query_week_spending(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test querying spending for the past week."""
        result = query_spending_by_time_period(
            session=db,
            user_id=test_user.id,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        # Total of all recent transactions (excluding the 35-day old one)
        assert result["total_amount"] == 274.80
        assert result["transaction_count"] == 5
        assert "Food and Drink, Groceries" in result["category_breakdown"]
        assert result["category_breakdown"]["Food and Drink, Groceries"] == 169.80
    
    def test_query_empty_period(
        self,
        db: Session,
        test_user: User,
    ) -> None:
        """Test querying period with no transactions."""
        result = query_spending_by_time_period(
            session=db,
            user_id=test_user.id,
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() - timedelta(days=100),
        )
        
        assert result["total_amount"] == 0.0
        assert result["transaction_count"] == 0
        assert len(result["category_breakdown"]) == 0


class TestCompareSpendingPeriods:
    """Tests for compare_spending_periods function."""
    
    def test_compare_periods(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test comparing spending between two periods."""
        today = date.today()
        
        result = compare_spending_periods(
            session=db,
            user_id=test_user.id,
            period1_start=today - timedelta(days=7),
            period1_end=today,
            period2_start=today - timedelta(days=40),
            period2_end=today - timedelta(days=30),
        )
        
        assert "period1" in result
        assert "period2" in result
        assert "difference" in result
        assert "percent_change" in result
        assert "category_changes" in result
        
        # Period 1 should have more spending than period 2
        assert result["period1"]["total"] > result["period2"]["total"]
        assert result["difference"] > 0


class TestGetCategoryBreakdown:
    """Tests for get_category_breakdown function."""
    
    def test_get_breakdown_with_transactions(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test getting category breakdown with transactions."""
        result = get_category_breakdown(
            session=db,
            user_id=test_user.id,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
        )
        
        assert result["total_amount"] == 274.80
        assert len(result["categories"]) > 0
        
        # Check that percentages add up to approximately 100
        total_percentage = sum(cat["percentage"] for cat in result["categories"])
        assert 99.0 <= total_percentage <= 101.0
        
        # Groceries should be the largest category
        groceries = next((c for c in result["categories"] if "Groceries" in c["category"]), None)
        assert groceries is not None
        assert groceries["amount"] == 169.80
    
    def test_get_breakdown_empty(
        self,
        db: Session,
        test_user: User,
    ) -> None:
        """Test getting category breakdown with no transactions."""
        result = get_category_breakdown(
            session=db,
            user_id=test_user.id,
            start_date=date.today() - timedelta(days=365),
            end_date=date.today() - timedelta(days=100),
        )
        
        assert result["total_amount"] == 0.0
        assert len(result["categories"]) == 0


class TestGetTransactions:
    """Tests for get_transactions function."""
    
    def test_get_transactions_all(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test getting all recent transactions."""
        result = get_transactions(
            session=db,
            user_id=test_user.id,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            limit=10,
        )
        
        assert len(result) == 5
        # Should be ordered by date descending
        assert result[0]["date"] > result[-1]["date"]
    
    def test_get_transactions_with_category_filter(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test getting transactions filtered by category."""
        result = get_transactions(
            session=db,
            user_id=test_user.id,
            category="Groceries",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            limit=10,
        )
        
        assert len(result) == 3
        assert all("Groceries" in txn["category"] for txn in result)
    
    def test_get_transactions_with_merchant_filter(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test getting transactions filtered by merchant."""
        result = get_transactions(
            session=db,
            user_id=test_user.id,
            merchant="Whole",
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            limit=10,
        )
        
        assert len(result) == 1
        assert "Whole" in result[0]["merchant"]
    
    def test_get_transactions_with_limit(
        self,
        db: Session,
        test_user: User,
        test_transactions: list[Transaction],
    ) -> None:
        """Test getting transactions with limit."""
        result = get_transactions(
            session=db,
            user_id=test_user.id,
            start_date=date.today() - timedelta(days=7),
            end_date=date.today(),
            limit=3,
        )
        
        assert len(result) == 3


class TestUtilityFunctions:
    """Tests for utility functions."""
    
    def test_get_month_date_range_current(self) -> None:
        """Test getting current month date range."""
        start, end = get_month_date_range(0)
        
        assert start.day == 1
        assert start.month == date.today().month
        assert end >= start
    
    def test_get_month_date_range_last_month(self) -> None:
        """Test getting last month date range."""
        start, end = get_month_date_range(1)
        
        assert start.day == 1
        assert end >= start
        # End should be last day of the month
        assert (end + timedelta(days=1)).day == 1
    
    def test_parse_time_period_this_month(self) -> None:
        """Test parsing 'this_month' time period."""
        start, end = parse_time_period("this_month")
        
        assert start.day == 1
        assert start.month == date.today().month
    
    def test_parse_time_period_last_month(self) -> None:
        """Test parsing 'last_month' time period."""
        start, end = parse_time_period("last_month")
        
        assert start.day == 1
        assert end >= start
    
    def test_parse_time_period_today(self) -> None:
        """Test parsing 'today' time period."""
        start, end = parse_time_period("today")
        
        assert start == date.today()
        assert end == date.today()
    
    def test_parse_time_period_this_year(self) -> None:
        """Test parsing 'this_year' time period."""
        start, end = parse_time_period("this_year")
        
        assert start == date(date.today().year, 1, 1)
        assert end == date.today()
    
    def test_parse_time_period_invalid(self) -> None:
        """Test parsing invalid time period defaults to this month."""
        start, end = parse_time_period("invalid_period")
        
        # Should default to current month
        assert start.day == 1
        assert start.month == date.today().month

