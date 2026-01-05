"""
Unit tests for SyncOrchestrator.

Tests all methods of SyncOrchestrator with proper mocking of dependencies.
"""

import uuid
from typing import Generator
from unittest.mock import MagicMock, Mock, patch

import pytest
from sqlmodel import Session

from app.core.db_service import DatabaseService, DatabaseServiceError
from app.core.plaid_service import PlaidAPIError, PlaidService, PlaidServiceError
from app.core.sync_orchestrator import SyncOrchestrator, SyncOrchestratorError
from app.models import PlaidItem, User, UserCreate


@pytest.fixture
def test_user(db: Session) -> Generator[User, None, None]:
    """Create a test user for orchestrator operations."""
    from app import crud
    
    user_create = UserCreate(
        email=f"testuser_{uuid.uuid4()}@example.com",
        password="testpassword123",
        full_name="Test User",
    )
    user = crud.create_user(session=db, user_create=user_create)
    yield user
    
    # Cleanup
    db.delete(user)
    db.commit()


@pytest.fixture
def mock_plaid_service() -> MagicMock:
    """Create a mock PlaidService."""
    return MagicMock(spec=PlaidService)


@pytest.fixture
def sync_orchestrator(
    db: Session,
    mock_plaid_service: MagicMock,
) -> SyncOrchestrator:
    """Create a SyncOrchestrator with mocked PlaidService."""
    return SyncOrchestrator(
        session=db,
        plaid_service=mock_plaid_service,
    )


class TestHandleLinkTokenRequest:
    """Tests for handle_link_token_request method."""
    
    def test_handle_link_token_request_success(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
    ) -> None:
        """Test successful link token request."""
        mock_plaid_service.create_link_token.return_value = {
            "link_token": "link-sandbox-test-token",
            "expiration": "2024-12-31T23:59:59Z",
            "request_id": "test-request-id",
        }
        
        result = sync_orchestrator.handle_link_token_request(
            user_id=test_user.id,
        )
        
        assert result["link_token"] == "link-sandbox-test-token"
        assert result["expiration"] == "2024-12-31T23:59:59Z"
        
        # Verify PlaidService was called correctly
        mock_plaid_service.create_link_token.assert_called_once_with(
            user_id=str(test_user.id),
            client_name="WalletAI",
        )
    
    def test_handle_link_token_request_custom_client_name(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
    ) -> None:
        """Test link token request with custom client name."""
        mock_plaid_service.create_link_token.return_value = {
            "link_token": "link-sandbox-test-token",
            "expiration": "2024-12-31T23:59:59Z",
            "request_id": "test-request-id",
        }
        
        result = sync_orchestrator.handle_link_token_request(
            user_id=test_user.id,
            client_name="CustomApp",
        )
        
        assert result["link_token"] == "link-sandbox-test-token"
        
        mock_plaid_service.create_link_token.assert_called_once_with(
            user_id=str(test_user.id),
            client_name="CustomApp",
        )
    
    def test_handle_link_token_request_plaid_error(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
    ) -> None:
        """Test link token request with Plaid error."""
        mock_plaid_service.create_link_token.side_effect = PlaidAPIError(
            "API error",
            error_code="INVALID_REQUEST",
        )
        
        with pytest.raises(SyncOrchestratorError) as exc_info:
            sync_orchestrator.handle_link_token_request(user_id=test_user.id)
        
        assert "Failed to create link token" in str(exc_info.value)
        assert exc_info.value.error_code == "INVALID_REQUEST"


