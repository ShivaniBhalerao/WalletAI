"""
Unit tests for DatabaseService.

Tests all methods of DatabaseService with proper database setup and teardown.
"""

import uuid
from datetime import date, datetime
from typing import Generator

import pytest
from sqlmodel import Session, delete

from app.core.db_service import DatabaseService, DatabaseServiceError
from app.models import Account, PlaidItem, Transaction, User, UserCreate


@pytest.fixture
def test_user(db: Session) -> User:
    """Create a test user for database operations."""
    from app import crud
    
    user_create = UserCreate(
        email=f"testuser_{uuid.uuid4()}@example.com",
        password="testpassword123",
        full_name="Test User",
    )
    user = crud.create_user(session=db, user_create=user_create)
    return user


@pytest.fixture
def db_service(db: Session) -> DatabaseService:
    """Create a DatabaseService instance for testing."""
    return DatabaseService(db)


@pytest.fixture
def test_plaid_item(
    test_user: User,
    db_service: DatabaseService,
) -> PlaidItem:
    """Create a test PlaidItem for database operations."""
    plaid_item = db_service.create_plaid_item(
        user_id=test_user.id,
        item_id="item-test-123",
        access_token="access-sandbox-test-token",
        institution_name="Test Bank",
    )
    return plaid_item


class TestCreatePlaidItem:
    """Tests for create_plaid_item method."""
    
    def test_create_plaid_item_success(
        self,
        db_service: DatabaseService,
        test_user: User,
    ) -> None:
        """Test successful PlaidItem creation."""
        plaid_item = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-123",
            access_token="access-token-123",
            institution_name="Chase Bank",
        )
        
        assert plaid_item.id is not None
        assert plaid_item.user_id == test_user.id
        assert plaid_item.item_id == "item-123"
        assert plaid_item.access_token == "access-token-123"
        assert plaid_item.institution_name == "Chase Bank"
        assert plaid_item.cursor is None
    
    def test_create_plaid_item_invalid_user(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test PlaidItem creation with invalid user ID."""
        with pytest.raises(DatabaseServiceError):
            db_service.create_plaid_item(
                user_id=uuid.uuid4(),  # Non-existent user
                item_id="item-123",
                access_token="access-token-123",
                institution_name="Test Bank",
            )


class TestGetPlaidItemsForUser:
    """Tests for get_plaid_items_for_user method."""
    
    def test_get_plaid_items_success(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test retrieving PlaidItems for a user."""
        plaid_items = db_service.get_plaid_items_for_user(test_user.id)
        
        assert len(plaid_items) >= 1
        assert any(item.id == test_plaid_item.id for item in plaid_items)
    
    def test_get_plaid_items_no_items(
        self,
        db_service: DatabaseService,
        test_user: User,
    ) -> None:
        """Test retrieving PlaidItems when user has none."""
        # Create a new user without any PlaidItems
        from app import crud
        
        new_user_create = UserCreate(
            email=f"newuser_{uuid.uuid4()}@example.com",
            password="testpassword123",
            full_name="New User",
        )
        new_user = crud.create_user(session=db_service.session, user_create=new_user_create)
        
        plaid_items = db_service.get_plaid_items_for_user(new_user.id)
        
        assert len(plaid_items) == 0
    
    def test_get_plaid_items_multiple(
        self,
        db_service: DatabaseService,
        test_user: User,
    ) -> None:
        """Test retrieving multiple PlaidItems for a user."""
        # Create multiple PlaidItems
        item1 = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-multi-1",
            access_token="access-token-1",
            institution_name="Bank 1",
        )
        item2 = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-multi-2",
            access_token="access-token-2",
            institution_name="Bank 2",
        )
        
        plaid_items = db_service.get_plaid_items_for_user(test_user.id)
        
        assert len(plaid_items) >= 2
        item_ids = [item.id for item in plaid_items]
        assert item1.id in item_ids
        assert item2.id in item_ids


class TestGetPlaidItemById:
    """Tests for get_plaid_item_by_id method."""
    
    def test_get_plaid_item_success(
        self,
        db_service: DatabaseService,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test retrieving a PlaidItem by ID."""
        plaid_item = db_service.get_plaid_item_by_id(test_plaid_item.id)
        
        assert plaid_item is not None
        assert plaid_item.id == test_plaid_item.id
        assert plaid_item.item_id == test_plaid_item.item_id
    
    def test_get_plaid_item_not_found(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test retrieving a non-existent PlaidItem."""
        plaid_item = db_service.get_plaid_item_by_id(uuid.uuid4())
        
        assert plaid_item is None


class TestUpsertAccounts:
    """Tests for upsert_accounts method."""
    
    def test_upsert_accounts_create_new(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test creating new accounts."""
        accounts_data = [
            {
                "account_id": "account-1",
                "name": "Checking",
                "official_name": "Plaid Gold Standard Checking",
                "type": "depository",
                "balances": {
                    "current": 100.0,
                    "iso_currency_code": "USD",
                },
            },
            {
                "account_id": "account-2",
                "name": "Savings",
                "official_name": "Plaid Silver Standard Savings",
                "type": "depository",
                "balances": {
                    "current": 200.0,
                    "iso_currency_code": "USD",
                },
            },
        ]
        
        accounts = db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        assert len(accounts) == 2
        assert accounts[0].plaid_account_id == "account-1"
        assert accounts[0].name == "Checking"
        assert accounts[0].current_balance == 100.0
        assert accounts[0].currency == "USD"
        assert accounts[1].plaid_account_id == "account-2"
    
    def test_upsert_accounts_update_existing(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test updating existing accounts."""
        # Create initial account
        initial_data = [
            {
                "account_id": "account-update-1",
                "name": "Checking",
                "official_name": "Original Name",
                "type": "depository",
                "balances": {
                    "current": 100.0,
                    "iso_currency_code": "USD",
                },
            },
        ]
        
        initial_accounts = db_service.upsert_accounts(
            accounts=initial_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        initial_id = initial_accounts[0].id
        
        # Update with new data
        updated_data = [
            {
                "account_id": "account-update-1",
                "name": "Updated Checking",
                "official_name": "Updated Name",
                "type": "depository",
                "balances": {
                    "current": 250.0,
                    "iso_currency_code": "USD",
                },
            },
        ]
        
        updated_accounts = db_service.upsert_accounts(
            accounts=updated_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        assert len(updated_accounts) == 1
        assert updated_accounts[0].id == initial_id  # Same ID
        assert updated_accounts[0].name == "Updated Checking"
        assert updated_accounts[0].current_balance == 250.0
    
    def test_upsert_accounts_empty_list(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test upserting empty account list."""
        accounts = db_service.upsert_accounts(
            accounts=[],
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        assert len(accounts) == 0


class TestUpsertTransactions:
    """Tests for upsert_transactions method."""
    
    def test_upsert_transactions_create_new(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test creating new transactions."""
        # First create an account
        accounts_data = [
            {
                "account_id": "account-txn-1",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        
        accounts = db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        account_mapping = {"account-txn-1": accounts[0].id}
        
        # Create transactions
        transactions_data = [
            {
                "transaction_id": "txn-1",
                "account_id": "account-txn-1",
                "amount": 25.50,
                "date": "2024-01-15",
                "merchant_name": "Starbucks",
                "pending": False,
                "category": ["Food and Drink", "Coffee Shop"],
            },
            {
                "transaction_id": "txn-2",
                "account_id": "account-txn-1",
                "amount": 100.00,
                "date": "2024-01-16",
                "name": "Whole Foods",  # Test fallback to 'name'
                "pending": True,
                "category": ["Shops", "Groceries"],
            },
        ]
        
        transactions = db_service.upsert_transactions(
            transactions=transactions_data,
            account_mapping=account_mapping,
        )
        
        assert len(transactions) == 2
        assert transactions[0].plaid_transaction_id == "txn-1"
        assert transactions[0].amount == 25.50
        assert transactions[0].merchant_name == "Starbucks"
        assert transactions[0].pending is False
        assert transactions[0].category == "Food and Drink, Coffee Shop"
        assert transactions[1].merchant_name == "Whole Foods"
    
    def test_upsert_transactions_update_existing(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test updating existing transactions."""
        # Create account
        accounts_data = [
            {
                "account_id": "account-txn-update",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        
        accounts = db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        account_mapping = {"account-txn-update": accounts[0].id}
        
        # Create initial transaction
        initial_data = [
            {
                "transaction_id": "txn-update-1",
                "account_id": "account-txn-update",
                "amount": 25.50,
                "date": "2024-01-15",
                "merchant_name": "Starbucks",
                "pending": True,
                "category": ["Food and Drink"],
            },
        ]
        
        initial_transactions = db_service.upsert_transactions(
            transactions=initial_data,
            account_mapping=account_mapping,
        )
        
        initial_id = initial_transactions[0].id
        
        # Update transaction (e.g., pending -> cleared)
        updated_data = [
            {
                "transaction_id": "txn-update-1",
                "account_id": "account-txn-update",
                "amount": 25.50,
                "date": "2024-01-15",
                "merchant_name": "Starbucks",
                "pending": False,  # Changed
                "category": ["Food and Drink", "Coffee Shop"],  # More specific
            },
        ]
        
        updated_transactions = db_service.upsert_transactions(
            transactions=updated_data,
            account_mapping=account_mapping,
        )
        
        assert len(updated_transactions) == 1
        assert updated_transactions[0].id == initial_id  # Same ID
        assert updated_transactions[0].pending is False  # Updated
        assert "Coffee Shop" in updated_transactions[0].category  # Updated
    
    def test_upsert_transactions_missing_account(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test upserting transactions with missing account mapping."""
        transactions_data = [
            {
                "transaction_id": "txn-orphan",
                "account_id": "account-nonexistent",
                "amount": 25.50,
                "date": "2024-01-15",
                "merchant_name": "Test",
                "pending": False,
                "category": ["Other"],
            },
        ]
        
        # Should skip the transaction without error
        transactions = db_service.upsert_transactions(
            transactions=transactions_data,
            account_mapping={},
        )
        
        assert len(transactions) == 0


class TestUpdateSyncCursor:
    """Tests for update_sync_cursor method."""
    
    def test_update_sync_cursor_success(
        self,
        db_service: DatabaseService,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test updating sync cursor."""
        assert test_plaid_item.cursor is None
        
        updated_item = db_service.update_sync_cursor(
            plaid_item_id=test_plaid_item.id,
            cursor="cursor-abc123",
        )
        
        assert updated_item.cursor == "cursor-abc123"
    
    def test_update_sync_cursor_multiple_times(
        self,
        db_service: DatabaseService,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test updating sync cursor multiple times."""
        # First update
        db_service.update_sync_cursor(
            plaid_item_id=test_plaid_item.id,
            cursor="cursor-1",
        )
        
        # Second update
        updated_item = db_service.update_sync_cursor(
            plaid_item_id=test_plaid_item.id,
            cursor="cursor-2",
        )
        
        assert updated_item.cursor == "cursor-2"
    
    def test_update_sync_cursor_not_found(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test updating cursor for non-existent PlaidItem."""
        with pytest.raises(DatabaseServiceError) as exc_info:
            db_service.update_sync_cursor(
                plaid_item_id=uuid.uuid4(),
                cursor="cursor-abc",
            )
        
        assert "not found" in str(exc_info.value).lower()


class TestDeleteTransactions:
    """Tests for delete_transactions method."""
    
    def test_delete_transactions_success(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test deleting transactions."""
        # Create account and transactions
        accounts_data = [
            {
                "account_id": "account-del",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        
        accounts = db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        account_mapping = {"account-del": accounts[0].id}
        
        transactions_data = [
            {
                "transaction_id": "txn-del-1",
                "account_id": "account-del",
                "amount": 25.50,
                "date": "2024-01-15",
                "merchant_name": "Test 1",
                "pending": False,
                "category": ["Other"],
            },
            {
                "transaction_id": "txn-del-2",
                "account_id": "account-del",
                "amount": 50.00,
                "date": "2024-01-16",
                "merchant_name": "Test 2",
                "pending": False,
                "category": ["Other"],
            },
        ]
        
        db_service.upsert_transactions(
            transactions=transactions_data,
            account_mapping=account_mapping,
        )
        
        # Delete one transaction
        count = db_service.delete_transactions(["txn-del-1"])
        
        assert count == 1
    
    def test_delete_transactions_multiple(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test deleting multiple transactions."""
        # Create account and transactions
        accounts_data = [
            {
                "account_id": "account-del-multi",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        
        accounts = db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        account_mapping = {"account-del-multi": accounts[0].id}
        
        transactions_data = [
            {
                "transaction_id": f"txn-del-multi-{i}",
                "account_id": "account-del-multi",
                "amount": 25.50,
                "date": "2024-01-15",
                "merchant_name": f"Test {i}",
                "pending": False,
                "category": ["Other"],
            }
            for i in range(5)
        ]
        
        db_service.upsert_transactions(
            transactions=transactions_data,
            account_mapping=account_mapping,
        )
        
        # Delete multiple transactions
        count = db_service.delete_transactions(
            ["txn-del-multi-0", "txn-del-multi-2", "txn-del-multi-4"]
        )
        
        assert count == 3
    
    def test_delete_transactions_empty_list(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test deleting with empty list."""
        count = db_service.delete_transactions([])
        
        assert count == 0
    
    def test_delete_transactions_nonexistent(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test deleting non-existent transactions."""
        count = db_service.delete_transactions(
            ["txn-nonexistent-1", "txn-nonexistent-2"]
        )
        
        assert count == 0


class TestGetAccountByPlaidId:
    """Tests for get_account_by_plaid_id method."""
    
    def test_get_account_by_plaid_id_success(
        self,
        db_service: DatabaseService,
        test_user: User,
        test_plaid_item: PlaidItem,
    ) -> None:
        """Test retrieving account by Plaid ID."""
        # Create account
        accounts_data = [
            {
                "account_id": "account-find-me",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        
        db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=test_plaid_item.id,
            user_id=test_user.id,
        )
        
        # Retrieve account
        account = db_service.get_account_by_plaid_id("account-find-me")
        
        assert account is not None
        assert account.plaid_account_id == "account-find-me"
        assert account.name == "Checking"
    
    def test_get_account_by_plaid_id_not_found(
        self,
        db_service: DatabaseService,
    ) -> None:
        """Test retrieving non-existent account."""
        account = db_service.get_account_by_plaid_id("account-nonexistent")
        
        assert account is None