class TestHandlePublicTokenExchange:
    """Tests for handle_public_token_exchange method."""
    
    def test_handle_public_token_exchange_success(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
    ) -> None:
        """Test successful public token exchange."""
        # Mock exchange response
        mock_plaid_service.exchange_public_token.return_value = {
            "access_token": "access-sandbox-test-token",
            "item_id": "item-123",
            "request_id": "test-request-id",
        }
        
        # Mock accounts response
        mock_plaid_service.get_accounts.return_value = {
            "accounts": [
                {
                    "account_id": "account-1",
                    "name": "Checking",
                    "official_name": "Plaid Checking",
                    "type": "depository",
                    "balances": {
                        "current": 100.0,
                        "iso_currency_code": "USD",
                    },
                },
            ],
            "item": {"item_id": "item-123"},
            "request_id": "test-request-id",
        }
        
        result = sync_orchestrator.handle_public_token_exchange(
            user_id=test_user.id,
            public_token="public-sandbox-test-token",
            institution_name="Chase Bank",
        )
        
        assert result["item_id"] == "item-123"
        assert result["plaid_item"] is not None
        assert result["plaid_item"].institution_name == "Chase Bank"
        assert len(result["accounts"]) == 1
        assert result["accounts"][0].name == "Checking"
        
        # Verify services were called
        mock_plaid_service.exchange_public_token.assert_called_once_with(
            public_token="public-sandbox-test-token"
        )
        mock_plaid_service.get_accounts.assert_called_once()
    
    def test_handle_public_token_exchange_plaid_error(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
    ) -> None:
        """Test public token exchange with Plaid error."""
        mock_plaid_service.exchange_public_token.side_effect = PlaidAPIError(
            "Invalid public token",
            error_code="INVALID_PUBLIC_TOKEN",
        )
        
        with pytest.raises(SyncOrchestratorError) as exc_info:
            sync_orchestrator.handle_public_token_exchange(
                user_id=test_user.id,
                public_token="invalid-token",
                institution_name="Test Bank",
            )
        
        assert "Plaid API error" in str(exc_info.value)
    
    def test_handle_public_token_exchange_accounts_error(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
    ) -> None:
        """Test public token exchange with accounts fetch error."""
        # Mock successful exchange
        mock_plaid_service.exchange_public_token.return_value = {
            "access_token": "access-sandbox-test-token",
            "item_id": "item-123",
            "request_id": "test-request-id",
        }
        
        # Mock accounts error
        mock_plaid_service.get_accounts.side_effect = PlaidAPIError(
            "Item login required",
            error_code="ITEM_LOGIN_REQUIRED",
        )
        
        with pytest.raises(SyncOrchestratorError):
            sync_orchestrator.handle_public_token_exchange(
                user_id=test_user.id,
                public_token="public-sandbox-test-token",
                institution_name="Test Bank",
            )


class TestSyncUserTransactions:
    """Tests for sync_user_transactions method."""
    
    def test_sync_user_transactions_no_items(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
    ) -> None:
        """Test syncing transactions when user has no PlaidItems."""
        result = sync_orchestrator.sync_user_transactions(user_id=test_user.id)
        
        assert result["total_added"] == 0
        assert result["total_modified"] == 0
        assert result["total_removed"] == 0
        assert result["items_synced"] == 0
        assert len(result["results"]) == 0
    
    def test_sync_user_transactions_single_item(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
        db: Session,
    ) -> None:
        """Test syncing transactions for user with one PlaidItem."""
        # Create a PlaidItem
        db_service = DatabaseService(db)
        plaid_item = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-sync-1",
            access_token="access-token-sync-1",
            institution_name="Test Bank",
        )
        
        # Create an account
        accounts_data = [
            {
                "account_id": "account-sync-1",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=plaid_item.id,
            user_id=test_user.id,
        )
        
        # Mock Plaid sync responses
        mock_plaid_service.sync_all_transactions.return_value = {
            "added": [
                {
                    "transaction_id": "txn-1",
                    "account_id": "account-sync-1",
                    "amount": 25.50,
                    "date": "2024-01-15",
                    "merchant_name": "Starbucks",
                    "pending": False,
                    "category": ["Food and Drink"],
                },
            ],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-abc123",
            "total_synced": 1,
            "request_id": "test-request-id",
        }
        
        mock_plaid_service.get_accounts.return_value = {
            "accounts": accounts_data,
            "item": {"item_id": "item-sync-1"},
            "request_id": "test-request-id",
        }
        
        # Sync transactions
        result = sync_orchestrator.sync_user_transactions(user_id=test_user.id)
        
        assert result["total_added"] == 1
        assert result["total_modified"] == 0
        assert result["total_removed"] == 0
        assert result["items_synced"] == 1
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True
    
    def test_sync_user_transactions_multiple_items(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
        db: Session,
    ) -> None:
        """Test syncing transactions for user with multiple PlaidItems."""
        db_service = DatabaseService(db)
        
        # Create two PlaidItems
        plaid_item_1 = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-multi-1",
            access_token="access-token-multi-1",
            institution_name="Bank 1",
        )
        
        plaid_item_2 = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-multi-2",
            access_token="access-token-multi-2",
            institution_name="Bank 2",
        )
        
        # Create accounts for each item
        accounts_data_1 = [
            {
                "account_id": "account-multi-1",
                "name": "Checking 1",
                "official_name": "Test Checking 1",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        db_service.upsert_accounts(
            accounts=accounts_data_1,
            plaid_item_id=plaid_item_1.id,
            user_id=test_user.id,
        )
        
        accounts_data_2 = [
            {
                "account_id": "account-multi-2",
                "name": "Checking 2",
                "official_name": "Test Checking 2",
                "type": "depository",
                "balances": {"current": 200.0, "iso_currency_code": "USD"},
            },
        ]
        db_service.upsert_accounts(
            accounts=accounts_data_2,
            plaid_item_id=plaid_item_2.id,
            user_id=test_user.id,
        )
        
        # Mock Plaid responses
        def mock_sync_all(access_token, cursor):
            if access_token == "access-token-multi-1":
                return {
                    "added": [{"transaction_id": "txn-1", "account_id": "account-multi-1", "amount": 10.0, "date": "2024-01-15", "merchant_name": "Test 1", "pending": False, "category": ["Other"]}],
                    "modified": [],
                    "removed": [],
                    "next_cursor": "cursor-1",
                    "total_synced": 1,
                }
            else:
                return {
                    "added": [{"transaction_id": "txn-2", "account_id": "account-multi-2", "amount": 20.0, "date": "2024-01-15", "merchant_name": "Test 2", "pending": False, "category": ["Other"]}],
                    "modified": [{"transaction_id": "txn-3", "account_id": "account-multi-2", "amount": 30.0, "date": "2024-01-16", "merchant_name": "Test 3", "pending": False, "category": ["Other"]}],
                    "removed": [],
                    "next_cursor": "cursor-2",
                    "total_synced": 2,
                }
        
        mock_plaid_service.sync_all_transactions.side_effect = mock_sync_all
        
        def mock_get_accounts(access_token):
            if access_token == "access-token-multi-1":
                return {"accounts": accounts_data_1, "item": {"item_id": "item-multi-1"}}
            else:
                return {"accounts": accounts_data_2, "item": {"item_id": "item-multi-2"}}
        
        mock_plaid_service.get_accounts.side_effect = mock_get_accounts
        
        # Sync transactions
        result = sync_orchestrator.sync_user_transactions(user_id=test_user.id)
        
        assert result["total_added"] == 2
        assert result["total_modified"] == 1
        assert result["total_removed"] == 0
        assert result["items_synced"] == 2
    
    def test_sync_user_transactions_partial_failure(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
        db: Session,
    ) -> None:
        """Test syncing when one item fails."""
        db_service = DatabaseService(db)
        
        # Create two PlaidItems
        plaid_item_1 = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-partial-1",
            access_token="access-token-partial-1",
            institution_name="Bank 1",
        )
        
        plaid_item_2 = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-partial-2",
            access_token="access-token-partial-2",
            institution_name="Bank 2",
        )
        
        # Create accounts
        accounts_data_1 = [
            {
                "account_id": "account-partial-1",
                "name": "Checking 1",
                "official_name": "Test Checking 1",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        db_service.upsert_accounts(
            accounts=accounts_data_1,
            plaid_item_id=plaid_item_1.id,
            user_id=test_user.id,
        )
        
        accounts_data_2 = [
            {
                "account_id": "account-partial-2",
                "name": "Checking 2",
                "official_name": "Test Checking 2",
                "type": "depository",
                "balances": {"current": 200.0, "iso_currency_code": "USD"},
            },
        ]
        db_service.upsert_accounts(
            accounts=accounts_data_2,
            plaid_item_id=plaid_item_2.id,
            user_id=test_user.id,
        )
        
        # Mock first item success, second item failure
        def mock_sync_all(access_token, cursor):
            if access_token == "access-token-partial-1":
                return {
                    "added": [{"transaction_id": "txn-1", "account_id": "account-partial-1", "amount": 10.0, "date": "2024-01-15", "merchant_name": "Test", "pending": False, "category": ["Other"]}],
                    "modified": [],
                    "removed": [],
                    "next_cursor": "cursor-1",
                    "total_synced": 1,
                }
            else:
                raise PlaidAPIError("Item login required", "ITEM_LOGIN_REQUIRED")
        
        mock_plaid_service.sync_all_transactions.side_effect = mock_sync_all
        mock_plaid_service.get_accounts.return_value = {
            "accounts": accounts_data_1,
            "item": {"item_id": "item-partial-1"},
        }
        
        # Should not raise, but continue with partial success
        result = sync_orchestrator.sync_user_transactions(user_id=test_user.id)
        
        assert result["items_synced"] == 2
        assert len(result["results"]) == 2
        
        # First item should succeed
        success_results = [r for r in result["results"] if r.get("success")]
        failure_results = [r for r in result["results"] if not r.get("success")]
        
        assert len(success_results) == 1
        assert len(failure_results) == 1


class TestSyncPlaidItem:
    """Tests for sync_plaid_item method."""
    
    def test_sync_plaid_item_success(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
        db: Session,
    ) -> None:
        """Test successful PlaidItem sync."""
        db_service = DatabaseService(db)
        
        # Create PlaidItem and account
        plaid_item = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-single-sync",
            access_token="access-token-single-sync",
            institution_name="Test Bank",
        )
        
        accounts_data = [
            {
                "account_id": "account-single-sync",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        
        db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=plaid_item.id,
            user_id=test_user.id,
        )
        
        # Mock Plaid responses
        mock_plaid_service.sync_all_transactions.return_value = {
            "added": [
                {
                    "transaction_id": "txn-new",
                    "account_id": "account-single-sync",
                    "amount": 25.50,
                    "date": "2024-01-15",
                    "merchant_name": "Starbucks",
                    "pending": False,
                    "category": ["Food and Drink"],
                },
            ],
            "modified": [],
            "removed": [{"transaction_id": "txn-old"}],
            "next_cursor": "cursor-new",
            "total_synced": 2,
        }
        
        mock_plaid_service.get_accounts.return_value = {
            "accounts": accounts_data,
            "item": {"item_id": "item-single-sync"},
        }
        
        # Sync
        result = sync_orchestrator.sync_plaid_item(plaid_item)
        
        assert result["success"] is True
        assert result["added_count"] == 1
        assert result["modified_count"] == 0
        assert result["removed_count"] == 0  # Transaction didn't exist
        assert result["institution_name"] == "Test Bank"
        
        # Verify cursor was updated
        updated_item = db_service.get_plaid_item_by_id(plaid_item.id)
        assert updated_item.cursor == "cursor-new"
    
    def test_sync_plaid_item_with_cursor(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
        db: Session,
    ) -> None:
        """Test PlaidItem sync with existing cursor."""
        db_service = DatabaseService(db)
        
        # Create PlaidItem with cursor
        plaid_item = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-cursor-sync",
            access_token="access-token-cursor-sync",
            institution_name="Test Bank",
        )
        db_service.update_sync_cursor(plaid_item.id, "cursor-old")
        
        accounts_data = [
            {
                "account_id": "account-cursor-sync",
                "name": "Checking",
                "official_name": "Test Checking",
                "type": "depository",
                "balances": {"current": 100.0, "iso_currency_code": "USD"},
            },
        ]
        
        db_service.upsert_accounts(
            accounts=accounts_data,
            plaid_item_id=plaid_item.id,
            user_id=test_user.id,
        )
        
        # Mock incremental sync
        mock_plaid_service.sync_all_transactions.return_value = {
            "added": [],
            "modified": [],
            "removed": [],
            "next_cursor": "cursor-new",
            "total_synced": 0,
        }
        
        mock_plaid_service.get_accounts.return_value = {
            "accounts": accounts_data,
            "item": {"item_id": "item-cursor-sync"},
        }
        
        # Refresh plaid_item
        plaid_item = db_service.get_plaid_item_by_id(plaid_item.id)
        
        # Sync
        result = sync_orchestrator.sync_plaid_item(plaid_item)
        
        assert result["success"] is True
        
        # Verify sync was called with cursor
        mock_plaid_service.sync_all_transactions.assert_called_once_with(
            access_token="access-token-cursor-sync",
            cursor="cursor-old",
        )
    
    def test_sync_plaid_item_plaid_error(
        self,
        sync_orchestrator: SyncOrchestrator,
        test_user: User,
        mock_plaid_service: MagicMock,
        db: Session,
    ) -> None:
        """Test PlaidItem sync with Plaid error."""
        db_service = DatabaseService(db)
        
        plaid_item = db_service.create_plaid_item(
            user_id=test_user.id,
            item_id="item-error",
            access_token="access-token-error",
            institution_name="Test Bank",
        )
        
        # Mock Plaid error
        mock_plaid_service.sync_all_transactions.side_effect = PlaidAPIError(
            "Item login required",
            "ITEM_LOGIN_REQUIRED",
        )
        
        with pytest.raises(SyncOrchestratorError) as exc_info:
            sync_orchestrator.sync_plaid_item(plaid_item)
        
        assert "Plaid API error" in str(exc_info.value)
        assert exc_info.value.error_code == "ITEM_LOGIN_REQUIRED"
